#!/usr/bin/env python3
"""
CARGO Backend Phase 3A Test Suite
Tests Admin User Management, RBAC staff roles, Finance operations + authorization
"""
import requests
import sys
import json
from typing import Dict, Any, Optional

# Base URL from frontend/.env
BASE_URL = "https://c2f4a448-f541-42c6-9812-a522b5e0e1d4.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@cargo.om", "password": "admin123"}
TEST_USERS = {
    "customer": {"phone": "+96890000001", "role": "customer"},
    "driver": {"phone": "+96890000002", "role": "driver"},
    "provider": {"phone": "+96890000005", "role": "provider"},
}

# Color codes
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
        self.warnings = []
    
    def add_pass(self, test_name: str, detail: str = ""):
        self.passed += 1
        msg = f"{GREEN}✓{RESET} {test_name}"
        if detail:
            msg += f"\n  {detail}"
        print(msg)
    
    def add_fail(self, test_name: str, reason: str):
        self.failed += 1
        error_msg = f"{test_name}: {reason}"
        self.errors.append(error_msg)
        print(f"{RED}✗{RESET} {test_name}")
        print(f"  {RED}Reason: {reason}{RESET}")
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)
        print(f"{YELLOW}⚠{RESET} {msg}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total: {total} | {GREEN}Passed: {self.passed}{RESET} | {RED}Failed: {self.failed}{RESET}")
        if self.warnings:
            print(f"\n{YELLOW}WARNINGS:{RESET}")
            for w in self.warnings:
                print(f"  - {w}")
        if self.errors:
            print(f"\n{RED}FAILED TESTS:{RESET}")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")
        print(f"{'='*70}\n")
        return self.failed == 0

# Global storage for test data
test_data = {
    "super_admin_token": None,
    "finance_accountant": {"email": None, "password": None, "token": None, "id": None},
    "document_reviewer": {"email": None, "password": None, "token": None, "id": None},
    "manager": {"email": None, "password": None, "token": None, "id": None},
    "customer_id": None,
    "driver_id": None,
    "adjustment_txn_id": None,
    "refund_txn_id": None,
}

def req(method: str, path: str, token: str = None, json_data: dict = None, params: dict = None) -> tuple:
    """Helper to make HTTP requests"""
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=20)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=json_data, timeout=20)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=json_data, timeout=20)
        else:
            return None, f"Unsupported method: {method}"
        
        return resp, None
    except requests.exceptions.Timeout:
        return None, f"Timeout after 20s"
    except requests.exceptions.ConnectionError as e:
        return None, f"Connection error: {str(e)[:100]}"
    except Exception as e:
        return None, f"Exception: {type(e).__name__}: {str(e)[:100]}"

def test_super_admin_login(result: TestResult):
    """Test 0: Super admin login"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 0: SUPER ADMIN LOGIN{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    resp, error = req("POST", "/auth/admin/login", json_data=ADMIN_CREDS)
    if error:
        result.add_fail("Super admin login", error)
        return False
    
    if resp.status_code != 200:
        result.add_fail("Super admin login", f"Status {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    token = data.get("token")
    user = data.get("user")
    
    if not token:
        result.add_fail("Super admin login", "No token in response")
        return False
    
    test_data["super_admin_token"] = token
    test_data["super_admin_id"] = user.get("id")
    result.add_pass("Super admin login", f"Token received, user role: {user.get('role')}")
    
    # Get permissions
    resp, error = req("GET", "/admin/me/permissions", token=token)
    if error or resp.status_code != 200:
        result.add_fail("Super admin permissions", f"Status {resp.status_code if resp else 'error'}")
        return False
    
    perms_data = resp.json()
    role_key = perms_data.get("role_key")
    permissions = perms_data.get("permissions", [])
    
    if role_key != "super_admin":
        result.add_fail("Super admin role_key", f"Expected 'super_admin', got '{role_key}'")
        return False
    
    result.add_pass("Super admin permissions", f"role_key={role_key}, {len(permissions)} permissions")
    return True

def test_roles_endpoint(result: TestResult):
    """Test 1: GET /admin/roles"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 1: ROLES ENDPOINT{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    token = test_data["super_admin_token"]
    resp, error = req("GET", "/admin/roles", token=token)
    
    if error:
        result.add_fail("GET /admin/roles", error)
        return
    
    if resp.status_code != 200:
        result.add_fail("GET /admin/roles", f"Status {resp.status_code}: {resp.text}")
        return
    
    roles = resp.json()
    result.add_pass("GET /admin/roles", f"Returned {len(roles)} roles")
    
    # Check for required roles
    required_roles = ["super_admin", "manager", "supervisor", "document_reviewer", 
                     "finance_accountant", "ministry_supervisor"]
    role_keys = [r.get("key") for r in roles]
    
    missing = [r for r in required_roles if r not in role_keys]
    if missing:
        result.add_fail("Required roles check", f"Missing roles: {missing}")
        return
    
    result.add_pass("Required roles check", f"All 6 canonical roles present")
    
    # Report permissions for finance_accountant and document_reviewer
    for role in roles:
        if role.get("key") == "finance_accountant":
            perms = role.get("permissions", [])
            result.add_pass("finance_accountant permissions", 
                          f"{len(perms)} permissions: {', '.join(perms[:5])}...")
        elif role.get("key") == "document_reviewer":
            perms = role.get("permissions", [])
            result.add_pass("document_reviewer permissions", 
                          f"{len(perms)} permissions: {', '.join(perms)}")

def test_create_staff(result: TestResult):
    """Test 2: Create 3 staff admins"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 2: CREATE STAFF ADMINS{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    token = test_data["super_admin_token"]
    
    # Create finance_accountant
    email1 = f"finance.test.{hash('finance') % 10000}@cargo.om"
    payload1 = {
        "name": "Finance Test User",
        "email": email1,
        "password": "finance123",
        "admin_role_key": "finance_accountant"
    }
    
    resp, error = req("POST", "/admin/admins", token=token, json_data=payload1)
    if error or resp.status_code != 200:
        result.add_fail("Create finance_accountant", 
                       f"Status {resp.status_code if resp else 'error'}: {resp.text if resp else error}")
    else:
        data = resp.json()
        test_data["finance_accountant"]["email"] = email1
        test_data["finance_accountant"]["password"] = "finance123"
        test_data["finance_accountant"]["id"] = data.get("id")
        result.add_pass("Create finance_accountant", f"Email: {email1}, ID: {data.get('id')}")
    
    # Create document_reviewer
    email2 = f"reviewer.test.{hash('reviewer') % 10000}@cargo.om"
    payload2 = {
        "name": "Document Reviewer Test",
        "email": email2,
        "password": "reviewer123",
        "admin_role_key": "document_reviewer"
    }
    
    resp, error = req("POST", "/admin/admins", token=token, json_data=payload2)
    if error or resp.status_code != 200:
        result.add_fail("Create document_reviewer", 
                       f"Status {resp.status_code if resp else 'error'}: {resp.text if resp else error}")
    else:
        data = resp.json()
        test_data["document_reviewer"]["email"] = email2
        test_data["document_reviewer"]["password"] = "reviewer123"
        test_data["document_reviewer"]["id"] = data.get("id")
        result.add_pass("Create document_reviewer", f"Email: {email2}, ID: {data.get('id')}")
    
    # Create manager
    email3 = f"manager.test.{hash('manager') % 10000}@cargo.om"
    payload3 = {
        "name": "Manager Test User",
        "email": email3,
        "password": "manager123",
        "admin_role_key": "manager"
    }
    
    resp, error = req("POST", "/admin/admins", token=token, json_data=payload3)
    if error or resp.status_code != 200:
        result.add_fail("Create manager", 
                       f"Status {resp.status_code if resp else 'error'}: {resp.text if resp else error}")
    else:
        data = resp.json()
        test_data["manager"]["email"] = email3
        test_data["manager"]["password"] = "manager123"
        test_data["manager"]["id"] = data.get("id")
        result.add_pass("Create manager", f"Email: {email3}, ID: {data.get('id')}")

def test_authorization_matrix(result: TestResult):
    """Test 3: Authorization matrix - permission enforcement"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 3: AUTHORIZATION MATRIX{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    # Login finance_accountant
    if test_data["finance_accountant"]["email"]:
        resp, error = req("POST", "/auth/admin/login", json_data={
            "email": test_data["finance_accountant"]["email"],
            "password": test_data["finance_accountant"]["password"]
        })
        if resp and resp.status_code == 200:
            test_data["finance_accountant"]["token"] = resp.json().get("token")
            result.add_pass("finance_accountant login", "Token received")
        else:
            result.add_fail("finance_accountant login", f"Status {resp.status_code if resp else 'error'}")
    
    # Login document_reviewer
    if test_data["document_reviewer"]["email"]:
        resp, error = req("POST", "/auth/admin/login", json_data={
            "email": test_data["document_reviewer"]["email"],
            "password": test_data["document_reviewer"]["password"]
        })
        if resp and resp.status_code == 200:
            test_data["document_reviewer"]["token"] = resp.json().get("token")
            result.add_pass("document_reviewer login", "Token received")
        else:
            result.add_fail("document_reviewer login", f"Status {resp.status_code if resp else 'error'}")
    
    # Test 3.1: finance_accountant can access finance endpoints
    fa_token = test_data["finance_accountant"]["token"]
    if fa_token:
        resp, _ = req("GET", "/admin/finance/stats", token=fa_token)
        if resp and resp.status_code == 200:
            result.add_pass("finance_accountant: GET /admin/finance/stats", "200 OK")
        else:
            result.add_fail("finance_accountant: GET /admin/finance/stats", 
                          f"Status {resp.status_code if resp else 'error'}")
        
        resp, _ = req("GET", "/admin/finance/transactions", token=fa_token)
        if resp and resp.status_code == 200:
            result.add_pass("finance_accountant: GET /admin/finance/transactions", "200 OK")
        else:
            result.add_fail("finance_accountant: GET /admin/finance/transactions", 
                          f"Status {resp.status_code if resp else 'error'}")
    
    # Test 3.2: document_reviewer CANNOT access finance stats (403)
    dr_token = test_data["document_reviewer"]["token"]
    if dr_token:
        resp, _ = req("GET", "/admin/finance/stats", token=dr_token)
        if resp and resp.status_code == 403:
            result.add_pass("document_reviewer: GET /admin/finance/stats", "403 Forbidden (correct)")
        else:
            result.add_fail("document_reviewer: GET /admin/finance/stats", 
                          f"Expected 403, got {resp.status_code if resp else 'error'}")
    
    # Test 3.3: document_reviewer CANNOT edit users (403)
    if dr_token and test_data.get("customer_id"):
        resp, _ = req("PUT", f"/admin/users/{test_data['customer_id']}", 
                     token=dr_token, json_data={"name": "Test Edit"})
        if resp and resp.status_code == 403:
            result.add_pass("document_reviewer: PUT /admin/users/{id}", "403 Forbidden (correct)")
        else:
            result.add_fail("document_reviewer: PUT /admin/users/{id}", 
                          f"Expected 403, got {resp.status_code if resp else 'error'}")
    
    # Test 3.4: finance_accountant CANNOT reverse transactions (403, only super_admin)
    if fa_token and test_data.get("adjustment_txn_id"):
        resp, _ = req("POST", f"/admin/finance/transactions/{test_data['adjustment_txn_id']}/reverse",
                     token=fa_token, json_data={"reason": "test"})
        if resp and resp.status_code == 403:
            result.add_pass("finance_accountant: POST /admin/finance/transactions/{id}/reverse", 
                          "403 Forbidden (correct, only super_admin)")
        else:
            result.add_fail("finance_accountant: POST /admin/finance/transactions/{id}/reverse", 
                          f"Expected 403, got {resp.status_code if resp else 'error'}")
    
    # Test 3.5: No Authorization header -> 401
    resp, _ = req("GET", "/admin/finance/stats")
    if resp and resp.status_code == 401:
        result.add_pass("No Authorization header: GET /admin/finance/stats", "401 Unauthorized (correct)")
    else:
        result.add_fail("No Authorization header: GET /admin/finance/stats", 
                      f"Expected 401, got {resp.status_code if resp else 'error'}")

def test_user_management(result: TestResult):
    """Test 4: User management operations"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 4: USER MANAGEMENT{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    token = test_data["super_admin_token"]
    
    # Test 4.1: GET /admin/users?role=customer
    resp, error = req("GET", "/admin/users", token=token, params={"role": "customer"})
    if error or not resp or resp.status_code != 200:
        result.add_fail("GET /admin/users?role=customer", 
                       f"Status {resp.status_code if resp else 'error'}")
        return
    
    customers = resp.json()
    result.add_pass("GET /admin/users?role=customer", f"Found {len(customers)} customers")
    
    # Find demo customer +96890000001
    demo_customer = None
    for c in customers:
        if c.get("phone") == "+96890000001":
            demo_customer = c
            test_data["customer_id"] = c.get("id")
            break
    
    if not demo_customer:
        result.add_fail("Find demo customer +96890000001", "Not found in customer list")
        return
    
    # Check normalized status field
    if "status" in demo_customer:
        result.add_pass("Demo customer status field", f"status={demo_customer.get('status')}")
    else:
        result.add_warning("Demo customer missing 'status' field (should be normalized)")
    
    result.add_pass("Find demo customer +96890000001", 
                   f"ID: {demo_customer.get('id')}, Name: {demo_customer.get('name')}")
    
    # Test 4.2: GET /admin/users?q=96890000001 (search)
    resp, error = req("GET", "/admin/users", token=token, params={"q": "96890000001"})
    if error or not resp or resp.status_code != 200:
        result.add_fail("GET /admin/users?q=96890000001", 
                       f"Status {resp.status_code if resp else 'error'}")
    else:
        search_results = resp.json()
        found = any(u.get("phone") == "+96890000001" for u in search_results)
        if found:
            result.add_pass("GET /admin/users?q=96890000001", "Customer found in search results")
        else:
            result.add_fail("GET /admin/users?q=96890000001", "Customer NOT found in search")
    
    # Test 4.3: PUT /admin/users/{customerId} - edit notes and name
    customer_id = test_data["customer_id"]
    if customer_id:
        resp, error = req("PUT", f"/admin/users/{customer_id}", token=token, 
                         json_data={"notes": "VIP", "name": "أحمد البلوشي"})
        if error or not resp or resp.status_code != 200:
            result.add_fail("PUT /admin/users/{customerId}", 
                           f"Status {resp.status_code if resp else 'error'}: {resp.text if resp else error}")
        else:
            updated = resp.json()
            result.add_pass("PUT /admin/users/{customerId}", 
                           f"Updated notes={updated.get('notes')}, name={updated.get('name')}")
    
    # Test 4.4: POST /admin/users/{customerId}/status {status:"disabled"}
    if customer_id:
        resp, error = req("POST", f"/admin/users/{customer_id}/status", token=token,
                         json_data={"status": "disabled"})
        if error or not resp or resp.status_code != 200:
            result.add_fail("POST /admin/users/{customerId}/status (disable)", 
                           f"Status {resp.status_code if resp else 'error'}")
        else:
            result.add_pass("POST /admin/users/{customerId}/status (disable)", "200 OK")
            
            # Test 4.5: Attempt customer login (should be 403 ACCOUNT_DISABLED)
            # OTP request
            otp_resp, _ = req("POST", "/auth/otp/request", 
                            json_data={"phone": "+96890000001", "role": "customer"})
            if otp_resp and otp_resp.status_code == 200:
                demo_code = otp_resp.json().get("demo_code")
                # OTP verify
                verify_resp, _ = req("POST", "/auth/otp/verify",
                                    json_data={"phone": "+96890000001", "role": "customer", "code": demo_code})
                if verify_resp and verify_resp.status_code == 403:
                    detail = verify_resp.json().get("detail", "")
                    if "ACCOUNT_DISABLED" in detail:
                        result.add_pass("Disabled customer login attempt", 
                                      "403 ACCOUNT_DISABLED (correct)")
                    else:
                        result.add_fail("Disabled customer login attempt", 
                                      f"403 but detail={detail}, expected ACCOUNT_DISABLED")
                else:
                    result.add_fail("Disabled customer login attempt", 
                                  f"Expected 403, got {verify_resp.status_code if verify_resp else 'error'}")
            else:
                result.add_fail("Disabled customer OTP request", "Failed to get OTP")
    
    # Test 4.6: POST /admin/users/{customerId}/status {status:"active"} - re-enable
    if customer_id:
        resp, error = req("POST", f"/admin/users/{customer_id}/status", token=token,
                         json_data={"status": "active"})
        if error or not resp or resp.status_code != 200:
            result.add_fail("POST /admin/users/{customerId}/status (re-enable)", 
                           f"Status {resp.status_code if resp else 'error'}")
        else:
            result.add_pass("POST /admin/users/{customerId}/status (re-enable)", "200 OK")
            
            # Test 4.7: Attempt customer login again (should succeed)
            otp_resp, _ = req("POST", "/auth/otp/request",
                            json_data={"phone": "+96890000001", "role": "customer"})
            if otp_resp and otp_resp.status_code == 200:
                demo_code = otp_resp.json().get("demo_code")
                verify_resp, _ = req("POST", "/auth/otp/verify",
                                    json_data={"phone": "+96890000001", "role": "customer", "code": demo_code})
                if verify_resp and verify_resp.status_code == 200:
                    result.add_pass("Re-enabled customer login", "200 OK (regression passed)")
                else:
                    result.add_fail("Re-enabled customer login", 
                                  f"Expected 200, got {verify_resp.status_code if verify_resp else 'error'}")
            else:
                result.add_fail("Re-enabled customer OTP request", "Failed")
    
    # Test 4.8: POST /admin/users/{superAdminOwnId}/status {status:"disabled"} -> 400 CANNOT_DISABLE_SELF
    super_admin_id = test_data.get("super_admin_id")
    if super_admin_id:
        resp, error = req("POST", f"/admin/users/{super_admin_id}/status", token=token,
                         json_data={"status": "disabled"})
        if resp and resp.status_code == 400:
            detail = resp.json().get("detail", "")
            if "CANNOT_DISABLE_SELF" in detail:
                result.add_pass("POST /admin/users/{superAdminOwnId}/status (disable self)", 
                              "400 CANNOT_DISABLE_SELF (correct)")
            else:
                result.add_fail("POST /admin/users/{superAdminOwnId}/status (disable self)", 
                              f"400 but detail={detail}, expected CANNOT_DISABLE_SELF")
        else:
            result.add_fail("POST /admin/users/{superAdminOwnId}/status (disable self)", 
                          f"Expected 400, got {resp.status_code if resp else 'error'}")
    
    # Test 4.9: POST /admin/users/{financeAccountantAdminId}/reset-password
    fa_id = test_data["finance_accountant"].get("id")
    if fa_id:
        new_password = "newpass123"
        resp, error = req("POST", f"/admin/users/{fa_id}/reset-password", token=token,
                         json_data={"password": new_password})
        if error or not resp or resp.status_code != 200:
            result.add_fail("POST /admin/users/{financeAccountantId}/reset-password", 
                           f"Status {resp.status_code if resp else 'error'}")
        else:
            result.add_pass("POST /admin/users/{financeAccountantId}/reset-password", "200 OK")
            
            # Test login with new password
            login_resp, _ = req("POST", "/auth/admin/login", json_data={
                "email": test_data["finance_accountant"]["email"],
                "password": new_password
            })
            if login_resp and login_resp.status_code == 200:
                result.add_pass("finance_accountant login with new password", "200 OK")
            else:
                result.add_fail("finance_accountant login with new password", 
                              f"Expected 200, got {login_resp.status_code if login_resp else 'error'}")

def test_finance_ledger(result: TestResult):
    """Test 5: Finance ledger operations"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 5: FINANCE LEDGER{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    token = test_data["super_admin_token"]
    
    # Test 5.1: GET /admin/finance/transactions
    resp, error = req("GET", "/admin/finance/transactions", token=token)
    if error or not resp or resp.status_code != 200:
        result.add_fail("GET /admin/finance/transactions", 
                       f"Status {resp.status_code if resp else 'error'}")
        return
    
    txns = resp.json()
    result.add_pass("GET /admin/finance/transactions", f"Found {len(txns)} transactions")
    
    # Check for trip-derived transactions
    trip_types = ["customer_payment", "platform_commission", "driver_earning"]
    trip_txns = [t for t in txns if t.get("type") in trip_types]
    
    if trip_txns:
        result.add_pass("Trip-derived transactions exist", 
                       f"Found {len(trip_txns)} trip-related transactions")
        
        # Verify gross = commission + net for driver_earning
        driver_earnings = [t for t in txns if t.get("type") == "driver_earning"]
        if driver_earnings:
            sample = driver_earnings[0]
            gross = float(sample.get("gross", 0))
            commission = float(sample.get("commission", 0))
            net = float(sample.get("net", 0))
            
            if abs(gross - (commission + net)) < 0.01:
                result.add_pass("driver_earning: gross = commission + net", 
                              f"gross={gross}, commission={commission}, net={net}")
            else:
                result.add_fail("driver_earning: gross = commission + net", 
                              f"gross={gross} != commission={commission} + net={net}")
            
            # Get commission settings
            settings_resp, _ = req("GET", "/admin/finance/settings", token=token)
            if settings_resp and settings_resp.status_code == 200:
                settings = settings_resp.json()
                expected_commission = gross * settings.get("commission_value", 10) / 100
                if abs(commission - expected_commission) < 0.01:
                    result.add_pass("Commission matches settings", 
                                  f"commission={commission}, expected={expected_commission:.3f}")
                else:
                    result.add_warning(f"Commission mismatch: {commission} vs expected {expected_commission:.3f}")
    else:
        result.add_warning("No trip-derived transactions found (may be expected if no completed trips)")
    
    # Test 5.2: Get a driver ID
    users_resp, _ = req("GET", "/admin/users", token=token, params={"role": "driver"})
    if users_resp and users_resp.status_code == 200:
        drivers = users_resp.json()
        if drivers:
            driver_id = drivers[0].get("id")
            test_data["driver_id"] = driver_id
            result.add_pass("Get driver ID", f"Driver ID: {driver_id}")
            
            # Test 5.3: POST /admin/finance/adjust
            adjust_resp, _ = req("POST", "/admin/finance/adjust", token=token, json_data={
                "account_id": driver_id,
                "account_role": "driver",
                "amount": 5,
                "reason": "test adjustment"
            })
            if adjust_resp and adjust_resp.status_code == 200:
                adjustment = adjust_resp.json()
                test_data["adjustment_txn_id"] = adjustment.get("id")
                result.add_pass("POST /admin/finance/adjust", 
                              f"Created adjustment txn_id={adjustment.get('id')}")
                
                # Test 5.4: GET /admin/finance/account/{driverId}
                account_resp, _ = req("GET", f"/admin/finance/account/{driver_id}", token=token)
                if account_resp and account_resp.status_code == 200:
                    account = account_resp.json()
                    totals = account.get("totals", {})
                    transactions = account.get("transactions", [])
                    
                    # Check if adjustment appears
                    adj_found = any(t.get("id") == adjustment.get("id") for t in transactions)
                    if adj_found:
                        result.add_pass("Adjustment appears in account transactions", 
                                      f"Found in {len(transactions)} transactions")
                    else:
                        result.add_fail("Adjustment appears in account transactions", 
                                      "Adjustment not found")
                    
                    # Check totals.adjustments
                    if totals.get("adjustments") is not None:
                        result.add_pass("Account totals.adjustments", 
                                      f"adjustments={totals.get('adjustments')}")
                    else:
                        result.add_warning("Account totals.adjustments field missing")
                else:
                    result.add_fail("GET /admin/finance/account/{driverId}", 
                                  f"Status {account_resp.status_code if account_resp else 'error'}")
            else:
                result.add_fail("POST /admin/finance/adjust", 
                              f"Status {adjust_resp.status_code if adjust_resp else 'error'}")
    
    # Test 5.5: POST /admin/finance/refund
    customer_id = test_data.get("customer_id")
    if customer_id:
        refund_resp, _ = req("POST", "/admin/finance/refund", token=token, json_data={
            "account_id": customer_id,
            "account_role": "customer",
            "amount": 10,
            "reason": "test refund"
        })
        if refund_resp and refund_resp.status_code == 200:
            refund = refund_resp.json()
            test_data["refund_txn_id"] = refund.get("id")
            result.add_pass("POST /admin/finance/refund", 
                          f"Created refund txn_id={refund.get('id')}")
            
            # Check if appears in customer account
            account_resp, _ = req("GET", f"/admin/finance/account/{customer_id}", token=token)
            if account_resp and account_resp.status_code == 200:
                account = account_resp.json()
                transactions = account.get("transactions", [])
                refund_found = any(t.get("id") == refund.get("id") for t in transactions)
                if refund_found:
                    result.add_pass("Refund appears in customer account", "Found")
                else:
                    result.add_fail("Refund appears in customer account", "Not found")
        else:
            result.add_fail("POST /admin/finance/refund", 
                          f"Status {refund_resp.status_code if refund_resp else 'error'}")
    
    # Test 5.6: POST /admin/finance/transactions/{adjustmentTxnId}/reverse
    adjustment_txn_id = test_data.get("adjustment_txn_id")
    if adjustment_txn_id:
        reverse_resp, _ = req("POST", f"/admin/finance/transactions/{adjustment_txn_id}/reverse",
                             token=token, json_data={"reason": "undo test adjustment"})
        if reverse_resp and reverse_resp.status_code == 200:
            reversal = reverse_resp.json()
            result.add_pass("POST /admin/finance/transactions/{id}/reverse", 
                          f"Created reversal txn_id={reversal.get('id')}, type={reversal.get('type')}")
            
            # Verify reversal transaction created
            if reversal.get("type") == "reversal":
                result.add_pass("Reversal transaction type", "type=reversal")
            else:
                result.add_fail("Reversal transaction type", 
                              f"Expected 'reversal', got '{reversal.get('type')}'")
            
            # Verify original marked as reversed
            driver_id = test_data.get("driver_id")
            if driver_id:
                account_resp, _ = req("GET", f"/admin/finance/account/{driver_id}", token=token)
                if account_resp and account_resp.status_code == 200:
                    account = account_resp.json()
                    transactions = account.get("transactions", [])
                    
                    # Find original adjustment
                    original = next((t for t in transactions if t.get("id") == adjustment_txn_id), None)
                    if original:
                        if original.get("reversed") is True:
                            result.add_pass("Original adjustment marked reversed", 
                                          f"reversed=True, amount={original.get('amount')} (unchanged)")
                        else:
                            result.add_fail("Original adjustment marked reversed", 
                                          f"reversed={original.get('reversed')}, expected True")
                    else:
                        result.add_fail("Original adjustment still present", "Not found in transactions")
                    
                    # Find reversal transaction
                    reversal_txn = next((t for t in transactions if t.get("id") == reversal.get("id")), None)
                    if reversal_txn:
                        result.add_pass("Reversal transaction present", 
                                      f"Found in account, amount={reversal_txn.get('amount')}")
                    else:
                        result.add_fail("Reversal transaction present", "Not found")
        else:
            result.add_fail("POST /admin/finance/transactions/{id}/reverse", 
                          f"Status {reverse_resp.status_code if reverse_resp else 'error'}: {reverse_resp.text if reverse_resp else ''}")

def test_audit_log(result: TestResult):
    """Test 6: Audit log"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 6: AUDIT LOG{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    token = test_data["super_admin_token"]
    
    resp, error = req("GET", "/admin/audit-logs", token=token)
    if error or not resp or resp.status_code != 200:
        result.add_fail("GET /admin/audit-logs", 
                       f"Status {resp.status_code if resp else 'error'}")
        return
    
    logs = resp.json()
    result.add_pass("GET /admin/audit-logs", f"Found {len(logs)} audit entries")
    
    # Check for required audit actions
    required_actions = [
        "admin_created",
        "user_updated",
        "user_disabled",
        "user_enabled",
        "password_reset",
        "financial_adjustment",
        "refund_created",
        "transaction_reversed"
    ]
    
    actions_found = set(log.get("action") for log in logs)
    
    for action in required_actions:
        if action in actions_found:
            result.add_pass(f"Audit log contains '{action}'", "Found")
        else:
            result.add_fail(f"Audit log contains '{action}'", "Not found")

def test_regression(result: TestResult):
    """Test 7: Regression - confirm OTP and admin logins still work"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 7: REGRESSION - AUTH FLOWS{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    # Test customer OTP login
    resp, _ = req("POST", "/auth/otp/request", json_data={"phone": "+96890000001", "role": "customer"})
    if resp and resp.status_code == 200:
        demo_code = resp.json().get("demo_code")
        verify_resp, _ = req("POST", "/auth/otp/verify", 
                            json_data={"phone": "+96890000001", "role": "customer", "code": demo_code})
        if verify_resp and verify_resp.status_code == 200:
            result.add_pass("Customer OTP login regression", "200 OK")
        else:
            result.add_fail("Customer OTP login regression", 
                          f"Status {verify_resp.status_code if verify_resp else 'error'}")
    else:
        result.add_fail("Customer OTP request regression", 
                       f"Status {resp.status_code if resp else 'error'}")
    
    # Test driver OTP login
    resp, _ = req("POST", "/auth/otp/request", json_data={"phone": "+96890000002", "role": "driver"})
    if resp and resp.status_code == 200:
        demo_code = resp.json().get("demo_code")
        verify_resp, _ = req("POST", "/auth/otp/verify",
                            json_data={"phone": "+96890000002", "role": "driver", "code": demo_code})
        if verify_resp and verify_resp.status_code == 200:
            result.add_pass("Driver OTP login regression", "200 OK")
        else:
            result.add_fail("Driver OTP login regression", 
                          f"Status {verify_resp.status_code if verify_resp else 'error'}")
    else:
        result.add_fail("Driver OTP request regression", 
                       f"Status {resp.status_code if resp else 'error'}")
    
    # Test provider OTP login
    resp, _ = req("POST", "/auth/otp/request", json_data={"phone": "+96890000005", "role": "provider"})
    if resp and resp.status_code == 200:
        demo_code = resp.json().get("demo_code")
        verify_resp, _ = req("POST", "/auth/otp/verify",
                            json_data={"phone": "+96890000005", "role": "provider", "code": demo_code})
        if verify_resp and verify_resp.status_code == 200:
            result.add_pass("Provider OTP login regression", "200 OK")
        else:
            result.add_fail("Provider OTP login regression", 
                          f"Status {verify_resp.status_code if verify_resp else 'error'}")
    else:
        result.add_fail("Provider OTP request regression", 
                       f"Status {resp.status_code if resp else 'error'}")
    
    # Test admin login
    resp, _ = req("POST", "/auth/admin/login", json_data=ADMIN_CREDS)
    if resp and resp.status_code == 200:
        result.add_pass("Admin login regression", "200 OK")
    else:
        result.add_fail("Admin login regression", 
                       f"Status {resp.status_code if resp else 'error'}")

def main():
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CARGO PHASE 3A BACKEND TEST SUITE{RESET}")
    print(f"{BLUE}Admin User Management, RBAC, Finance + Authorization{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"Base URL: {BASE_URL}")
    
    result = TestResult()
    
    # Test 0: Super admin login (prerequisite)
    if not test_super_admin_login(result):
        print(f"\n{RED}CRITICAL: Super admin login failed. Cannot proceed.{RESET}")
        result.summary()
        sys.exit(1)
    
    # Test 1: Roles endpoint
    test_roles_endpoint(result)
    
    # Test 2: Create staff admins
    test_create_staff(result)
    
    # Test 3: Authorization matrix
    test_authorization_matrix(result)
    
    # Test 4: User management
    test_user_management(result)
    
    # Test 5: Finance ledger
    test_finance_ledger(result)
    
    # Test 6: Audit log
    test_audit_log(result)
    
    # Test 7: Regression
    test_regression(result)
    
    # Summary
    success = result.summary()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
