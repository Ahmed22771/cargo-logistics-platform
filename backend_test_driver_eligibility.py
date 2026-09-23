#!/usr/bin/env python3
"""
CARGO Backend Test — Driver Eligibility + Bid Flow (Focused Test)
Tests Yousef eligibility fix, compliance enforcement, and basic regression
"""
import requests
import sys
import json
from typing import Dict, Any, Optional, Tuple

# Base URL from frontend/.env
BASE_URL = "https://301fb6e6-a7ac-4e14-abe2-cd78e9c93702.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
CUSTOMER_PHONE = "+96890000001"
YOUSEF_PHONE = "+96890000004"  # يوسف الرئيسي - now eligible
APPROVED_DRIVER_PHONE = "+96890000002"  # خالد العامري - approved driver
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"

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
    
    def add_pass(self, test_name: str, details: str = ""):
        self.passed += 1
        print(f"{GREEN}✓ PASS{RESET} {test_name}")
        if details:
            print(f"  {BLUE}{details}{RESET}")
    
    def add_fail(self, test_name: str, reason: str):
        self.failed += 1
        error_msg = f"{test_name}: {reason}"
        self.errors.append(error_msg)
        print(f"{RED}✗ FAIL{RESET} {test_name}")
        print(f"  {RED}{reason}{RESET}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*80}")
        print(f"TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total: {total} | {GREEN}Passed: {self.passed}{RESET} | {RED}Failed: {self.failed}{RESET}")
        if self.errors:
            print(f"\n{RED}FAILED TESTS:{RESET}")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")
        print(f"{'='*80}\n")
        return self.failed == 0

def otp_login(phone: str, role: str) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
    """Complete OTP login flow. Returns (token, user, error)"""
    # Request OTP
    try:
        resp = requests.post(f"{BASE_URL}/auth/otp/request", 
                            json={"phone": phone, "role": role}, 
                            timeout=10)
        if resp.status_code != 200:
            return None, None, f"OTP request failed: {resp.status_code} {resp.text[:200]}"
        
        data = resp.json()
        demo_code = data.get("demo_code")
        if not demo_code:
            return None, None, "demo_code missing from OTP request response"
        
        # Verify OTP
        resp = requests.post(f"{BASE_URL}/auth/otp/verify",
                            json={"phone": phone, "role": role, "code": demo_code},
                            timeout=10)
        if resp.status_code != 200:
            return None, None, f"OTP verify failed: {resp.status_code} {resp.text[:200]}"
        
        data = resp.json()
        token = data.get("token")
        user = data.get("user")
        if not token or not user:
            return None, None, "token or user missing from verify response"
        
        return token, user, None
    except Exception as e:
        return None, None, f"Exception during OTP login: {str(e)}"

def admin_login() -> Tuple[Optional[str], Optional[str]]:
    """Admin login. Returns (token, error)"""
    try:
        resp = requests.post(f"{BASE_URL}/auth/admin/login",
                            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                            timeout=10)
        if resp.status_code != 200:
            return None, f"Admin login failed: {resp.status_code} {resp.text[:200]}"
        
        data = resp.json()
        token = data.get("token")
        if not token:
            return None, "token missing from admin login response"
        
        return token, None
    except Exception as e:
        return None, f"Exception during admin login: {str(e)}"

def main():
    result = TestResult()
    
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}CARGO Backend Test — Driver Eligibility + Bid Flow{RESET}")
    print(f"{BLUE}BASE: {BASE_URL}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    # Store tokens and IDs for later tests
    customer_token = None
    yousef_token = None
    yousef_user = None
    approved_driver_token = None
    approved_driver_user = None
    shipment_id = None
    shipment_id2 = None
    bid_id = None
    
    # ========================================================================
    # TEST 1: YOUSEF ELIGIBLE BID (main test)
    # ========================================================================
    print(f"\n{YELLOW}[TEST 1] YOUSEF ELIGIBLE BID{RESET}")
    print(f"{YELLOW}Testing that Yousef (+96890000004) can now bid after demo-data fix{RESET}\n")
    
    # 1.1: Login Yousef
    print(f"1.1: Login driver Yousef ({YOUSEF_PHONE})...")
    yousef_token, yousef_user, error = otp_login(YOUSEF_PHONE, "driver")
    if error:
        result.add_fail("1.1: Yousef OTP login", error)
    else:
        result.add_pass("1.1: Yousef OTP login", 
                       f"HTTP 200, token received, user.role={yousef_user.get('role')}, name={yousef_user.get('name')}")
    
    # 1.2: Check Yousef eligibility
    if yousef_token:
        print(f"1.2: GET /api/driver/eligibility as Yousef...")
        try:
            resp = requests.get(f"{BASE_URL}/driver/eligibility",
                               headers={"Authorization": f"Bearer {yousef_token}"},
                               timeout=10)
            if resp.status_code != 200:
                result.add_fail("1.2: Yousef eligibility check", 
                               f"HTTP {resp.status_code}: {resp.text[:200]}")
            else:
                data = resp.json()
                eligible = data.get("eligible")
                reasons = data.get("reasons", [])
                if eligible is True:
                    result.add_pass("1.2: Yousef eligibility check",
                                   f"HTTP 200, eligible=true, reasons={reasons}")
                else:
                    result.add_fail("1.2: Yousef eligibility check",
                                   f"eligible={eligible} (expected true), reasons={reasons}")
        except Exception as e:
            result.add_fail("1.2: Yousef eligibility check", f"Exception: {str(e)}")
    
    # 1.3: Login customer to create shipment
    print(f"1.3: Login customer ({CUSTOMER_PHONE})...")
    customer_token, customer_user, error = otp_login(CUSTOMER_PHONE, "customer")
    if error:
        result.add_fail("1.3: Customer OTP login", error)
    else:
        result.add_pass("1.3: Customer OTP login",
                       f"HTTP 200, token received, user.role={customer_user.get('role')}")
    
    # 1.4: Customer creates a PUBLISHED shipment
    if customer_token:
        print(f"1.4: Customer creates PUBLISHED shipment...")
        try:
            shipment_payload = {
                "title": "Test Shipment for Yousef Bid",
                "description": "Testing Yousef eligibility after demo-data fix",
                "category": "general",
                "weight": "50",
                "quantity": "1",
                "pickup_location": {
                    "address": "Muscat, Oman",
                    "lat": 23.5880,
                    "lng": 58.3829,
                    "city": "Muscat",
                    "area": "Muscat",
                    "country": "Oman"
                },
                "delivery_location": {
                    "address": "Salalah, Oman",
                    "lat": 17.0150,
                    "lng": 54.0924,
                    "city": "Salalah",
                    "area": "Dhofar",
                    "country": "Oman"
                },
                "vehicle_type": "pickup",
                "status": "PUBLISHED"
            }
            resp = requests.post(f"{BASE_URL}/shipments",
                                json=shipment_payload,
                                headers={"Authorization": f"Bearer {customer_token}"},
                                timeout=10)
            if resp.status_code != 200:
                result.add_fail("1.4: Customer create PUBLISHED shipment",
                               f"HTTP {resp.status_code}: {resp.text[:200]}")
            else:
                data = resp.json()
                shipment_id = data.get("id")
                status = data.get("status")
                result.add_pass("1.4: Customer create PUBLISHED shipment",
                               f"HTTP 200, shipment_id={shipment_id}, status={status}")
        except Exception as e:
            result.add_fail("1.4: Customer create PUBLISHED shipment", f"Exception: {str(e)}")
    
    # 1.5: Yousef submits bid (should succeed - HTTP 200)
    if yousef_token and shipment_id:
        print(f"1.5: Yousef POST /api/shipments/{shipment_id}/bids...")
        try:
            bid_payload = {"price": 45, "note": "I can deliver this safely"}
            resp = requests.post(f"{BASE_URL}/shipments/{shipment_id}/bids",
                                json=bid_payload,
                                headers={"Authorization": f"Bearer {yousef_token}"},
                                timeout=10)
            if resp.status_code != 200:
                result.add_fail("1.5: Yousef submit bid (expect 200)",
                               f"HTTP {resp.status_code}: {resp.text[:500]}")
            else:
                data = resp.json()
                bid_id = data.get("id")
                price = data.get("price")
                driver_name = data.get("driver_name")
                result.add_pass("1.5: Yousef submit bid (expect 200)",
                               f"HTTP 200, bid_id={bid_id}, price={price}, driver_name={driver_name}")
        except Exception as e:
            result.add_fail("1.5: Yousef submit bid (expect 200)", f"Exception: {str(e)}")
    
    # ========================================================================
    # TEST 2: COMPLIANCE NOT BYPASSED (structured 403)
    # ========================================================================
    print(f"\n{YELLOW}[TEST 2] COMPLIANCE NOT BYPASSED{RESET}")
    print(f"{YELLOW}Testing that compliance rules are enforced with structured 403{RESET}\n")
    
    # 2.1: Login approved driver
    print(f"2.1: Login approved driver ({APPROVED_DRIVER_PHONE})...")
    approved_driver_token, approved_driver_user, error = otp_login(APPROVED_DRIVER_PHONE, "driver")
    if error:
        result.add_fail("2.1: Approved driver OTP login", error)
    else:
        result.add_pass("2.1: Approved driver OTP login",
                       f"HTTP 200, token received, user.role={approved_driver_user.get('role')}, name={approved_driver_user.get('name')}")
    
    # 2.2: Temporarily PUT driver_training_status to IN_PROGRESS
    if approved_driver_token:
        print(f"2.2: Temporarily PUT /api/driver/regulatory (training=IN_PROGRESS)...")
        try:
            resp = requests.put(f"{BASE_URL}/driver/regulatory",
                               json={"driver_training_status": "IN_PROGRESS"},
                               headers={"Authorization": f"Bearer {approved_driver_token}"},
                               timeout=10)
            if resp.status_code != 200:
                result.add_fail("2.2: Temporarily set training=IN_PROGRESS",
                               f"HTTP {resp.status_code}: {resp.text[:200]}")
            else:
                data = resp.json()
                training_status = data.get("driver_training_status")
                result.add_pass("2.2: Temporarily set training=IN_PROGRESS",
                               f"HTTP 200, driver_training_status={training_status}")
        except Exception as e:
            result.add_fail("2.2: Temporarily set training=IN_PROGRESS", f"Exception: {str(e)}")
    
    # 2.3: Customer creates another PUBLISHED shipment
    if customer_token:
        print(f"2.3: Customer creates another PUBLISHED shipment...")
        try:
            shipment_payload2 = {
                "title": "Test Shipment for Compliance Check",
                "description": "Testing compliance enforcement",
                "category": "general",
                "weight": "30",
                "quantity": "1",
                "pickup_location": {
                    "address": "Muscat, Oman",
                    "lat": 23.5880,
                    "lng": 58.3829,
                    "city": "Muscat",
                    "area": "Muscat",
                    "country": "Oman"
                },
                "delivery_location": {
                    "address": "Nizwa, Oman",
                    "lat": 22.9333,
                    "lng": 57.5333,
                    "city": "Nizwa",
                    "area": "Nizwa",
                    "country": "Oman"
                },
                "vehicle_type": "pickup",
                "status": "PUBLISHED"
            }
            resp = requests.post(f"{BASE_URL}/shipments",
                                json=shipment_payload2,
                                headers={"Authorization": f"Bearer {customer_token}"},
                                timeout=10)
            if resp.status_code != 200:
                result.add_fail("2.3: Customer create second PUBLISHED shipment",
                               f"HTTP {resp.status_code}: {resp.text[:200]}")
            else:
                data = resp.json()
                shipment_id2 = data.get("id")
                status = data.get("status")
                result.add_pass("2.3: Customer create second PUBLISHED shipment",
                               f"HTTP 200, shipment_id={shipment_id2}, status={status}")
        except Exception as e:
            result.add_fail("2.3: Customer create second PUBLISHED shipment", f"Exception: {str(e)}")
    
    # 2.4: Approved driver tries to bid (should get 403 with structured detail)
    if approved_driver_token and shipment_id2:
        print(f"2.4: Approved driver POST bid (expect 403 NOT_ELIGIBLE)...")
        try:
            bid_payload = {"price": 40, "note": "Test bid"}
            resp = requests.post(f"{BASE_URL}/shipments/{shipment_id2}/bids",
                                json=bid_payload,
                                headers={"Authorization": f"Bearer {approved_driver_token}"},
                                timeout=10)
            if resp.status_code != 403:
                result.add_fail("2.4: Approved driver bid (expect 403)",
                               f"HTTP {resp.status_code} (expected 403): {resp.text[:500]}")
            else:
                data = resp.json()
                detail = data.get("detail", {})
                if isinstance(detail, dict):
                    code = detail.get("code")
                    reasons = detail.get("reasons", [])
                    has_training_reason = any(
                        r.get("code") == "DRIVER_APP_TRAINING_NOT_COMPLETED" 
                        for r in reasons
                    )
                    if code == "NOT_ELIGIBLE" and has_training_reason:
                        result.add_pass("2.4: Approved driver bid (expect 403)",
                                       f"HTTP 403, detail.code={code}, reasons contains DRIVER_APP_TRAINING_NOT_COMPLETED")
                    else:
                        result.add_fail("2.4: Approved driver bid (expect 403)",
                                       f"HTTP 403 but detail.code={code}, reasons={reasons} (expected NOT_ELIGIBLE with DRIVER_APP_TRAINING_NOT_COMPLETED)")
                else:
                    result.add_fail("2.4: Approved driver bid (expect 403)",
                                   f"HTTP 403 but detail is not a dict: {detail}")
        except Exception as e:
            result.add_fail("2.4: Approved driver bid (expect 403)", f"Exception: {str(e)}")
    
    # 2.5: RESTORE driver_training_status to COMPLETED
    if approved_driver_token:
        print(f"2.5: RESTORE PUT /api/driver/regulatory (training=COMPLETED)...")
        try:
            resp = requests.put(f"{BASE_URL}/driver/regulatory",
                               json={"driver_training_status": "COMPLETED"},
                               headers={"Authorization": f"Bearer {approved_driver_token}"},
                               timeout=10)
            if resp.status_code != 200:
                result.add_fail("2.5: RESTORE training=COMPLETED",
                               f"HTTP {resp.status_code}: {resp.text[:200]}")
            else:
                data = resp.json()
                training_status = data.get("driver_training_status")
                result.add_pass("2.5: RESTORE training=COMPLETED",
                               f"HTTP 200, driver_training_status={training_status}")
        except Exception as e:
            result.add_fail("2.5: RESTORE training=COMPLETED", f"Exception: {str(e)}")
    
    # 2.6: Verify restore worked - check eligibility
    if approved_driver_token:
        print(f"2.6: Verify restore - GET /api/driver/eligibility...")
        try:
            resp = requests.get(f"{BASE_URL}/driver/eligibility",
                               headers={"Authorization": f"Bearer {approved_driver_token}"},
                               timeout=10)
            if resp.status_code != 200:
                result.add_fail("2.6: Verify restore - eligibility check",
                               f"HTTP {resp.status_code}: {resp.text[:200]}")
            else:
                data = resp.json()
                eligible = data.get("eligible")
                if eligible is True:
                    result.add_pass("2.6: Verify restore - eligibility check",
                                   f"HTTP 200, eligible=true (restore successful)")
                else:
                    result.add_fail("2.6: Verify restore - eligibility check",
                                   f"eligible={eligible} (expected true after restore)")
        except Exception as e:
            result.add_fail("2.6: Verify restore - eligibility check", f"Exception: {str(e)}")
    
    # ========================================================================
    # TEST 3: DRIVER PROFILE DATA SOURCE
    # ========================================================================
    print(f"\n{YELLOW}[TEST 3] DRIVER PROFILE DATA SOURCE{RESET}")
    print(f"{YELLOW}Testing that GET /api/auth/me returns vehicle.type for profile{RESET}\n")
    
    if yousef_token:
        print(f"3.1: GET /api/auth/me as Yousef...")
        try:
            resp = requests.get(f"{BASE_URL}/auth/me",
                               headers={"Authorization": f"Bearer {yousef_token}"},
                               timeout=10)
            if resp.status_code != 200:
                result.add_fail("3.1: Yousef GET /auth/me",
                               f"HTTP {resp.status_code}: {resp.text[:200]}")
            else:
                data = resp.json()
                name = data.get("name")
                phone = data.get("phone")
                email = data.get("email")
                vehicle = data.get("vehicle", {})
                vehicle_type = vehicle.get("type") if isinstance(vehicle, dict) else None
                
                # Check all required fields
                has_name = name is not None
                has_phone = phone is not None
                has_email = "email" in data  # email field present (may be empty string)
                has_vehicle_type = vehicle_type == "pickup"
                
                if has_name and has_phone and has_email and has_vehicle_type:
                    result.add_pass("3.1: Yousef GET /auth/me",
                                   f"HTTP 200, name={name}, phone={phone}, email='{email}', vehicle.type={vehicle_type}")
                else:
                    missing = []
                    if not has_name: missing.append("name")
                    if not has_phone: missing.append("phone")
                    if not has_email: missing.append("email field")
                    if not has_vehicle_type: missing.append(f"vehicle.type='pickup' (got {vehicle_type})")
                    result.add_fail("3.1: Yousef GET /auth/me",
                                   f"Missing or incorrect fields: {', '.join(missing)}")
        except Exception as e:
            result.add_fail("3.1: Yousef GET /auth/me", f"Exception: {str(e)}")
    
    # ========================================================================
    # TEST 4: REGRESSION (light)
    # ========================================================================
    print(f"\n{YELLOW}[TEST 4] REGRESSION (light){RESET}")
    print(f"{YELLOW}Testing basic auth and flow endpoints{RESET}\n")
    
    # 4.1: Admin login
    print(f"4.1: Admin login...")
    admin_token, error = admin_login()
    if error:
        result.add_fail("4.1: Admin login", error)
    else:
        result.add_pass("4.1: Admin login", f"HTTP 200, token received")
    
    # 4.2: Customer OTP login (already done, just verify)
    if customer_token:
        result.add_pass("4.2: Customer OTP login", "Already verified in test 1.3")
    else:
        result.add_fail("4.2: Customer OTP login", "Customer token not available")
    
    # 4.3: Driver OTP logins (+96890000002, +96890000003, +96890000004)
    driver_phones = ["+96890000002", "+96890000003", "+96890000004"]
    for i, phone in enumerate(driver_phones, start=3):
        print(f"4.{i}: Driver OTP login ({phone})...")
        token, user, error = otp_login(phone, "driver")
        if error:
            result.add_fail(f"4.{i}: Driver OTP login ({phone})", error)
        else:
            result.add_pass(f"4.{i}: Driver OTP login ({phone})",
                           f"HTTP 200, token received, name={user.get('name')}")
    
    # 4.6: GET /api/marketplace/shipments as Yousef
    if yousef_token:
        print(f"4.6: GET /api/marketplace/shipments as Yousef...")
        try:
            resp = requests.get(f"{BASE_URL}/marketplace/shipments",
                               headers={"Authorization": f"Bearer {yousef_token}"},
                               timeout=10)
            if resp.status_code != 200:
                result.add_fail("4.6: Yousef GET marketplace/shipments",
                               f"HTTP {resp.status_code}: {resp.text[:200]}")
            else:
                data = resp.json()
                count = len(data) if isinstance(data, list) else 0
                result.add_pass("4.6: Yousef GET marketplace/shipments",
                               f"HTTP 200, {count} shipments returned")
        except Exception as e:
            result.add_fail("4.6: Yousef GET marketplace/shipments", f"Exception: {str(e)}")
    
    # 4.7: Customer creates shipment (already done in 1.4)
    if shipment_id:
        result.add_pass("4.7: Customer creates shipment", f"Already verified in test 1.4, shipment_id={shipment_id}")
    else:
        result.add_fail("4.7: Customer creates shipment", "Shipment not created in test 1.4")
    
    # 4.8: Basic accept flow - customer accepts Yousef's bid
    if customer_token and bid_id:
        print(f"4.8: Customer POST /api/bids/{bid_id}/accept...")
        try:
            resp = requests.post(f"{BASE_URL}/bids/{bid_id}/accept",
                                headers={"Authorization": f"Bearer {customer_token}"},
                                timeout=10)
            if resp.status_code != 200:
                result.add_fail("4.8: Customer accept Yousef's bid",
                               f"HTTP {resp.status_code}: {resp.text[:500]}")
            else:
                data = resp.json()
                trip_id = data.get("id")
                trip_status = data.get("status")
                result.add_pass("4.8: Customer accept Yousef's bid",
                               f"HTTP 200, trip created, trip_id={trip_id}, status={trip_status}")
        except Exception as e:
            result.add_fail("4.8: Customer accept Yousef's bid", f"Exception: {str(e)}")
    elif not bid_id:
        result.add_fail("4.8: Customer accept Yousef's bid", "No bid_id available (test 1.5 may have failed)")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    success = result.summary()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
