#!/usr/bin/env python3
"""CARGO OTP Service Backend Tests — Phase: OTP provider-agnostic layer + rate limiting + lifecycle.

Test sequence as per review request:
PHASE 1 — default config (no .env changes)
PHASE 2 — temporary .env experiments (each: append line, restart, test, remove, restart)
PHASE 3 — final environment verification
"""

import requests
import time
import sys
import subprocess
import re

# BASE_URL = "http://localhost:8001/api"
BASE_URL = "https://hardened-cargo.preview.emergentagent.com/api"

def log(msg):
    print(f"[TEST] {msg}", flush=True)

def test_result(test_id, passed, detail=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} [{test_id}] {detail}", flush=True)
    return passed

def restart_backend():
    """Restart backend and wait for it to be ready."""
    log("Restarting backend...")
    subprocess.run(["sudo", "supervisorctl", "restart", "backend"], check=True, capture_output=True)
    time.sleep(8)  # Wait for backend to be ready
    # Verify backend is up
    for i in range(10):
        try:
            resp = requests.get(f"{BASE_URL.rsplit('/api', 1)[0]}/api/", timeout=5)
            if resp.status_code == 200:
                log("Backend ready")
                return
        except:
            pass
        time.sleep(2)
    log("WARNING: Backend may not be fully ready")

def append_env_line(line):
    """Append a line to /app/backend/.env"""
    with open("/app/backend/.env", "a") as f:
        f.write(f"\n{line}\n")
    log(f"Appended to .env: {line}")

def remove_env_line(line):
    """Remove a specific line from /app/backend/.env"""
    with open("/app/backend/.env", "r") as f:
        lines = f.readlines()
    with open("/app/backend/.env", "w") as f:
        for l in lines:
            if line not in l:
                f.write(l)
    log(f"Removed from .env: {line}")

def verify_env_original():
    """Verify .env contains exactly the original 5 lines."""
    with open("/app/backend/.env", "r") as f:
        content = f.read().strip()
    lines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
    expected = ["MONGO_URL=", "DB_NAME=", "ADMIN_EMAIL=", "ADMIN_PASSWORD=", "JWT_SECRET="]
    if len(lines) == 5 and all(any(exp in l for exp in expected) for l in lines):
        return True
    return False

# ============================================================================
# PHASE 1 — Default config tests
# ============================================================================
def phase1_tests():
    log("=" * 80)
    log("PHASE 1 — Default config (no .env changes)")
    log("=" * 80)
    
    results = []
    
    # [1] Demo OTP login for 3 seeded roles
    log("\n[1] Demo OTP login for 3 seeded roles")
    
    roles_phones = [
        ("customer", "+96890000001"),
        ("driver", "+96890000002"),
        ("provider", "+96890000005"),
    ]
    
    for role, phone in roles_phones:
        log(f"\n  Testing {role} {phone}")
        
        # Request OTP
        resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": phone, "role": role}, timeout=10)
        if resp.status_code != 200:
            results.append(test_result(f"1.{role}.request", False, f"Request failed: {resp.status_code} {resp.text}"))
            continue
        
        data = resp.json()
        if "demo_code" not in data:
            results.append(test_result(f"1.{role}.request", False, f"demo_code not present in response"))
            continue
        
        demo_code = data["demo_code"]
        results.append(test_result(f"1.{role}.request", True, f"Request 200, demo_code={demo_code}"))
        
        # Verify OTP
        resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={"phone": phone, "role": role, "code": demo_code}, timeout=10)
        if resp.status_code != 200:
            results.append(test_result(f"1.{role}.verify", False, f"Verify failed: {resp.status_code} {resp.text}"))
            continue
        
        data = resp.json()
        if "token" not in data or "user" not in data:
            results.append(test_result(f"1.{role}.verify", False, f"Missing token or user in response"))
            continue
        
        if data["user"].get("role") != role:
            results.append(test_result(f"1.{role}.verify", False, f"User role mismatch: expected {role}, got {data['user'].get('role')}"))
            continue
        
        results.append(test_result(f"1.{role}.verify", True, f"Verify 200, token received, user.role={role}"))
    
    # [2] Single-use: fresh phone
    log("\n[2] Single-use test")
    phone = "+96897770001"
    role = "customer"
    
    resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": phone, "role": role}, timeout=10)
    if resp.status_code == 200 and "demo_code" in resp.json():
        demo_code = resp.json()["demo_code"]
        results.append(test_result("2.request", True, f"Request 200, demo_code={demo_code}"))
        
        # First verify - should succeed
        resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={"phone": phone, "role": role, "code": demo_code}, timeout=10)
        if resp.status_code == 200:
            results.append(test_result("2.verify.first", True, "First verify 200"))
            
            # Second verify with SAME code - should fail 400
            resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={"phone": phone, "role": role, "code": demo_code}, timeout=10)
            if resp.status_code == 400 and "Invalid or expired code" in resp.text:
                results.append(test_result("2.verify.second", True, "Second verify 400 'Invalid or expired code' (single-use enforced)"))
            else:
                results.append(test_result("2.verify.second", False, f"Expected 400, got {resp.status_code} {resp.text}"))
        else:
            results.append(test_result("2.verify.first", False, f"First verify failed: {resp.status_code}"))
    else:
        results.append(test_result("2.request", False, f"Request failed: {resp.status_code}"))
    
    # [3] Attempt limit
    log("\n[3] Attempt limit test")
    phone = "+96897770002"
    role = "customer"
    
    resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": phone, "role": role}, timeout=10)
    if resp.status_code == 200 and "demo_code" in resp.json():
        demo_code = resp.json()["demo_code"]
        results.append(test_result("3.request", True, f"Request 200, demo_code={demo_code}"))
        
        # Verify with wrong code 5 times (OTP_VERIFY_MAX_ATTEMPTS=5)
        wrong_attempts = 0
        for i in range(5):
            resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={"phone": phone, "role": role, "code": "000000"}, timeout=10)
            if resp.status_code == 400:
                wrong_attempts += 1
        
        results.append(test_result("3.wrong_attempts", wrong_attempts == 5, f"5 wrong attempts all returned 400"))
        
        # Now verify with CORRECT code - should fail because budget exhausted
        resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={"phone": phone, "role": role, "code": demo_code}, timeout=10)
        if resp.status_code == 400 and "Invalid or expired code" in resp.text:
            results.append(test_result("3.correct_after_exhausted", True, "Correct code after budget exhausted returns 400 (code invalidated)"))
        else:
            results.append(test_result("3.correct_after_exhausted", False, f"Expected 400, got {resp.status_code}"))
    else:
        results.append(test_result("3.request", False, f"Request failed: {resp.status_code}"))
    
    # [4] Request rate limiting
    log("\n[4] Request rate limiting test")
    phone = "+96897770003"
    role = "customer"
    
    success_count = 0
    rate_limited = False
    
    for i in range(6):
        resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": phone, "role": role}, timeout=10)
        if resp.status_code == 200:
            success_count += 1
        elif resp.status_code == 429 and "OTP_RATE_LIMITED" in resp.text:
            rate_limited = True
            break
    
    if success_count == 5 and rate_limited:
        results.append(test_result("4.rate_limit", True, f"First 5 requests succeeded, 6th request returned 429 OTP_RATE_LIMITED"))
    else:
        results.append(test_result("4.rate_limit", False, f"Expected 5 success + 1 rate limit, got {success_count} success, rate_limited={rate_limited}"))
    
    return results

# ============================================================================
# PHASE 2 — Temporary .env experiments
# ============================================================================
def phase2_tests():
    log("=" * 80)
    log("PHASE 2 — Temporary .env experiments")
    log("=" * 80)
    
    results = []
    
    # [5] Demo disabled
    log("\n[5] Demo disabled test")
    append_env_line("OTP_DEMO_EXPOSE_CODE=false")
    restart_backend()
    
    phone = "+96897770004"
    role = "customer"
    resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": phone, "role": role}, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if "demo_code" not in data:
            results.append(test_result("5.demo_disabled", True, "Request 200, demo_code NOT present (demo disabled)"))
        else:
            results.append(test_result("5.demo_disabled", False, f"demo_code present when it should be hidden: {data}"))
    else:
        results.append(test_result("5.demo_disabled", False, f"Request failed: {resp.status_code}"))
    
    remove_env_line("OTP_DEMO_EXPOSE_CODE=false")
    restart_backend()
    
    # [6] Expiry
    log("\n[6] Expiry test")
    append_env_line("OTP_TTL_SECONDS=2")
    restart_backend()
    
    phone = "+96897770005"
    role = "customer"
    resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": phone, "role": role}, timeout=10)
    
    if resp.status_code == 200 and "demo_code" in resp.json():
        demo_code = resp.json()["demo_code"]
        results.append(test_result("6.request", True, f"Request 200, demo_code={demo_code}"))
        
        log("  Sleeping 4 seconds to let OTP expire...")
        time.sleep(4)
        
        resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={"phone": phone, "role": role, "code": demo_code}, timeout=10)
        if resp.status_code == 400 and "Invalid or expired code" in resp.text:
            results.append(test_result("6.expired", True, "Verify after expiry returns 400 'Invalid or expired code'"))
        else:
            results.append(test_result("6.expired", False, f"Expected 400, got {resp.status_code} {resp.text}"))
    else:
        results.append(test_result("6.request", False, f"Request failed: {resp.status_code}"))
    
    remove_env_line("OTP_TTL_SECONDS=2")
    restart_backend()
    
    # [7] Unknown provider
    log("\n[7] Unknown provider test")
    append_env_line("OTP_PROVIDER=fake_sms")
    restart_backend()
    
    phone = "+96897770006"
    role = "customer"
    resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": phone, "role": role}, timeout=10)
    
    if resp.status_code == 500 and "OTP_PROVIDER_NOT_CONFIGURED" in resp.text:
        results.append(test_result("7.unknown_provider", True, "Request returns 500 OTP_PROVIDER_NOT_CONFIGURED (fail-closed)"))
        # Verify no demo_code exposed
        if "demo_code" not in resp.text:
            results.append(test_result("7.no_code_leak", True, "No demo_code exposed in error response"))
        else:
            results.append(test_result("7.no_code_leak", False, "demo_code found in error response"))
    else:
        results.append(test_result("7.unknown_provider", False, f"Expected 500 OTP_PROVIDER_NOT_CONFIGURED, got {resp.status_code} {resp.text}"))
    
    remove_env_line("OTP_PROVIDER=fake_sms")
    restart_backend()
    
    return results

# ============================================================================
# PHASE 3 — Final environment verification
# ============================================================================
def phase3_tests():
    log("=" * 80)
    log("PHASE 3 — Final environment verification")
    log("=" * 80)
    
    results = []
    
    # [8] Verify .env original
    log("\n[8] Verify .env contains exactly original 5 lines")
    if verify_env_original():
        results.append(test_result("8.env_original", True, ".env contains exactly original 5 lines (MONGO_URL, DB_NAME, ADMIN_EMAIL, ADMIN_PASSWORD, JWT_SECRET)"))
    else:
        results.append(test_result("8.env_original", False, ".env does not match original 5 lines"))
    
    # Verify backend running
    try:
        result = subprocess.run(["sudo", "supervisorctl", "status", "backend"], capture_output=True, text=True, timeout=5)
        if "RUNNING" in result.stdout:
            results.append(test_result("8.backend_running", True, "Backend RUNNING via supervisorctl"))
        else:
            results.append(test_result("8.backend_running", False, f"Backend not running: {result.stdout}"))
    except Exception as e:
        results.append(test_result("8.backend_running", False, f"Error checking backend: {e}"))
    
    # Verify GET /api/ returns 200
    try:
        resp = requests.get(f"{BASE_URL.rsplit('/api', 1)[0]}/api/", timeout=10)
        if resp.status_code == 200:
            results.append(test_result("8.api_health", True, "GET /api/ returns 200"))
        else:
            results.append(test_result("8.api_health", False, f"GET /api/ returns {resp.status_code}"))
    except Exception as e:
        results.append(test_result("8.api_health", False, f"GET /api/ failed: {e}"))
    
    # [9] Final login test
    log("\n[9] Final login test (demo mode restored)")
    phone = "+96890000001"
    role = "customer"
    
    resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": phone, "role": role}, timeout=10)
    if resp.status_code == 200 and "demo_code" in resp.json():
        demo_code = resp.json()["demo_code"]
        results.append(test_result("9.final_login", True, f"Request 200, demo_code present (demo mode restored), demo_code={demo_code}"))
    else:
        results.append(test_result("9.final_login", False, f"Request failed or demo_code missing: {resp.status_code}"))
    
    # [10] Log hygiene
    log("\n[10] Log hygiene test")
    phone = "+96897770007"
    role = "customer"
    
    resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": phone, "role": role}, timeout=10)
    if resp.status_code == 200 and "demo_code" in resp.json():
        demo_code = resp.json()["demo_code"]
        results.append(test_result("10.request", True, f"Request 200, demo_code={demo_code}"))
        
        # Check backend logs for the code
        try:
            with open("/var/log/supervisor/backend.out.log", "r") as f:
                out_log = f.read()
            with open("/var/log/supervisor/backend.err.log", "r") as f:
                err_log = f.read()
            
            if demo_code in out_log or demo_code in err_log:
                results.append(test_result("10.log_hygiene", False, f"demo_code {demo_code} FOUND in backend logs (security issue)"))
            else:
                results.append(test_result("10.log_hygiene", True, f"demo_code {demo_code} NOT found in backend logs (secure)"))
        except Exception as e:
            results.append(test_result("10.log_hygiene", False, f"Error reading logs: {e}"))
    else:
        results.append(test_result("10.request", False, f"Request failed: {resp.status_code}"))
    
    return results

# ============================================================================
# Main
# ============================================================================
def main():
    log("CARGO OTP Service Backend Tests — Starting")
    log(f"BASE_URL: {BASE_URL}")
    
    # CRITICAL: Restart backend BEFORE Phase 1 to reset in-memory rate limiter
    log("\n" + "=" * 80)
    log("PRE-TEST: Restarting backend to reset in-memory rate limiter")
    log("=" * 80)
    restart_backend()
    
    all_results = []
    
    try:
        all_results.extend(phase1_tests())
        all_results.extend(phase2_tests())
        all_results.extend(phase3_tests())
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Summary
    log("\n" + "=" * 80)
    log("TEST SUMMARY")
    log("=" * 80)
    passed = sum(1 for r in all_results if r)
    total = len(all_results)
    log(f"PASSED: {passed}/{total}")
    log(f"FAILED: {total - passed}/{total}")
    
    if passed == total:
        log("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        log("\n❌ SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
