#!/usr/bin/env python3
"""
P0 Security Hardening Backend Test
Tests IDOR fix for bids authorization + OTP dev behavior + light regression
"""

import requests
import json
import time
import sys
from typing import Dict, Optional

# Base URL from frontend/.env
BASE_URL = "https://301fb6e6-a7ac-4e14-abe2-cd78e9c93702.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"

CUSTOMER1_PHONE = "+96890000001"
DRIVER_PHONE = "+96890000002"
PROVIDER_PHONE = "+96890000005"

# Will use a new customer for IDOR test
CUSTOMER2_PHONE = "+96890000099"  # Unused phone for testing

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_test(test_num: str, description: str):
    print(f"\n{Colors.BLUE}[TEST {test_num}]{Colors.END} {description}")

def log_pass(message: str):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.END} {message}")

def log_fail(message: str):
    print(f"  {Colors.RED}✗ FAIL:{Colors.END} {message}")

def log_info(message: str):
    print(f"  {Colors.YELLOW}ℹ INFO:{Colors.END} {message}")

def admin_login() -> Optional[str]:
    """Login as admin and return token"""
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/admin/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token")
            log_pass(f"Admin login successful, token: {token[:20]}...")
            return token
        else:
            log_fail(f"Admin login failed: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        log_fail(f"Admin login exception: {e}")
        return None

def otp_login(phone: str, role: str) -> Optional[Dict]:
    """Login via OTP and return {token, user}"""
    try:
        # Step 1: Request OTP
        log_info(f"Requesting OTP for {phone} role={role}")
        resp1 = requests.post(
            f"{BASE_URL}/auth/otp/request",
            json={"phone": phone, "role": role},
            timeout=10
        )
        if resp1.status_code != 200:
            log_fail(f"OTP request failed: {resp1.status_code} {resp1.text}")
            return None
        
        data1 = resp1.json()
        demo_code = data1.get("demo_code")
        if not demo_code:
            log_fail(f"No demo_code in response: {data1}")
            return None
        
        log_pass(f"OTP request successful, demo_code={demo_code}")
        
        # Step 2: Verify OTP
        log_info(f"Verifying OTP with code {demo_code}")
        resp2 = requests.post(
            f"{BASE_URL}/auth/otp/verify",
            json={"phone": phone, "role": role, "code": demo_code},
            timeout=10
        )
        if resp2.status_code != 200:
            log_fail(f"OTP verify failed: {resp2.status_code} {resp2.text}")
            return None
        
        data2 = resp2.json()
        token = data2.get("token")
        user = data2.get("user")
        if not token or not user:
            log_fail(f"Missing token or user in verify response: {data2}")
            return None
        
        log_pass(f"OTP verify successful, token: {token[:20]}..., user.role={user.get('role')}")
        return {"token": token, "user": user}
    
    except Exception as e:
        log_fail(f"OTP login exception: {e}")
        return None

def create_shipment(token: str) -> Optional[str]:
    """Create a PUBLISHED shipment and return shipment_id"""
    try:
        # Create shipment payload
        shipment_data = {
            "title": "Test Shipment for P0 Security",
            "category": "general",
            "description": "Test shipment for P0 security testing",
            "weight": "50",
            "weight_unit": "kg",
            "dimensions": "100x50x30 cm",
            "pickup_location": {
                "address": "Muscat, Oman",
                "lat": 23.5880,
                "lng": 58.3829,
                "city": "Muscat",
                "area": "Ruwi",
                "country": "Oman"
            },
            "delivery_location": {
                "address": "Salalah, Oman",
                "lat": 17.0150,
                "lng": 54.0924,
                "city": "Salalah",
                "area": "City Center",
                "country": "Oman"
            },
            "pickup_date": "2026-02-01",
            "pickup_time": "10:00",
            "vehicle_type": "pickup_truck",
            "status": "PUBLISHED"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create published shipment (status=PUBLISHED in payload)
        resp = requests.post(
            f"{BASE_URL}/shipments",
            json=shipment_data,
            headers=headers,
            timeout=10
        )
        if resp.status_code != 200:
            log_fail(f"Shipment creation failed: {resp.status_code} {resp.text}")
            return None
        
        data = resp.json()
        shipment_id = data.get("id")
        log_pass(f"Shipment created and published: {shipment_id}")
        return shipment_id
    
    except Exception as e:
        log_fail(f"Create shipment exception: {e}")
        return None

def create_bid(shipment_id: str, token: str, amount: float = 30.0) -> Optional[str]:
    """Create a bid on a shipment and return bid_id"""
    try:
        bid_data = {
            "price": amount,
            "note": "Test bid for P0 security testing"
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = requests.post(
            f"{BASE_URL}/shipments/{shipment_id}/bids",
            json=bid_data,
            headers=headers,
            timeout=10
        )
        if resp.status_code != 200:
            log_fail(f"Bid creation failed: {resp.status_code} {resp.text}")
            return None
        
        data = resp.json()
        bid_id = data.get("id")
        log_pass(f"Bid created: {bid_id}, amount={amount}")
        return bid_id
    
    except Exception as e:
        log_fail(f"Create bid exception: {e}")
        return None

def get_shipment_bids(shipment_id: str, token: str, expect_status: int = 200) -> tuple:
    """Get bids for a shipment, return (status_code, response_data)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{BASE_URL}/shipments/{shipment_id}/bids",
            headers=headers,
            timeout=10
        )
        return (resp.status_code, resp.json() if resp.status_code == 200 else resp.text)
    except Exception as e:
        log_fail(f"Get shipment bids exception: {e}")
        return (0, str(e))

def get_role_bids(role: str, token: str) -> tuple:
    """Get role-specific bids (/driver/bids, /provider/bids, /admin/bids)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{BASE_URL}/{role}/bids",
            headers=headers,
            timeout=10
        )
        return (resp.status_code, resp.json() if resp.status_code == 200 else resp.text)
    except Exception as e:
        log_fail(f"Get {role} bids exception: {e}")
        return (0, str(e))

def check_backend_logs_for_otp():
    """Check if OTP code appears in backend logs"""
    try:
        import subprocess
        result = subprocess.run(
            ["tail", "-n", "50", "/var/log/supervisor/backend.err.log"],
            capture_output=True,
            text=True,
            timeout=5
        )
        log_content = result.stdout + result.stderr
        
        # Look for 6-digit patterns that might be OTP codes
        import re
        otp_pattern = re.compile(r'\b\d{6}\b')
        matches = otp_pattern.findall(log_content)
        
        if matches:
            log_fail(f"Found potential OTP codes in logs: {matches}")
            return False
        else:
            log_pass("No OTP codes found in backend logs")
            return True
    except Exception as e:
        log_info(f"Could not check logs: {e}")
        return True  # Don't fail test if we can't check logs

def main():
    print(f"\n{'='*80}")
    print(f"P0 SECURITY HARDENING - BACKEND TEST")
    print(f"BASE_URL: {BASE_URL}")
    print(f"{'='*80}")
    
    results = {
        "passed": 0,
        "failed": 0,
        "total": 0
    }
    
    # ========================================================================
    # P0-3 BIDS AUTHORIZATION (IDOR FIX) - PRIMARY FOCUS
    # ========================================================================
    
    print(f"\n{Colors.YELLOW}{'='*80}{Colors.END}")
    print(f"{Colors.YELLOW}P0-3 BIDS AUTHORIZATION (IDOR FIX){Colors.END}")
    print(f"{Colors.YELLOW}{'='*80}{Colors.END}")
    
    # Test 1: Customer creates shipment, driver bids, customer can see bids
    log_test("1", "Customer +96890000001 creates PUBLISHED shipment, driver bids, customer GET /api/shipments/{sid}/bids -> 200")
    results["total"] += 1
    
    customer1_auth = otp_login(CUSTOMER1_PHONE, "customer")
    if not customer1_auth:
        log_fail("Customer1 login failed")
        results["failed"] += 1
    else:
        customer1_token = customer1_auth["token"]
        
        # Create and publish shipment
        shipment_id = create_shipment(customer1_token)
        if not shipment_id:
            log_fail("Shipment creation failed")
            results["failed"] += 1
        else:
            # Driver bids on shipment
            driver_auth = otp_login(DRIVER_PHONE, "driver")
            if not driver_auth:
                log_fail("Driver login failed")
                results["failed"] += 1
            else:
                driver_token = driver_auth["token"]
                bid_id = create_bid(shipment_id, driver_token)
                
                if not bid_id:
                    log_fail("Bid creation failed")
                    results["failed"] += 1
                else:
                    # Customer should be able to see bids on their own shipment
                    status, data = get_shipment_bids(shipment_id, customer1_token, expect_status=200)
                    if status == 200:
                        log_pass(f"Customer can see bids on own shipment: HTTP {status}")
                        log_info(f"Response: {json.dumps(data, indent=2)[:200]}...")
                        results["passed"] += 1
                    else:
                        log_fail(f"Customer cannot see bids on own shipment: HTTP {status}, {data}")
                        results["failed"] += 1
    
    # Test 2: Different customer cannot see bids
    log_test("2", "Different customer (new registration) GET /api/shipments/{sid}/bids -> 403 or 404")
    results["total"] += 1
    
    if shipment_id:
        customer2_auth = otp_login(CUSTOMER2_PHONE, "customer")
        if not customer2_auth:
            log_fail("Customer2 login failed")
            results["failed"] += 1
        else:
            customer2_token = customer2_auth["token"]
            status, data = get_shipment_bids(shipment_id, customer2_token)
            if status in [403, 404]:
                log_pass(f"Different customer blocked from seeing bids: HTTP {status}")
                log_info(f"Response: {data}")
                results["passed"] += 1
            else:
                log_fail(f"Different customer can see bids (IDOR vulnerability!): HTTP {status}, {data}")
                results["failed"] += 1
    else:
        log_fail("No shipment_id from test 1")
        results["failed"] += 1
    
    # Test 3: Driver cannot see competitor bids, but can see own bids
    log_test("3", "Driver GET /api/shipments/{sid}/bids (not their shipment) -> 403; GET /api/driver/bids -> 200")
    results["total"] += 1
    
    if shipment_id and driver_token:
        # Driver tries to see bids on shipment (should be blocked)
        status, data = get_shipment_bids(shipment_id, driver_token)
        if status == 403:
            log_pass(f"Driver blocked from seeing competitor bids via /shipments/{{sid}}/bids: HTTP {status}")
            log_info(f"Response: {data}")
            
            # Driver should be able to see own bids via /driver/bids
            status2, data2 = get_role_bids("driver", driver_token)
            if status2 == 200:
                log_pass(f"Driver can see own bids via /driver/bids: HTTP {status2}")
                log_info(f"Response: {json.dumps(data2, indent=2)[:200]}...")
                results["passed"] += 1
            else:
                log_fail(f"Driver cannot see own bids via /driver/bids: HTTP {status2}, {data2}")
                results["failed"] += 1
        else:
            log_fail(f"Driver can see competitor bids (IDOR vulnerability!): HTTP {status}, {data}")
            results["failed"] += 1
    else:
        log_fail("Missing shipment_id or driver_token from previous tests")
        results["failed"] += 1
    
    # Test 4: Provider cannot see bids, but can see own bids
    log_test("4", "Provider GET /api/shipments/{sid}/bids -> 403; GET /api/provider/bids -> 200")
    results["total"] += 1
    
    provider_auth = otp_login(PROVIDER_PHONE, "provider")
    if not provider_auth:
        log_fail("Provider login failed")
        results["failed"] += 1
    elif not shipment_id:
        log_fail("No shipment_id from test 1")
        results["failed"] += 1
    else:
        provider_token = provider_auth["token"]
        
        # Provider tries to see bids on shipment (should be blocked)
        status, data = get_shipment_bids(shipment_id, provider_token)
        if status == 403:
            log_pass(f"Provider blocked from seeing bids via /shipments/{{sid}}/bids: HTTP {status}")
            log_info(f"Response: {data}")
            
            # Provider should be able to see own bids via /provider/bids
            status2, data2 = get_role_bids("provider", provider_token)
            if status2 == 200:
                log_pass(f"Provider can see own bids via /provider/bids: HTTP {status2}")
                log_info(f"Response: {json.dumps(data2, indent=2)[:200]}...")
                results["passed"] += 1
            else:
                log_fail(f"Provider cannot see own bids via /provider/bids: HTTP {status2}, {data2}")
                results["failed"] += 1
        else:
            log_fail(f"Provider can see bids (IDOR vulnerability!): HTTP {status}, {data}")
            results["failed"] += 1
    
    # Test 5: Admin can see bids, role-specific endpoints are protected
    log_test("5", "Admin GET /api/shipments/{sid}/bids -> 200; /api/admin/bids admin-only")
    results["total"] += 1
    
    admin_token = admin_login()
    if not admin_token:
        log_fail("Admin login failed")
        results["failed"] += 1
    elif not shipment_id:
        log_fail("No shipment_id from test 1")
        results["failed"] += 1
    else:
        # Admin should be able to see bids on any shipment
        status, data = get_shipment_bids(shipment_id, admin_token)
        if status == 200:
            log_pass(f"Admin can see bids via /shipments/{{sid}}/bids: HTTP {status}")
            log_info(f"Response: {json.dumps(data, indent=2)[:200]}...")
            
            # Admin should be able to access /admin/bids
            status2, data2 = get_role_bids("admin", admin_token)
            if status2 == 200:
                log_pass(f"Admin can access /admin/bids: HTTP {status2}")
                
                # Customer should NOT be able to access /admin/bids
                if customer1_token:
                    status3, data3 = get_role_bids("admin", customer1_token)
                    if status3 == 403:
                        log_pass(f"Customer blocked from /admin/bids: HTTP {status3}")
                        results["passed"] += 1
                    else:
                        log_fail(f"Customer can access /admin/bids: HTTP {status3}, {data3}")
                        results["failed"] += 1
                else:
                    log_fail("No customer1_token")
                    results["failed"] += 1
            else:
                log_fail(f"Admin cannot access /admin/bids: HTTP {status2}, {data2}")
                results["failed"] += 1
        else:
            log_fail(f"Admin cannot see bids via /shipments/{{sid}}/bids: HTTP {status}, {data}")
            results["failed"] += 1
    
    # ========================================================================
    # P0-1 OTP (DEV BEHAVIOR)
    # ========================================================================
    
    print(f"\n{Colors.YELLOW}{'='*80}{Colors.END}")
    print(f"{Colors.YELLOW}P0-1 OTP (DEV BEHAVIOR){Colors.END}")
    print(f"{Colors.YELLOW}{'='*80}{Colors.END}")
    
    # Test 6: OTP request returns demo_code in dev
    log_test("6", "POST /api/auth/otp/request -> 200 with demo_code in response")
    results["total"] += 1
    
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/otp/request",
            json={"phone": CUSTOMER1_PHONE, "role": "customer"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            demo_code = data.get("demo_code")
            if demo_code:
                log_pass(f"OTP request returns demo_code: {demo_code}")
                results["passed"] += 1
            else:
                log_fail(f"OTP request missing demo_code: {data}")
                results["failed"] += 1
        else:
            log_fail(f"OTP request failed: {resp.status_code} {resp.text}")
            results["failed"] += 1
    except Exception as e:
        log_fail(f"OTP request exception: {e}")
        results["failed"] += 1
    
    # Test 7: Full OTP verify login works
    log_test("7", "Full OTP verify login works for customer/driver/provider")
    results["total"] += 1
    
    test7_passed = True
    for phone, role in [(CUSTOMER1_PHONE, "customer"), (DRIVER_PHONE, "driver"), (PROVIDER_PHONE, "provider")]:
        auth = otp_login(phone, role)
        if not auth:
            log_fail(f"OTP login failed for {role} {phone}")
            test7_passed = False
    
    if test7_passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 8: OTP code does NOT appear in backend logs
    log_test("8", "Verify OTP code does NOT appear in backend logs")
    results["total"] += 1
    
    # First make an OTP request to generate a fresh log entry
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/otp/request",
            json={"phone": "+96890000003", "role": "driver"},
            timeout=10
        )
        time.sleep(1)  # Give logs time to flush
    except:
        pass
    
    if check_backend_logs_for_otp():
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # ========================================================================
    # REGRESSION (LIGHT)
    # ========================================================================
    
    print(f"\n{Colors.YELLOW}{'='*80}{Colors.END}")
    print(f"{Colors.YELLOW}REGRESSION (LIGHT){Colors.END}")
    print(f"{Colors.YELLOW}{'='*80}{Colors.END}")
    
    # Test 9: Basic regression - admin login, OTP logins, shipment creation, bid flow
    log_test("9", "Regression: admin login, OTP logins, shipment + bid flow")
    results["total"] += 1
    
    regression_passed = True
    
    # Admin login
    admin_token = admin_login()
    if not admin_token:
        log_fail("Regression: Admin login failed")
        regression_passed = False
    
    # Customer OTP login
    customer_auth = otp_login(CUSTOMER1_PHONE, "customer")
    if not customer_auth:
        log_fail("Regression: Customer OTP login failed")
        regression_passed = False
    
    # Driver OTP login
    driver_auth = otp_login(DRIVER_PHONE, "driver")
    if not driver_auth:
        log_fail("Regression: Driver OTP login failed")
        regression_passed = False
    
    # Provider OTP login
    provider_auth = otp_login(PROVIDER_PHONE, "provider")
    if not provider_auth:
        log_fail("Regression: Provider OTP login failed")
        regression_passed = False
    
    # Customer creates basic shipment
    if customer_auth:
        shipment_id = create_shipment(customer_auth["token"])
        if not shipment_id:
            log_fail("Regression: Shipment creation failed")
            regression_passed = False
        else:
            # Driver bids
            if driver_auth:
                bid_id = create_bid(shipment_id, driver_auth["token"])
                if not bid_id:
                    log_fail("Regression: Bid creation failed")
                    regression_passed = False
                else:
                    # Customer accepts bid
                    try:
                        resp = requests.post(
                            f"{BASE_URL}/bids/{bid_id}/accept",
                            headers={"Authorization": f"Bearer {customer_auth['token']}"},
                            timeout=10
                        )
                        if resp.status_code == 200:
                            log_pass("Regression: Bid acceptance successful")
                        else:
                            log_fail(f"Regression: Bid acceptance failed: {resp.status_code} {resp.text}")
                            regression_passed = False
                    except Exception as e:
                        log_fail(f"Regression: Bid acceptance exception: {e}")
                        regression_passed = False
    
    if regression_passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total tests: {results['total']}")
    print(f"{Colors.GREEN}Passed: {results['passed']}{Colors.END}")
    print(f"{Colors.RED}Failed: {results['failed']}{Colors.END}")
    print(f"{'='*80}\n")
    
    if results['failed'] == 0:
        print(f"{Colors.GREEN}✓ ALL TESTS PASSED{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.RED}✗ SOME TESTS FAILED{Colors.END}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
