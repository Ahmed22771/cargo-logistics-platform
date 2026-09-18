#!/usr/bin/env python3
"""
CARGO Backend Authentication Regression Test Suite
Tests OTP login (customer, driver, provider) and admin login flows
"""
import requests
import sys
import json
from typing import Dict, Any, Optional

# Base URL from frontend/.env
BASE_URL = "https://shipment-flow-58.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
TEST_USERS = {
    "customer": {"phone": "+96890000001", "role": "customer", "name": "أحمد البلوشي"},
    "driver_approved": {"phone": "+96890000002", "role": "driver", "name": "Driver Approved"},
    "driver_pending": {"phone": "+96890000004", "role": "driver", "name": "Driver Pending"},
    "provider": {"phone": "+96890000005", "role": "provider", "name": "Provider Test"},
}

ADMIN_CREDS = {"email": "admin@cargo.om", "password": "admin123"}

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name: str):
        self.passed += 1
        print(f"{GREEN}✓{RESET} {test_name}")
    
    def add_fail(self, test_name: str, reason: str):
        self.failed += 1
        error_msg = f"{test_name}: {reason}"
        self.errors.append(error_msg)
        print(f"{RED}✗{RESET} {test_name}")
        print(f"  {RED}Reason: {reason}{RESET}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total: {total} | {GREEN}Passed: {self.passed}{RESET} | {RED}Failed: {self.failed}{RESET}")
        if self.errors:
            print(f"\n{RED}FAILED TESTS:{RESET}")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")
        print(f"{'='*60}\n")
        return self.failed == 0

def test_otp_request(phone: str, role: str) -> Optional[str]:
    """Test OTP request and return demo_code"""
    url = f"{BASE_URL}/auth/otp/request"
    payload = {"phone": phone, "role": role}
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            return None, f"Status {resp.status_code}: {resp.text}"
        
        data = resp.json()
        if not data.get("success"):
            return None, "success=false in response"
        if "demo_code" not in data:
            return None, "demo_code missing from response"
        
        return data["demo_code"], None
    except Exception as e:
        return None, f"Exception: {str(e)}"

def test_otp_verify(phone: str, role: str, code: str) -> tuple[Optional[Dict], Optional[str]]:
    """Test OTP verify and return (token, user) or error"""
    url = f"{BASE_URL}/auth/otp/verify"
    payload = {"phone": phone, "role": role, "code": code}
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            return None, f"Status {resp.status_code}: {resp.text}"
        
        data = resp.json()
        if "token" not in data:
            return None, "token missing from response"
        if "user" not in data:
            return None, "user missing from response"
        
        return data, None
    except Exception as e:
        return None, f"Exception: {str(e)}"

def test_auth_me(token: str) -> tuple[Optional[Dict], Optional[str]]:
    """Test /auth/me with JWT token"""
    url = f"{BASE_URL}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None, f"Status {resp.status_code}: {resp.text}"
        
        user = resp.json()
        return user, None
    except Exception as e:
        return None, f"Exception: {str(e)}"

def test_admin_login(email: str, password: str) -> tuple[Optional[Dict], Optional[str]]:
    """Test admin login"""
    url = f"{BASE_URL}/auth/admin/login"
    payload = {"email": email, "password": password}
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            return None, f"Status {resp.status_code}: {resp.text}"
        
        data = resp.json()
        if "token" not in data:
            return None, "token missing from response"
        if "user" not in data:
            return None, "user missing from response"
        
        return data, None
    except Exception as e:
        return None, f"Exception: {str(e)}"

def run_otp_flow_test(result: TestResult, user_key: str, user_data: Dict, expected_role: str):
    """Run complete OTP flow: request -> verify -> /auth/me"""
    phone = user_data["phone"]
    role = user_data["role"]
    
    print(f"\n{BLUE}Testing {user_key.upper()} OTP Flow{RESET}")
    print(f"Phone: {phone}, Role: {role}")
    
    # Step 1: OTP Request
    demo_code, error = test_otp_request(phone, role)
    if error:
        result.add_fail(f"{user_key}: OTP Request", error)
        return
    result.add_pass(f"{user_key}: OTP Request (got demo_code: {demo_code})")
    
    # Step 2: OTP Verify
    verify_data, error = test_otp_verify(phone, role, demo_code)
    if error:
        result.add_fail(f"{user_key}: OTP Verify", error)
        return
    
    token = verify_data["token"]
    user = verify_data["user"]
    
    # Validate user role
    if user.get("role") != expected_role:
        result.add_fail(f"{user_key}: OTP Verify role check", 
                       f"Expected role={expected_role}, got {user.get('role')}")
        return
    
    result.add_pass(f"{user_key}: OTP Verify (token received, role={user.get('role')})")
    
    # For pending driver, check verification_status
    if user_key == "driver_pending":
        v_status = user.get("verification_status")
        if v_status in ["PENDING", "DRAFT", "UNDER_REVIEW"]:
            result.add_pass(f"{user_key}: Verification status is {v_status} (login NOT blocked)")
        elif v_status == "SUSPENDED":
            result.add_fail(f"{user_key}: Verification status", 
                           f"Pending driver should NOT be SUSPENDED, got {v_status}")
            return
        else:
            # Just note it, don't fail
            print(f"  {YELLOW}Note: verification_status={v_status}{RESET}")
    
    # Step 3: /auth/me
    me_user, error = test_auth_me(token)
    if error:
        result.add_fail(f"{user_key}: GET /auth/me", error)
        return
    
    if me_user.get("id") != user.get("id"):
        result.add_fail(f"{user_key}: GET /auth/me user mismatch", 
                       f"Expected id={user.get('id')}, got {me_user.get('id')}")
        return
    
    result.add_pass(f"{user_key}: GET /auth/me (user verified)")

def run_admin_login_test(result: TestResult):
    """Run admin login flow"""
    print(f"\n{BLUE}Testing ADMIN Login{RESET}")
    print(f"Email: {ADMIN_CREDS['email']}")
    
    # Step 1: Admin Login
    login_data, error = test_admin_login(ADMIN_CREDS["email"], ADMIN_CREDS["password"])
    if error:
        result.add_fail("Admin: Login", error)
        return
    
    token = login_data["token"]
    user = login_data["user"]
    
    if user.get("role") != "admin":
        result.add_fail("Admin: Login role check", f"Expected role=admin, got {user.get('role')}")
        return
    
    result.add_pass(f"Admin: Login (token received, role={user.get('role')})")
    
    # Step 2: /auth/me
    me_user, error = test_auth_me(token)
    if error:
        result.add_fail("Admin: GET /auth/me", error)
        return
    
    if me_user.get("id") != user.get("id"):
        result.add_fail("Admin: GET /auth/me user mismatch", 
                       f"Expected id={user.get('id')}, got {me_user.get('id')}")
        return
    
    result.add_pass("Admin: GET /auth/me (user verified)")

def run_negative_tests(result: TestResult):
    """Run negative/contract tests"""
    print(f"\n{BLUE}Testing NEGATIVE/CONTRACT Cases{RESET}")
    
    # Test 1: Wrong OTP code
    phone = TEST_USERS["customer"]["phone"]
    role = TEST_USERS["customer"]["role"]
    
    # First get a valid code
    demo_code, error = test_otp_request(phone, role)
    if error:
        result.add_fail("Negative: Setup OTP request", error)
        return
    
    # Now try with wrong code
    wrong_code = "000000" if demo_code != "000000" else "111111"
    url = f"{BASE_URL}/auth/otp/verify"
    payload = {"phone": phone, "role": role, "code": wrong_code}
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 400:
            data = resp.json()
            detail = data.get("detail", "")
            if "Invalid or expired code" in detail:
                result.add_pass("Negative: Wrong OTP code returns 400 with correct error")
            else:
                result.add_fail("Negative: Wrong OTP code error message", 
                               f"Expected 'Invalid or expired code', got '{detail}'")
        elif resp.status_code == 500:
            result.add_fail("Negative: Wrong OTP code returns 500", 
                           "Should return 400, not 500 (reproduces 'Something went wrong')")
        else:
            result.add_fail("Negative: Wrong OTP code status", 
                           f"Expected 400, got {resp.status_code}")
    except Exception as e:
        result.add_fail("Negative: Wrong OTP code exception", str(e))

def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}CARGO AUTHENTICATION REGRESSION TEST SUITE{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Base URL: {BASE_URL}")
    
    result = TestResult()
    
    # Test 1: Customer OTP Login
    run_otp_flow_test(result, "customer", TEST_USERS["customer"], "customer")
    
    # Test 2: Driver (approved) OTP Login
    run_otp_flow_test(result, "driver_approved", TEST_USERS["driver_approved"], "driver")
    
    # Test 3: Pending Driver OTP Login (MUST NOT be blocked)
    run_otp_flow_test(result, "driver_pending", TEST_USERS["driver_pending"], "driver")
    
    # Test 4: Provider OTP Login
    run_otp_flow_test(result, "provider", TEST_USERS["provider"], "provider")
    
    # Test 5: Admin Login
    run_admin_login_test(result)
    
    # Test 6: Negative/Contract Tests
    run_negative_tests(result)
    
    # Summary
    success = result.summary()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
