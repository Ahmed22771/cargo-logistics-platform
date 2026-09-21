#!/usr/bin/env python3
"""
Phase 4 Backend Comprehensive Test Suite
Tests: Legacy document migration, document review permissions, suspend/activate, audit logs, regression
"""
import requests
import json
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://cargo-state-check.preview.emergentagent.com/api"

# Test credentials
SUPER_ADMIN_EMAIL = "admin@cargo.om"
SUPER_ADMIN_PASSWORD = "admin123"

CUSTOMER_PHONE = "+96890000001"
DRIVER_PHONE = "+96890000002"
PROVIDER_PHONE = "+96890000005"

# Test results storage
results = {
    "A_LEGACY_MIGRATION": [],
    "B_DOC_REVIEW_PERMISSION": [],
    "C_DOC_LIST_FILTERS": [],
    "D_SUSPEND_CUSTOMER": [],
    "E_SUSPEND_DRIVER_PROVIDER": [],
    "F_SUSPEND_ADMIN": [],
    "G_SELF_PROTECTION": [],
    "H_LAST_SUPER_ADMIN": [],
    "I_AUDIT_LOG": [],
    "J_REGRESSION": [],
}

def log_result(section, test_name, passed, status_code=None, detail=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    msg = f"{status} - {test_name}"
    if status_code:
        msg += f" (HTTP {status_code})"
    if detail:
        msg += f" - {detail}"
    results[section].append(msg)
    print(msg)

def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

# ============================================================================
# SECTION A: LEGACY DOCUMENT MIGRATION
# ============================================================================
def test_section_a():
    print_section("SECTION A: LEGACY DOCUMENT MIGRATION")
    
    # A1: Login as super_admin
    resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    })
    log_result("A_LEGACY_MIGRATION", "A1: Super admin login", resp.status_code == 200, resp.status_code)
    if resp.status_code != 200:
        print(f"ERROR: Cannot proceed without super_admin token: {resp.text}")
        return None
    
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # A2: GET /admin/documents - verify migration
    resp = requests.get(f"{BASE_URL}/admin/documents", headers=headers)
    log_result("A_LEGACY_MIGRATION", "A2: GET /admin/documents", resp.status_code == 200, resp.status_code)
    
    if resp.status_code == 200:
        docs = resp.json()
        migrated_docs = [d for d in docs if d.get("migrated_from_legacy")]
        has_driver_owner = any(d.get("owner_type") == "driver" for d in docs)
        has_vehicle_owner = any(d.get("owner_type") == "vehicle" for d in docs)
        
        log_result("A_LEGACY_MIGRATION", "A2.1: Migrated documents exist", 
                   len(migrated_docs) > 0, detail=f"Found {len(migrated_docs)} migrated docs")
        log_result("A_LEGACY_MIGRATION", "A2.2: owner_type=driver exists", has_driver_owner)
        log_result("A_LEGACY_MIGRATION", "A2.3: owner_type=vehicle exists", has_vehicle_owner)
        
        # A3: Idempotency check - count docs per (owner_id, doc_type_key)
        owner_doc_pairs = {}
        for d in docs:
            key = (d.get("owner_id"), d.get("doc_type_key"))
            owner_doc_pairs[key] = owner_doc_pairs.get(key, 0) + 1
        
        duplicates = {k: v for k, v in owner_doc_pairs.items() if v > 1}
        log_result("A_LEGACY_MIGRATION", "A3: Idempotency (no duplicates)", 
                   len(duplicates) == 0, detail=f"Duplicates: {len(duplicates)}")
        
        # A4: Non-destruction - check legacy documents[] still exist
        resp_drivers = requests.get(f"{BASE_URL}/admin/drivers", headers=headers)
        if resp_drivers.status_code == 200:
            drivers = resp_drivers.json()
            approved_driver = next((d for d in drivers if d.get("phone") == DRIVER_PHONE), None)
            if approved_driver:
                legacy_docs = approved_driver.get("documents", [])
                log_result("A_LEGACY_MIGRATION", "A4: Legacy documents[] preserved", 
                           len(legacy_docs) > 0, detail=f"Found {len(legacy_docs)} legacy docs")
            else:
                log_result("A_LEGACY_MIGRATION", "A4: Legacy documents[] preserved", 
                           False, detail="Approved driver not found")
    
    return token

# ============================================================================
# SECTION B: DOCUMENT REVIEW PERMISSION MATRIX
# ============================================================================
def test_section_b(super_token):
    print_section("SECTION B: DOCUMENT REVIEW PERMISSION MATRIX")
    headers = {"Authorization": f"Bearer {super_token}"}
    
    # B1: Create document_reviewer admin
    timestamp = int(datetime.now().timestamp())
    docrev_email = f"docrev_p4_{timestamp}@cargo.om"
    resp = requests.post(f"{BASE_URL}/admin/admins", headers=headers, json={
        "name": "DocRev Test",
        "email": docrev_email,
        "password": "test12345",
        "admin_role_key": "document_reviewer"
    })
    log_result("B_DOC_REVIEW_PERMISSION", "B1: Create document_reviewer admin", 
               resp.status_code == 200, resp.status_code)
    
    if resp.status_code != 200:
        print(f"ERROR: Cannot create document_reviewer: {resp.text}")
        return None
    
    docrev_id = resp.json()["id"]
    
    # B2: Login as document_reviewer and check permissions
    resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
        "email": docrev_email,
        "password": "test12345"
    })
    log_result("B_DOC_REVIEW_PERMISSION", "B2.1: Document reviewer login", 
               resp.status_code == 200, resp.status_code)
    
    if resp.status_code != 200:
        return None
    
    docrev_token = resp.json()["token"]
    docrev_headers = {"Authorization": f"Bearer {docrev_token}"}
    
    resp = requests.get(f"{BASE_URL}/admin/me/permissions", headers=docrev_headers)
    log_result("B_DOC_REVIEW_PERMISSION", "B2.2: GET /admin/me/permissions", 
               resp.status_code == 200, resp.status_code)
    
    if resp.status_code == 200:
        perms = resp.json().get("permissions", [])
        has_review = "documents.review" in perms
        has_view = "documents.view" in perms
        no_finance = "finance.view" not in perms
        no_suspend = "users.suspend" not in perms
        
        log_result("B_DOC_REVIEW_PERMISSION", "B2.3: Has documents.review permission", has_review)
        log_result("B_DOC_REVIEW_PERMISSION", "B2.4: Has documents.view permission", has_view)
        log_result("B_DOC_REVIEW_PERMISSION", "B2.5: No finance.view permission", no_finance)
        log_result("B_DOC_REVIEW_PERMISSION", "B2.6: No users.suspend permission", no_suspend)
    
    # B3: Approve a PENDING document
    resp = requests.get(f"{BASE_URL}/admin/documents?status=PENDING", headers=docrev_headers)
    if resp.status_code == 200 and len(resp.json()) > 0:
        pending_doc = resp.json()[0]
        doc_id = pending_doc["id"]
        
        resp = requests.post(f"{BASE_URL}/admin/documents/{doc_id}/review", 
                            headers=docrev_headers, json={"action": "approve"})
        log_result("B_DOC_REVIEW_PERMISSION", "B3.1: Approve document", 
                   resp.status_code == 200, resp.status_code)
        
        # Check audit log
        resp = requests.get(f"{BASE_URL}/admin/audit-logs", headers={"Authorization": f"Bearer {super_token}"})
        if resp.status_code == 200:
            logs = resp.json()
            approve_log = next((l for l in logs if l.get("action") == "DOCUMENT_APPROVED" 
                               and l.get("entity_id") == doc_id), None)
            if approve_log:
                has_actor = approve_log.get("actor_id") == docrev_id
                has_old_status = approve_log.get("old_value", {}).get("status") == "PENDING"
                has_new_status = approve_log.get("new_value", {}).get("status") == "APPROVED"
                has_owner = "owner_id" in approve_log.get("new_value", {})
                
                log_result("B_DOC_REVIEW_PERMISSION", "B3.2: Audit log DOCUMENT_APPROVED exists", True)
                log_result("B_DOC_REVIEW_PERMISSION", "B3.3: Audit log has correct actor", has_actor)
                log_result("B_DOC_REVIEW_PERMISSION", "B3.4: Audit log has old_value.status=PENDING", has_old_status)
                log_result("B_DOC_REVIEW_PERMISSION", "B3.5: Audit log has new_value.status=APPROVED", has_new_status)
                log_result("B_DOC_REVIEW_PERMISSION", "B3.6: Audit log has owner_id", has_owner)
            else:
                log_result("B_DOC_REVIEW_PERMISSION", "B3.2: Audit log DOCUMENT_APPROVED exists", False)
    else:
        log_result("B_DOC_REVIEW_PERMISSION", "B3: Approve document", False, 
                   detail="No PENDING documents found")
    
    # B4: Reject a document with reason
    resp = requests.get(f"{BASE_URL}/admin/documents?status=PENDING", headers=docrev_headers)
    if resp.status_code == 200 and len(resp.json()) > 0:
        pending_doc = resp.json()[0]
        doc_id = pending_doc["id"]
        
        resp = requests.post(f"{BASE_URL}/admin/documents/{doc_id}/review", 
                            headers=docrev_headers, json={"action": "reject", "reason": "Test rejection reason"})
        log_result("B_DOC_REVIEW_PERMISSION", "B4.1: Reject document with reason", 
                   resp.status_code == 200, resp.status_code)
        
        if resp.status_code == 200:
            doc = resp.json()
            log_result("B_DOC_REVIEW_PERMISSION", "B4.2: Document status=REJECTED", 
                       doc.get("status") == "REJECTED")
            log_result("B_DOC_REVIEW_PERMISSION", "B4.3: rejection_reason preserved", 
                       doc.get("rejection_reason") == "Test rejection reason")
    else:
        log_result("B_DOC_REVIEW_PERMISSION", "B4: Reject document", False, 
                   detail="No PENDING documents found")
    
    # B5: Create finance_accountant and test 403 on document review
    fin_email = f"finacct_p4_{timestamp}@cargo.om"
    resp = requests.post(f"{BASE_URL}/admin/admins", headers={"Authorization": f"Bearer {super_token}"}, json={
        "name": "Finance Test",
        "email": fin_email,
        "password": "test12345",
        "admin_role_key": "finance_accountant"
    })
    log_result("B_DOC_REVIEW_PERMISSION", "B5.1: Create finance_accountant admin", 
               resp.status_code == 200, resp.status_code)
    
    if resp.status_code == 200:
        resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
            "email": fin_email,
            "password": "test12345"
        })
        if resp.status_code == 200:
            fin_token = resp.json()["token"]
            fin_headers = {"Authorization": f"Bearer {fin_token}"}
            
            # Try to review a document - should get 403
            resp = requests.get(f"{BASE_URL}/admin/documents", headers=fin_headers)
            if resp.status_code == 200 and len(resp.json()) > 0:
                doc_id = resp.json()[0]["id"]
                resp = requests.post(f"{BASE_URL}/admin/documents/{doc_id}/review", 
                                    headers=fin_headers, json={"action": "approve"})
                log_result("B_DOC_REVIEW_PERMISSION", "B5.2: Finance accountant CANNOT review (403)", 
                           resp.status_code == 403, resp.status_code, 
                           detail=resp.json().get("detail", ""))
    
    # B6: Finance accountant cannot access finance stats - wait, they SHOULD be able to
    # Let's test they CAN access finance but CANNOT access other areas
    if resp.status_code == 200:
        resp = requests.get(f"{BASE_URL}/admin/finance/stats", headers=fin_headers)
        log_result("B_DOC_REVIEW_PERMISSION", "B6.1: Finance accountant CAN access finance/stats", 
                   resp.status_code == 200, resp.status_code)
    
    # B7: Document reviewer cannot access finance
    resp = requests.get(f"{BASE_URL}/admin/finance/stats", headers=docrev_headers)
    log_result("B_DOC_REVIEW_PERMISSION", "B7: Document reviewer CANNOT access finance (403)", 
               resp.status_code == 403, resp.status_code)
    
    return docrev_id, docrev_email

# ============================================================================
# SECTION C: DOCUMENT LIST FILTERS
# ============================================================================
def test_section_c(super_token):
    print_section("SECTION C: DOCUMENT LIST FILTERS")
    headers = {"Authorization": f"Bearer {super_token}"}
    
    filters = [
        ("owner_type=driver", "owner_type", "driver"),
        ("owner_type=vehicle", "owner_type", "vehicle"),
        ("status=PENDING", "status", "PENDING"),
        ("doc_type=driving_license", "doc_type_key", "driving_license"),
        ("expiring=true", "expiry_flag", ["EXPIRING", "EXPIRED"]),
        ("q=خالد", "owner_name", "خالد"),
    ]
    
    for query_str, field, expected in filters:
        resp = requests.get(f"{BASE_URL}/admin/documents?{query_str}", headers=headers)
        log_result("C_DOC_LIST_FILTERS", f"GET /admin/documents?{query_str}", 
                   resp.status_code == 200, resp.status_code)
        
        if resp.status_code == 200:
            docs = resp.json()
            # Verify all docs have owner_type set
            all_have_owner_type = all("owner_type" in d for d in docs)
            log_result("C_DOC_LIST_FILTERS", f"  All docs have owner_type ({query_str})", 
                       all_have_owner_type)
            
            # Verify filter works (if docs returned)
            if len(docs) > 0:
                if isinstance(expected, list):
                    # For expiring filter
                    filter_works = all(d.get(field) in expected for d in docs)
                elif field == "owner_name":
                    # For search query
                    filter_works = any(expected in d.get(field, "") for d in docs)
                else:
                    filter_works = all(d.get(field) == expected for d in docs)
                
                log_result("C_DOC_LIST_FILTERS", f"  Filter works correctly ({query_str})", 
                           filter_works, detail=f"Returned {len(docs)} docs")

# ============================================================================
# SECTION D: SUSPEND/ACTIVATE - CUSTOMER
# ============================================================================
def test_section_d(super_token):
    print_section("SECTION D: SUSPEND/ACTIVATE - CUSTOMER")
    headers = {"Authorization": f"Bearer {super_token}"}
    
    # D1: Find customer
    resp = requests.get(f"{BASE_URL}/admin/users?role=customer", headers=headers)
    log_result("D_SUSPEND_CUSTOMER", "D1: GET /admin/users?role=customer", 
               resp.status_code == 200, resp.status_code)
    
    if resp.status_code != 200 or len(resp.json()) == 0:
        print("ERROR: No customer found")
        return None
    
    customer = next((u for u in resp.json() if u.get("phone") == CUSTOMER_PHONE), None)
    if not customer:
        print("ERROR: Demo customer not found")
        return None
    
    customer_id = customer["id"]
    
    # D2: Suspend customer
    resp = requests.post(f"{BASE_URL}/admin/users/{customer_id}/suspend", 
                        headers=headers, json={"reason": "test-suspend-p4"})
    log_result("D_SUSPEND_CUSTOMER", "D2: POST /admin/users/{id}/suspend", 
               resp.status_code == 200, resp.status_code)
    
    if resp.status_code == 200:
        data = resp.json()
        log_result("D_SUSPEND_CUSTOMER", "D2.1: Response status=suspended", 
                   data.get("status") == "suspended")
        log_result("D_SUSPEND_CUSTOMER", "D2.2: Response has reason", 
                   data.get("reason") == "test-suspend-p4")
    
    # D3: Request OTP for suspended customer
    resp = requests.post(f"{BASE_URL}/auth/otp/request", json={
        "phone": CUSTOMER_PHONE,
        "role": "customer"
    })
    log_result("D_SUSPEND_CUSTOMER", "D3: POST /auth/otp/request (suspended)", 
               resp.status_code == 200, resp.status_code)
    
    if resp.status_code == 200:
        demo_code = resp.json().get("demo_code")
        
        # D4: Verify OTP - should get 403 ACCOUNT_SUSPENDED
        resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
            "phone": CUSTOMER_PHONE,
            "role": "customer",
            "code": demo_code
        })
        log_result("D_SUSPEND_CUSTOMER", "D4: POST /auth/otp/verify BLOCKED (403)", 
                   resp.status_code == 403, resp.status_code)
        
        if resp.status_code == 403:
            log_result("D_SUSPEND_CUSTOMER", "D4.1: Detail=ACCOUNT_SUSPENDED", 
                       resp.json().get("detail") == "ACCOUNT_SUSPENDED")
    
    # D5: Get suspension history
    resp = requests.get(f"{BASE_URL}/admin/users/{customer_id}/suspension-history", headers=headers)
    log_result("D_SUSPEND_CUSTOMER", "D5: GET /admin/users/{id}/suspension-history", 
               resp.status_code == 200, resp.status_code)
    
    if resp.status_code == 200:
        data = resp.json()
        history = data.get("history", [])
        has_suspended = any(h.get("action") == "SUSPENDED" and h.get("reason") == "test-suspend-p4" 
                           for h in history)
        log_result("D_SUSPEND_CUSTOMER", "D5.1: History contains SUSPENDED entry", has_suspended)
    
    # D6: Activate customer
    resp = requests.post(f"{BASE_URL}/admin/users/{customer_id}/activate", headers=headers)
    log_result("D_SUSPEND_CUSTOMER", "D6: POST /admin/users/{id}/activate", 
               resp.status_code == 200, resp.status_code)
    
    # D7: Login should now work
    resp = requests.post(f"{BASE_URL}/auth/otp/request", json={
        "phone": CUSTOMER_PHONE,
        "role": "customer"
    })
    if resp.status_code == 200:
        demo_code = resp.json().get("demo_code")
        resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
            "phone": CUSTOMER_PHONE,
            "role": "customer",
            "code": demo_code
        })
        log_result("D_SUSPEND_CUSTOMER", "D7: Customer login works after activate (200)", 
                   resp.status_code == 200, resp.status_code)
        
        if resp.status_code == 200:
            customer_token = resp.json().get("token")
    
    # D8: Suspension history preserved
    resp = requests.get(f"{BASE_URL}/admin/users/{customer_id}/suspension-history", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        history = data.get("history", [])
        has_suspended = any(h.get("action") == "SUSPENDED" for h in history)
        has_activated = any(h.get("action") == "ACTIVATED" for h in history)
        log_result("D_SUSPEND_CUSTOMER", "D8.1: History has SUSPENDED entry", has_suspended)
        log_result("D_SUSPEND_CUSTOMER", "D8.2: History has ACTIVATED entry", has_activated)
        log_result("D_SUSPEND_CUSTOMER", "D8.3: History preserved (not overwritten)", 
                   len(history) >= 2)
    
    return customer_id

# ============================================================================
# SECTION E: SUSPEND/ACTIVATE - DRIVER + PROVIDER
# ============================================================================
def test_section_e(super_token):
    print_section("SECTION E: SUSPEND/ACTIVATE - DRIVER + PROVIDER")
    headers = {"Authorization": f"Bearer {super_token}"}
    
    # E1: Test driver
    resp = requests.get(f"{BASE_URL}/admin/users?role=driver", headers=headers)
    if resp.status_code == 200:
        driver = next((u for u in resp.json() if u.get("phone") == DRIVER_PHONE), None)
        if driver:
            driver_id = driver["id"]
            
            # Get driver token before suspend
            resp = requests.post(f"{BASE_URL}/auth/otp/request", json={
                "phone": DRIVER_PHONE,
                "role": "driver"
            })
            if resp.status_code == 200:
                demo_code = resp.json().get("demo_code")
                resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
                    "phone": DRIVER_PHONE,
                    "role": "driver",
                    "code": demo_code
                })
                if resp.status_code == 200:
                    driver_token = resp.json().get("token")
            
            # Suspend driver
            resp = requests.post(f"{BASE_URL}/admin/users/{driver_id}/suspend", 
                                headers=headers, json={"reason": "test-suspend-driver"})
            log_result("E_SUSPEND_DRIVER_PROVIDER", "E1.1: Suspend driver", 
                       resp.status_code == 200, resp.status_code)
            
            # Try OTP login - should fail
            resp = requests.post(f"{BASE_URL}/auth/otp/request", json={
                "phone": DRIVER_PHONE,
                "role": "driver"
            })
            if resp.status_code == 200:
                demo_code = resp.json().get("demo_code")
                resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
                    "phone": DRIVER_PHONE,
                    "role": "driver",
                    "code": demo_code
                })
                log_result("E_SUSPEND_DRIVER_PROVIDER", "E1.2: Driver OTP verify blocked (403)", 
                           resp.status_code == 403, resp.status_code)
            
            # Try marketplace access with old token - should also fail
            if 'driver_token' in locals():
                resp = requests.get(f"{BASE_URL}/marketplace/shipments", 
                                   headers={"Authorization": f"Bearer {driver_token}"})
                log_result("E_SUSPEND_DRIVER_PROVIDER", "E1.3: Marketplace access blocked (403)", 
                           resp.status_code == 403, resp.status_code)
            
            # Activate driver
            resp = requests.post(f"{BASE_URL}/admin/users/{driver_id}/activate", headers=headers)
            log_result("E_SUSPEND_DRIVER_PROVIDER", "E1.4: Activate driver", 
                       resp.status_code == 200, resp.status_code)
    
    # E2: Test provider
    resp = requests.get(f"{BASE_URL}/admin/users?role=provider", headers=headers)
    if resp.status_code == 200:
        provider = next((u for u in resp.json() if u.get("phone") == PROVIDER_PHONE), None)
        if provider:
            provider_id = provider["id"]
            
            # Suspend provider
            resp = requests.post(f"{BASE_URL}/admin/users/{provider_id}/suspend", 
                                headers=headers, json={"reason": "test-suspend-provider"})
            log_result("E_SUSPEND_DRIVER_PROVIDER", "E2.1: Suspend provider", 
                       resp.status_code == 200, resp.status_code)
            
            # Try OTP login - should fail
            resp = requests.post(f"{BASE_URL}/auth/otp/request", json={
                "phone": PROVIDER_PHONE,
                "role": "provider"
            })
            if resp.status_code == 200:
                demo_code = resp.json().get("demo_code")
                resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
                    "phone": PROVIDER_PHONE,
                    "role": "provider",
                    "code": demo_code
                })
                log_result("E_SUSPEND_DRIVER_PROVIDER", "E2.2: Provider OTP verify blocked (403)", 
                           resp.status_code == 403, resp.status_code)
            
            # Activate provider
            resp = requests.post(f"{BASE_URL}/admin/users/{provider_id}/activate", headers=headers)
            log_result("E_SUSPEND_DRIVER_PROVIDER", "E2.3: Activate provider", 
                       resp.status_code == 200, resp.status_code)

# ============================================================================
# SECTION F: SUSPEND/ACTIVATE - STAFF ADMIN
# ============================================================================
def test_section_f(super_token, docrev_id, docrev_email):
    print_section("SECTION F: SUSPEND/ACTIVATE - STAFF ADMIN")
    headers = {"Authorization": f"Bearer {super_token}"}
    
    # F1: Suspend the document_reviewer admin
    resp = requests.post(f"{BASE_URL}/admin/users/{docrev_id}/suspend", 
                        headers=headers, json={"reason": "test-suspend-admin"})
    log_result("F_SUSPEND_ADMIN", "F1: Suspend document_reviewer admin", 
               resp.status_code == 200, resp.status_code)
    
    # F2: Try to login as suspended admin
    resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
        "email": docrev_email,
        "password": "test12345"
    })
    log_result("F_SUSPEND_ADMIN", "F2.1: Admin login blocked (403)", 
               resp.status_code == 403, resp.status_code)
    
    if resp.status_code == 403:
        log_result("F_SUSPEND_ADMIN", "F2.2: Detail=ACCOUNT_SUSPENDED", 
                   resp.json().get("detail") == "ACCOUNT_SUSPENDED")
    
    # F3: Activate admin
    resp = requests.post(f"{BASE_URL}/admin/users/{docrev_id}/activate", headers=headers)
    log_result("F_SUSPEND_ADMIN", "F3: Activate admin", 
               resp.status_code == 200, resp.status_code)
    
    # F4: Login should now work
    resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
        "email": docrev_email,
        "password": "test12345"
    })
    log_result("F_SUSPEND_ADMIN", "F4: Admin login works after activate (200)", 
               resp.status_code == 200, resp.status_code)

# ============================================================================
# SECTION G: SELF-PROTECTION
# ============================================================================
def test_section_g(super_token):
    print_section("SECTION G: SELF-PROTECTION")
    headers = {"Authorization": f"Bearer {super_token}"}
    
    # Get super_admin's own ID
    resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if resp.status_code == 200:
        super_admin_id = resp.json()["id"]
        
        # Try to suspend self
        resp = requests.post(f"{BASE_URL}/admin/users/{super_admin_id}/suspend", 
                            headers=headers, json={"reason": "test-self-suspend"})
        log_result("G_SELF_PROTECTION", "G1: Cannot suspend self (400)", 
                   resp.status_code == 400, resp.status_code)
        
        if resp.status_code == 400:
            log_result("G_SELF_PROTECTION", "G1.1: Detail=CANNOT_SUSPEND_SELF", 
                       resp.json().get("detail") == "CANNOT_SUSPEND_SELF")

# ============================================================================
# SECTION H: LAST SUPER_ADMIN PROTECTION
# ============================================================================
def test_section_h(super_token):
    print_section("SECTION H: LAST SUPER_ADMIN PROTECTION")
    headers = {"Authorization": f"Bearer {super_token}"}
    
    # Get current super_admin ID
    resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if resp.status_code != 200:
        return
    
    original_super_id = resp.json()["id"]
    
    # H1: Create a second super_admin
    timestamp = int(datetime.now().timestamp())
    second_super_email = f"super2_p4_{timestamp}@cargo.om"
    resp = requests.post(f"{BASE_URL}/admin/admins", headers=headers, json={
        "name": "Second Super Admin",
        "email": second_super_email,
        "password": "test12345",
        "admin_role_key": "super_admin"
    })
    log_result("H_LAST_SUPER_ADMIN", "H1: Create second super_admin", 
               resp.status_code == 200, resp.status_code)
    
    if resp.status_code != 200:
        return
    
    second_super_id = resp.json()["id"]
    
    # H2: Suspend the second super_admin (should work, 1 remains)
    resp = requests.post(f"{BASE_URL}/admin/users/{second_super_id}/suspend", 
                        headers=headers, json={"reason": "test-suspend-second"})
    log_result("H_LAST_SUPER_ADMIN", "H2: Suspend second super_admin (200)", 
               resp.status_code == 200, resp.status_code)
    
    # H3: Now try to suspend the original (should fail - last one)
    resp = requests.post(f"{BASE_URL}/admin/users/{original_super_id}/suspend", 
                        headers=headers, json={"reason": "test-suspend-last"})
    log_result("H_LAST_SUPER_ADMIN", "H3.1: Cannot suspend last super_admin (400)", 
               resp.status_code == 400, resp.status_code)
    
    if resp.status_code == 400:
        log_result("H_LAST_SUPER_ADMIN", "H3.2: Detail=CANNOT_SUSPEND_LAST_SUPER_ADMIN", 
                   resp.json().get("detail") == "CANNOT_SUSPEND_LAST_SUPER_ADMIN")
    
    # H4: Reactivate the second super_admin
    resp = requests.post(f"{BASE_URL}/admin/users/{second_super_id}/activate", headers=headers)
    log_result("H_LAST_SUPER_ADMIN", "H4: Reactivate second super_admin", 
               resp.status_code == 200, resp.status_code)
    
    # H5: Now suspending the original should work (2 active)
    resp = requests.post(f"{BASE_URL}/admin/users/{original_super_id}/suspend", 
                        headers=headers, json={"reason": "test-suspend-original"})
    log_result("H_LAST_SUPER_ADMIN", "H5: Suspend original super_admin works (200)", 
               resp.status_code == 200, resp.status_code)
    
    # H6: Immediately reactivate
    # Login as second super_admin first
    resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
        "email": second_super_email,
        "password": "test12345"
    })
    if resp.status_code == 200:
        second_token = resp.json()["token"]
        resp = requests.post(f"{BASE_URL}/admin/users/{original_super_id}/activate", 
                            headers={"Authorization": f"Bearer {second_token}"})
        log_result("H_LAST_SUPER_ADMIN", "H6: Reactivate original super_admin", 
                   resp.status_code == 200, resp.status_code)

# ============================================================================
# SECTION I: AUDIT LOG
# ============================================================================
def test_section_i(super_token):
    print_section("SECTION I: AUDIT LOG")
    headers = {"Authorization": f"Bearer {super_token}"}
    
    resp = requests.get(f"{BASE_URL}/admin/audit-logs", headers=headers)
    log_result("I_AUDIT_LOG", "I1: GET /admin/audit-logs", 
               resp.status_code == 200, resp.status_code)
    
    if resp.status_code == 200:
        logs = resp.json()
        
        required_actions = [
            "USER_SUSPENDED",
            "USER_ACTIVATED",
            "DOCUMENT_APPROVED",
            "DOCUMENT_REJECTED"
        ]
        
        for action in required_actions:
            entries = [l for l in logs if l.get("action") == action]
            log_result("I_AUDIT_LOG", f"I2: Audit log contains {action}", 
                       len(entries) > 0, detail=f"Found {len(entries)} entries")
            
            if len(entries) > 0:
                entry = entries[0]
                has_actor = "actor_id" in entry
                has_old_value = "old_value" in entry
                has_new_value = "new_value" in entry
                
                log_result("I_AUDIT_LOG", f"  {action} has actor_id", has_actor)
                log_result("I_AUDIT_LOG", f"  {action} has old_value", has_old_value)
                log_result("I_AUDIT_LOG", f"  {action} has new_value", has_new_value)
                
                if action in ["USER_SUSPENDED", "DOCUMENT_REJECTED"]:
                    has_reason = "reason" in entry or "reason" in entry.get("new_value", {})
                    log_result("I_AUDIT_LOG", f"  {action} has reason", has_reason)

# ============================================================================
# SECTION J: REGRESSION
# ============================================================================
def test_section_j(super_token):
    print_section("SECTION J: REGRESSION")
    headers = {"Authorization": f"Bearer {super_token}"}
    
    # J1: Active demo accounts login
    accounts = [
        (CUSTOMER_PHONE, "customer", "Customer"),
        (DRIVER_PHONE, "driver", "Driver"),
        (PROVIDER_PHONE, "provider", "Provider"),
    ]
    
    tokens = {}
    for phone, role, name in accounts:
        resp = requests.post(f"{BASE_URL}/auth/otp/request", json={
            "phone": phone,
            "role": role
        })
        if resp.status_code == 200:
            demo_code = resp.json().get("demo_code")
            resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
                "phone": phone,
                "role": role,
                "code": demo_code
            })
            log_result("J_REGRESSION", f"J1: {name} OTP login", 
                       resp.status_code == 200, resp.status_code)
            if resp.status_code == 200:
                tokens[role] = resp.json().get("token")
    
    # Admin login
    resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    })
    log_result("J_REGRESSION", "J1: Admin login", 
               resp.status_code == 200, resp.status_code)
    
    # J2: Admin endpoints
    admin_endpoints = [
        "/admin/stats",
        "/admin/drivers",
        "/admin/shipments",
        "/admin/bids",
        "/admin/trips",
        "/admin/roles",
        "/admin/finance/stats",
        "/admin/finance/transactions",
        "/admin/ops-stats",
        "/admin/audit-logs",
    ]
    
    for endpoint in admin_endpoints:
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        log_result("J_REGRESSION", f"J2: GET {endpoint}", 
                   resp.status_code == 200, resp.status_code)
    
    # J3: Happy-path flow
    if "customer" in tokens:
        customer_headers = {"Authorization": f"Bearer {tokens['customer']}"}
        
        # Create shipment
        resp = requests.post(f"{BASE_URL}/shipments", headers=customer_headers, json={
            "title": "Test shipment Phase 4",
            "description": "Test description",
            "category": "furniture",
            "quantity": "1",
            "weight": "100",
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
                "lat": 17.0194,
                "lng": 54.0897,
                "city": "Salalah",
                "area": "Dhofar",
                "country": "Oman"
            },
            "pickup_date": "2026-08-01",
            "pickup_time": "10:00",
            "vehicle_type": "pickup",
            "status": "DRAFT"
        })
        log_result("J_REGRESSION", "J3.1: POST /shipments (DRAFT)", 
                   resp.status_code == 200, resp.status_code)
        
        if resp.status_code == 200:
            shipment_id = resp.json()["id"]
            
            # Get my shipments
            resp = requests.get(f"{BASE_URL}/shipments/mine", headers=customer_headers)
            log_result("J_REGRESSION", "J3.2: GET /shipments/mine", 
                       resp.status_code == 200, resp.status_code)
            
            # Publish shipment
            resp = requests.post(f"{BASE_URL}/shipments/{shipment_id}/publish", 
                                headers=customer_headers)
            log_result("J_REGRESSION", "J3.3: POST /shipments/{id}/publish", 
                       resp.status_code == 200, resp.status_code)
            
            # Driver marketplace
            if "driver" in tokens:
                driver_headers = {"Authorization": f"Bearer {tokens['driver']}"}
                resp = requests.get(f"{BASE_URL}/marketplace/shipments", headers=driver_headers)
                log_result("J_REGRESSION", "J3.4: GET /marketplace/shipments (driver)", 
                           resp.status_code == 200, resp.status_code)
                
                # Submit bid
                resp = requests.post(f"{BASE_URL}/shipments/{shipment_id}/bids", 
                                    headers=driver_headers, json={"price": 100})
                log_result("J_REGRESSION", "J3.5: POST /shipments/{id}/bids", 
                           resp.status_code == 200, resp.status_code)
                
                if resp.status_code == 200:
                    bid_id = resp.json()["id"]
                    
                    # Accept bid
                    resp = requests.post(f"{BASE_URL}/bids/{bid_id}/accept", 
                                        headers=customer_headers)
                    log_result("J_REGRESSION", "J3.6: POST /bids/{id}/accept", 
                               resp.status_code == 200, resp.status_code)
                    
                    if resp.status_code == 200:
                        trip_id = resp.json()["id"]
                        
                        # Update trip status
                        resp = requests.post(f"{BASE_URL}/trips/{trip_id}/status", 
                                            headers=driver_headers, json={
                                                "status": "DRIVER_EN_ROUTE",
                                                "lat": 23.5880,
                                                "lng": 58.3829
                                            })
                        log_result("J_REGRESSION", "J3.7: POST /trips/{id}/status", 
                                   resp.status_code == 200, resp.status_code)

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("\n" + "="*80)
    print("  PHASE 4 BACKEND COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Started at: {datetime.now().isoformat()}")
    
    try:
        # Section A: Legacy Migration
        super_token = test_section_a()
        if not super_token:
            print("\n❌ CRITICAL: Cannot proceed without super_admin token")
            return
        
        # Section B: Document Review Permission
        docrev_result = test_section_b(super_token)
        docrev_id, docrev_email = docrev_result if docrev_result else (None, None)
        
        # Section C: Document List Filters
        test_section_c(super_token)
        
        # Section D: Suspend/Activate Customer
        test_section_d(super_token)
        
        # Section E: Suspend/Activate Driver + Provider
        test_section_e(super_token)
        
        # Section F: Suspend/Activate Staff Admin
        if docrev_id and docrev_email:
            test_section_f(super_token, docrev_id, docrev_email)
        
        # Section G: Self-Protection
        test_section_g(super_token)
        
        # Section H: Last Super Admin Protection
        test_section_h(super_token)
        
        # Section I: Audit Log
        test_section_i(super_token)
        
        # Section J: Regression
        test_section_j(super_token)
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Print summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    
    total_pass = 0
    total_fail = 0
    
    for section, tests in results.items():
        section_pass = sum(1 for t in tests if "✅ PASS" in t)
        section_fail = sum(1 for t in tests if "❌ FAIL" in t)
        total_pass += section_pass
        total_fail += section_fail
        
        print(f"\n{section}: {section_pass} PASS, {section_fail} FAIL")
        for test in tests:
            if "❌ FAIL" in test:
                print(f"  {test}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: {total_pass} PASS, {total_fail} FAIL")
    print(f"Completed at: {datetime.now().isoformat()}")
    print("="*80)

if __name__ == "__main__":
    main()
