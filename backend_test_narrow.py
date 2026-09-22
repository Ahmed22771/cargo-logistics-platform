#!/usr/bin/env python3
"""
Narrow backend verification for current scoped changes.
Tests ONLY:
1. Admin login + /api/auth/me
2. Customer OTP request+verify
3. Driver OTP request+verify
4. Provider OTP request+verify + provider-specific endpoints
5. Provider profile update (no-op, preserve existing values)
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://cargo-readiness-om.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"
CUSTOMER_PHONE = "+96890000001"
DRIVER_PHONE = "+96890000002"
PROVIDER_PHONE = "+96890000005"

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def pass_test(self, name: str):
        self.passed += 1
        print(f"✅ PASS: {name}")
    
    def fail_test(self, name: str, reason: str):
        self.failed += 1
        error_msg = f"❌ FAIL: {name} - {reason}"
        self.errors.append(error_msg)
        print(error_msg)
    
    def summary(self):
        print("\n" + "="*80)
        print(f"SUMMARY: {self.passed} passed, {self.failed} failed")
        if self.errors:
            print("\nFAILURES:")
            for error in self.errors:
                print(f"  {error}")
        print("="*80)
        return self.failed == 0

result = TestResult()

def test_json_serializable(data: Any, test_name: str) -> bool:
    """Verify data is JSON serializable"""
    try:
        json.dumps(data)
        return True
    except (TypeError, ValueError) as e:
        result.fail_test(test_name, f"Response not JSON serializable: {e}")
        return False

def test_admin_login():
    """Test 1: Admin POST /api/auth/admin/login returns 200 and token; GET /api/auth/me works"""
    print("\n[1] Testing Admin Login")
    
    # Admin login
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/admin/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        
        if resp.status_code != 200:
            result.fail_test("Admin login", f"Expected 200, got {resp.status_code}: {resp.text}")
            return None
        
        data = resp.json()
        if not test_json_serializable(data, "Admin login response"):
            return None
        
        if "token" not in data:
            result.fail_test("Admin login", "Response missing 'token' field")
            return None
        
        token = data["token"]
        result.pass_test("Admin login returns 200 and token")
        
        # Test GET /api/auth/me
        resp_me = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if resp_me.status_code != 200:
            result.fail_test("Admin GET /auth/me", f"Expected 200, got {resp_me.status_code}: {resp_me.text}")
            return None
        
        me_data = resp_me.json()
        if not test_json_serializable(me_data, "Admin GET /auth/me response"):
            return None
        
        result.pass_test("Admin GET /auth/me returns 200")
        return token
        
    except Exception as e:
        result.fail_test("Admin login", f"Exception: {e}")
        return None

def test_customer_otp():
    """Test 2: Customer OTP request+verify once returns 200/token"""
    print("\n[2] Testing Customer OTP Login")
    
    try:
        # OTP request
        resp_req = requests.post(
            f"{BASE_URL}/auth/otp/request",
            json={"phone": CUSTOMER_PHONE, "role": "customer"},
            timeout=10
        )
        
        if resp_req.status_code != 200:
            result.fail_test("Customer OTP request", f"Expected 200, got {resp_req.status_code}: {resp_req.text}")
            return None
        
        req_data = resp_req.json()
        if not test_json_serializable(req_data, "Customer OTP request response"):
            return None
        
        if "demo_code" not in req_data:
            result.fail_test("Customer OTP request", "Response missing 'demo_code' field")
            return None
        
        demo_code = req_data["demo_code"]
        result.pass_test("Customer OTP request returns 200 with demo_code")
        
        # OTP verify
        resp_verify = requests.post(
            f"{BASE_URL}/auth/otp/verify",
            json={"phone": CUSTOMER_PHONE, "role": "customer", "code": demo_code},
            timeout=10
        )
        
        if resp_verify.status_code != 200:
            result.fail_test("Customer OTP verify", f"Expected 200, got {resp_verify.status_code}: {resp_verify.text}")
            return None
        
        verify_data = resp_verify.json()
        if not test_json_serializable(verify_data, "Customer OTP verify response"):
            return None
        
        if "token" not in verify_data:
            result.fail_test("Customer OTP verify", "Response missing 'token' field")
            return None
        
        token = verify_data["token"]
        result.pass_test("Customer OTP verify returns 200 and token")
        return token
        
    except Exception as e:
        result.fail_test("Customer OTP login", f"Exception: {e}")
        return None

def test_driver_otp():
    """Test 3: Driver OTP request+verify once returns 200/token"""
    print("\n[3] Testing Driver OTP Login")
    
    try:
        # OTP request
        resp_req = requests.post(
            f"{BASE_URL}/auth/otp/request",
            json={"phone": DRIVER_PHONE, "role": "driver"},
            timeout=10
        )
        
        if resp_req.status_code != 200:
            result.fail_test("Driver OTP request", f"Expected 200, got {resp_req.status_code}: {resp_req.text}")
            return None
        
        req_data = resp_req.json()
        if not test_json_serializable(req_data, "Driver OTP request response"):
            return None
        
        if "demo_code" not in req_data:
            result.fail_test("Driver OTP request", "Response missing 'demo_code' field")
            return None
        
        demo_code = req_data["demo_code"]
        result.pass_test("Driver OTP request returns 200 with demo_code")
        
        # OTP verify
        resp_verify = requests.post(
            f"{BASE_URL}/auth/otp/verify",
            json={"phone": DRIVER_PHONE, "role": "driver", "code": demo_code},
            timeout=10
        )
        
        if resp_verify.status_code != 200:
            result.fail_test("Driver OTP verify", f"Expected 200, got {resp_verify.status_code}: {resp_verify.text}")
            return None
        
        verify_data = resp_verify.json()
        if not test_json_serializable(verify_data, "Driver OTP verify response"):
            return None
        
        if "token" not in verify_data:
            result.fail_test("Driver OTP verify", "Response missing 'token' field")
            return None
        
        token = verify_data["token"]
        result.pass_test("Driver OTP verify returns 200 and token")
        return token
        
    except Exception as e:
        result.fail_test("Driver OTP login", f"Exception: {e}")
        return None

def test_provider_otp_and_endpoints():
    """Test 4: Provider OTP request+verify + provider-specific endpoints"""
    print("\n[4] Testing Provider OTP Login and Provider Endpoints")
    
    try:
        # OTP request
        resp_req = requests.post(
            f"{BASE_URL}/auth/otp/request",
            json={"phone": PROVIDER_PHONE, "role": "provider"},
            timeout=10
        )
        
        if resp_req.status_code != 200:
            result.fail_test("Provider OTP request", f"Expected 200, got {resp_req.status_code}: {resp_req.text}")
            return None
        
        req_data = resp_req.json()
        if not test_json_serializable(req_data, "Provider OTP request response"):
            return None
        
        if "demo_code" not in req_data:
            result.fail_test("Provider OTP request", "Response missing 'demo_code' field")
            return None
        
        demo_code = req_data["demo_code"]
        result.pass_test("Provider OTP request returns 200 with demo_code")
        
        # OTP verify
        resp_verify = requests.post(
            f"{BASE_URL}/auth/otp/verify",
            json={"phone": PROVIDER_PHONE, "role": "provider", "code": demo_code},
            timeout=10
        )
        
        if resp_verify.status_code != 200:
            result.fail_test("Provider OTP verify", f"Expected 200, got {resp_verify.status_code}: {resp_verify.text}")
            return None
        
        verify_data = resp_verify.json()
        if not test_json_serializable(verify_data, "Provider OTP verify response"):
            return None
        
        if "token" not in verify_data:
            result.fail_test("Provider OTP verify", "Response missing 'token' field")
            return None
        
        token = verify_data["token"]
        result.pass_test("Provider OTP verify returns 200 and token")
        
        # Test provider-specific endpoints
        headers = {"Authorization": f"Bearer {token}"}
        
        # GET /api/provider/summary
        resp_summary = requests.get(f"{BASE_URL}/provider/summary", headers=headers, timeout=10)
        if resp_summary.status_code != 200:
            result.fail_test("GET /provider/summary", f"Expected 200, got {resp_summary.status_code}: {resp_summary.text}")
        else:
            summary_data = resp_summary.json()
            if test_json_serializable(summary_data, "GET /provider/summary response"):
                result.pass_test("GET /provider/summary returns 200 and JSON serializable")
        
        # GET /api/provider/opportunities
        resp_opps = requests.get(f"{BASE_URL}/provider/opportunities", headers=headers, timeout=10)
        if resp_opps.status_code != 200:
            result.fail_test("GET /provider/opportunities", f"Expected 200, got {resp_opps.status_code}: {resp_opps.text}")
        else:
            opps_data = resp_opps.json()
            if test_json_serializable(opps_data, "GET /provider/opportunities response"):
                result.pass_test("GET /provider/opportunities returns 200 and JSON serializable")
        
        # GET /api/provider/bids
        resp_bids = requests.get(f"{BASE_URL}/provider/bids", headers=headers, timeout=10)
        if resp_bids.status_code != 200:
            result.fail_test("GET /provider/bids", f"Expected 200, got {resp_bids.status_code}: {resp_bids.text}")
        else:
            bids_data = resp_bids.json()
            if test_json_serializable(bids_data, "GET /provider/bids response"):
                result.pass_test("GET /provider/bids returns 200 and JSON serializable")
        
        # GET /api/provider/transactions
        resp_txns = requests.get(f"{BASE_URL}/provider/transactions", headers=headers, timeout=10)
        if resp_txns.status_code != 200:
            result.fail_test("GET /provider/transactions", f"Expected 200, got {resp_txns.status_code}: {resp_txns.text}")
        else:
            txns_data = resp_txns.json()
            if test_json_serializable(txns_data, "GET /provider/transactions response"):
                result.pass_test("GET /provider/transactions returns 200 and JSON serializable")
        
        return token
        
    except Exception as e:
        result.fail_test("Provider OTP login and endpoints", f"Exception: {e}")
        return None

def test_provider_profile_update(token: str):
    """Test 5: PUT /api/profile using existing provider values (no changes)"""
    print("\n[5] Testing Provider Profile Update (No-Op)")
    
    if not token:
        result.fail_test("Provider profile update", "No provider token available")
        return
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # First, GET /api/auth/me to get current provider values
        resp_me = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
        
        if resp_me.status_code != 200:
            result.fail_test("Provider GET /auth/me", f"Expected 200, got {resp_me.status_code}: {resp_me.text}")
            return
        
        me_data = resp_me.json()
        if not test_json_serializable(me_data, "Provider GET /auth/me response"):
            return
        
        result.pass_test("Provider GET /auth/me returns 200")
        
        # Extract current values
        profile_update = {
            "name": me_data.get("name"),
            "email": me_data.get("email"),
            "phone": me_data.get("phone"),
            "address": me_data.get("address"),
            "company_name": me_data.get("company_name"),
            "cr_number": me_data.get("cr_number")
        }
        
        print(f"  Current provider values: name={profile_update['name']}, email={profile_update['email']}, phone={profile_update['phone']}")
        
        # PUT /api/profile with same values (no-op update)
        resp_update = requests.put(
            f"{BASE_URL}/profile",
            json=profile_update,
            headers=headers,
            timeout=10
        )
        
        if resp_update.status_code != 200:
            result.fail_test("Provider PUT /profile", f"Expected 200, got {resp_update.status_code}: {resp_update.text}")
            return
        
        update_data = resp_update.json()
        if not test_json_serializable(update_data, "Provider PUT /profile response"):
            return
        
        result.pass_test("Provider PUT /profile returns 200")
        
        # Verify fields are preserved
        resp_verify = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
        if resp_verify.status_code != 200:
            result.fail_test("Provider profile verification", f"GET /auth/me after update failed: {resp_verify.status_code}")
            return
        
        verify_data = resp_verify.json()
        
        # Check all fields are preserved
        fields_preserved = True
        for field, original_value in profile_update.items():
            if verify_data.get(field) != original_value:
                result.fail_test("Provider profile preservation", f"Field '{field}' changed: {original_value} -> {verify_data.get(field)}")
                fields_preserved = False
        
        if fields_preserved:
            result.pass_test("Provider profile fields preserved after no-op update")
        
    except Exception as e:
        result.fail_test("Provider profile update", f"Exception: {e}")

def main():
    print("="*80)
    print("NARROW BACKEND VERIFICATION")
    print(f"Backend URL: {BASE_URL}")
    print("="*80)
    
    # Test 1: Admin login
    admin_token = test_admin_login()
    
    # Test 2: Customer OTP
    customer_token = test_customer_otp()
    
    # Test 3: Driver OTP
    driver_token = test_driver_otp()
    
    # Test 4: Provider OTP + endpoints
    provider_token = test_provider_otp_and_endpoints()
    
    # Test 5: Provider profile update
    if provider_token:
        test_provider_profile_update(provider_token)
    
    # Summary
    success = result.summary()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
