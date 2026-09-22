#!/usr/bin/env python3
"""CARGO Privacy & Data Governance Backend Test — Oman PDPL technical readiness.

Tests all 31 items from the review request:
- Classifications (4 tests)
- Consent (6 tests)
- Policy (3 tests)
- DSR (5 tests)
- RoPA (1 test)
- Retention (1 test)
- Breach (4 tests)
- Processors/Transfers (2 tests)
- DPO/Residency (2 tests)
- Audit (1 test)
- RBAC negative (1 test)
- Regression light (1 test)
"""
import os
import sys
import requests
from datetime import datetime

# Read BASE_URL from frontend/.env
BASE_URL = None
try:
    with open("/app/frontend/.env", "r") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip() + "/api"
                break
except Exception as e:
    print(f"❌ Failed to read BASE_URL from /app/frontend/.env: {e}")
    sys.exit(1)

if not BASE_URL:
    print("❌ REACT_APP_BACKEND_URL not found in /app/frontend/.env")
    sys.exit(1)

print(f"🔗 BASE_URL: {BASE_URL}\n")

# Test counters
total_tests = 0
passed_tests = 0
failed_tests = 0

def test(name, condition, details=""):
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    if condition:
        passed_tests += 1
        print(f"✅ {name}")
        if details:
            print(f"   {details}")
    else:
        failed_tests += 1
        print(f"❌ {name}")
        if details:
            print(f"   {details}")

def section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

# ==================== AUTH ====================
section("AUTHENTICATION")

# Admin login
resp = requests.post(f"{BASE_URL}/auth/admin/login", json={"email": "admin@cargo.om", "password": "admin123"})
test("Admin login", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code != 200:
    print(f"❌ FATAL: Admin login failed. Cannot proceed. Response: {resp.text}")
    sys.exit(1)
admin_token = resp.json()["token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}
print(f"   Admin token: {admin_token[:20]}...")

# Customer OTP login
resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": "+96890000001", "role": "customer"})
test("Customer OTP request", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    demo_code = resp.json().get("demo_code")
    print(f"   Demo code: {demo_code}")
    resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={"phone": "+96890000001", "role": "customer", "code": demo_code})
    test("Customer OTP verify", resp.status_code == 200, f"HTTP {resp.status_code}")
    if resp.status_code == 200:
        customer_token = resp.json()["token"]
        customer_id = resp.json()["user"]["id"]
        customer_headers = {"Authorization": f"Bearer {customer_token}"}
        print(f"   Customer token: {customer_token[:20]}...")
        print(f"   Customer ID: {customer_id}")
    else:
        print(f"❌ FATAL: Customer OTP verify failed. Response: {resp.text}")
        sys.exit(1)
else:
    print(f"❌ FATAL: Customer OTP request failed. Response: {resp.text}")
    sys.exit(1)

# Driver OTP login
resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": "+96890000002", "role": "driver"})
test("Driver OTP request", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    demo_code = resp.json().get("demo_code")
    resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={"phone": "+96890000002", "role": "driver", "code": demo_code})
    test("Driver OTP verify", resp.status_code == 200, f"HTTP {resp.status_code}")
    if resp.status_code == 200:
        driver_token = resp.json()["token"]
        driver_headers = {"Authorization": f"Bearer {driver_token}"}
        print(f"   Driver token: {driver_token[:20]}...")
    else:
        print(f"❌ FATAL: Driver OTP verify failed. Response: {resp.text}")
        sys.exit(1)
else:
    print(f"❌ FATAL: Driver OTP request failed. Response: {resp.text}")
    sys.exit(1)

# Provider OTP login
resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": "+96890000005", "role": "provider"})
test("Provider OTP request", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    demo_code = resp.json().get("demo_code")
    resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={"phone": "+96890000005", "role": "provider", "code": demo_code})
    test("Provider OTP verify", resp.status_code == 200, f"HTTP {resp.status_code}")
    if resp.status_code == 200:
        provider_token = resp.json()["token"]
        provider_headers = {"Authorization": f"Bearer {provider_token}"}
        print(f"   Provider token: {provider_token[:20]}...")
    else:
        print(f"❌ FATAL: Provider OTP verify failed. Response: {resp.text}")
        sys.exit(1)
else:
    print(f"❌ FATAL: Provider OTP request failed. Response: {resp.text}")
    sys.exit(1)

# ==================== [C] CLASSIFICATION ====================
section("[C] DATA CLASSIFICATION")

# C1: GET classifications - seeded catalog present (>=15)
resp = requests.get(f"{BASE_URL}/admin/privacy/classifications", headers=admin_headers)
test("C1: GET /admin/privacy/classifications", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    classifications = resp.json()
    test("C1: Seeded catalog present (>=15)", len(classifications) >= 15, f"Count: {len(classifications)}")
    print(f"   Sample: {classifications[0] if classifications else 'None'}")
else:
    test("C1: Seeded catalog present (>=15)", False, f"Failed to fetch classifications")

# C2: POST classification with valid category
resp = requests.post(f"{BASE_URL}/admin/privacy/classifications", headers=admin_headers, 
                     json={"collection": "test_col", "field": "x", "category": "PERSONAL"})
test("C2: POST classification (valid category)", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    created_classification = resp.json()
    classification_id = created_classification.get("id")
    print(f"   Created classification ID: {classification_id}")
else:
    classification_id = None

# C3: POST classification with invalid category
resp = requests.post(f"{BASE_URL}/admin/privacy/classifications", headers=admin_headers,
                     json={"collection": "test_col", "field": "y", "category": "BOGUS"})
test("C3: POST classification (invalid category)", resp.status_code == 400, f"HTTP {resp.status_code}")
if resp.status_code == 400:
    test("C3: Error detail INVALID_CATEGORY", "INVALID_CATEGORY" in resp.text, f"Detail: {resp.json().get('detail')}")

# C4: PUT classification
if classification_id:
    resp = requests.put(f"{BASE_URL}/admin/privacy/classifications/{classification_id}", headers=admin_headers,
                        json={"category": "INTERNAL"})
    test("C4: PUT classification", resp.status_code == 200, f"HTTP {resp.status_code}")
    if resp.status_code == 200:
        updated = resp.json()
        test("C4: Category updated to INTERNAL", updated.get("category") == "INTERNAL", f"Category: {updated.get('category')}")
else:
    test("C4: PUT classification", False, "Skipped - no classification_id from C2")

# ==================== [CONSENT] ====================
section("[CONSENT] CONSENT RECORDS")

# CONSENT5: POST consent with basis=consent
resp = requests.post(f"{BASE_URL}/privacy/consent", headers=customer_headers,
                     json={"purpose": "marketing", "basis": "consent", "version": "v1", "source": "app"})
test("CONSENT5: POST consent (basis=consent)", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    consent1 = resp.json()
    consent1_id = consent1.get("id")
    test("CONSENT5: status=ACTIVE", consent1.get("status") == "ACTIVE", f"Status: {consent1.get('status')}")
    print(f"   Consent ID: {consent1_id}")
else:
    consent1_id = None

# CONSENT6: POST consent with basis=contractual_necessity
resp = requests.post(f"{BASE_URL}/privacy/consent", headers=customer_headers,
                     json={"purpose": "service", "basis": "contractual_necessity"})
test("CONSENT6: POST consent (basis=contractual_necessity)", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    consent2 = resp.json()
    consent2_id = consent2.get("id")
    print(f"   Consent ID: {consent2_id}")
else:
    consent2_id = None

# CONSENT7: POST consent with invalid basis
resp = requests.post(f"{BASE_URL}/privacy/consent", headers=customer_headers,
                     json={"purpose": "x", "basis": "BOGUS"})
test("CONSENT7: POST consent (invalid basis)", resp.status_code == 400, f"HTTP {resp.status_code}")
if resp.status_code == 400:
    test("CONSENT7: Error detail INVALID_BASIS", "INVALID_BASIS" in resp.text, f"Detail: {resp.json().get('detail')}")

# CONSENT8: GET my consents
resp = requests.get(f"{BASE_URL}/privacy/consent/mine", headers=customer_headers)
test("CONSENT8: GET /privacy/consent/mine", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    my_consents = resp.json()
    test("CONSENT8: List contains created records", len(my_consents) >= 2, f"Count: {len(my_consents)}")
    print(f"   Consents: {[c.get('purpose') for c in my_consents]}")

# CONSENT9: Withdraw consent
if consent1_id:
    resp = requests.post(f"{BASE_URL}/privacy/consent/{consent1_id}/withdraw", headers=customer_headers)
    test("CONSENT9: POST withdraw consent", resp.status_code == 200, f"HTTP {resp.status_code}")
    if resp.status_code == 200:
        withdrawn = resp.json()
        test("CONSENT9: status=WITHDRAWN", withdrawn.get("status") == "WITHDRAWN", f"Status: {withdrawn.get('status')}")
        test("CONSENT9: withdrawn_at set", withdrawn.get("withdrawn_at") is not None, f"withdrawn_at: {withdrawn.get('withdrawn_at')}")
        
        # CRITICAL: Confirm customer account still exists
        resp = requests.get(f"{BASE_URL}/auth/me", headers=customer_headers)
        test("CONSENT9: Customer account still exists (GET /auth/me)", resp.status_code == 200, f"HTTP {resp.status_code}")
        if resp.status_code == 200:
            print(f"   ✅ CRITICAL: Withdrawal did NOT delete customer account")
else:
    test("CONSENT9: POST withdraw consent", False, "Skipped - no consent1_id from CONSENT5")

# CONSENT10: Admin GET consent by user_id
resp = requests.get(f"{BASE_URL}/admin/privacy/consent?user_id={customer_id}", headers=admin_headers)
test("CONSENT10: GET /admin/privacy/consent?user_id", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    admin_consents = resp.json()
    test("CONSENT10: Shows customer records", len(admin_consents) >= 2, f"Count: {len(admin_consents)}")

# ==================== [POLICY] ====================
section("[POLICY] PRIVACY POLICY")

# POLICY11: GET policy as customer
resp = requests.get(f"{BASE_URL}/privacy/policy", headers=customer_headers)
test("POLICY11: GET /privacy/policy", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    policy = resp.json()
    test("POLICY11: Has privacy_policy_version", "privacy_policy_version" in policy, f"Version: {policy.get('privacy_policy_version')}")
    print(f"   Policy: {policy}")

# POLICY12: POST accept policy
resp = requests.post(f"{BASE_URL}/privacy/policy/accept", headers=customer_headers)
test("POLICY12: POST /privacy/policy/accept", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    accepted = resp.json()
    test("POLICY12: accepted_version matches", accepted.get("accepted_version") is not None, f"Version: {accepted.get('accepted_version')}")
    
    # Check GET /auth/me shows privacy_policy_accepted_version
    resp = requests.get(f"{BASE_URL}/auth/me", headers=customer_headers)
    if resp.status_code == 200:
        me = resp.json()
        test("POLICY12: GET /auth/me shows privacy_policy_accepted_version", 
             "privacy_policy_accepted_version" in me, f"Version: {me.get('privacy_policy_accepted_version')}")

# POLICY13: Admin update policy
resp = requests.put(f"{BASE_URL}/admin/privacy/policy", headers=admin_headers,
                    json={"privacy_policy_version": "2025.1", "status": "ACTIVE", "effective_date": "2025-01-01"})
test("POLICY13: PUT /admin/privacy/policy", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    # Verify GET shows 2025.1
    resp = requests.get(f"{BASE_URL}/admin/privacy/policy", headers=admin_headers)
    if resp.status_code == 200:
        policy = resp.json()
        test("POLICY13: GET shows version 2025.1", policy.get("privacy_policy_version") == "2025.1", 
             f"Version: {policy.get('privacy_policy_version')}")

# ==================== [DSR] DATA SUBJECT REQUESTS ====================
section("[DSR] DATA SUBJECT REQUESTS")

# DSR14: POST DSR with valid request_type
resp = requests.post(f"{BASE_URL}/privacy/requests", headers=customer_headers,
                     json={"request_type": "ACCESS", "reason": "want my data"})
test("DSR14: POST /privacy/requests (valid type)", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    dsr = resp.json()
    dsr_id = dsr.get("id")
    test("DSR14: status=RECEIVED", dsr.get("status") == "RECEIVED", f"Status: {dsr.get('status')}")
    test("DSR14: due_at set", dsr.get("due_at") is not None, f"due_at: {dsr.get('due_at')}")
    print(f"   DSR ID: {dsr_id}")
    print(f"   received_at: {dsr.get('received_at')}")
    print(f"   due_at: {dsr.get('due_at')}")
else:
    dsr_id = None

# DSR15: POST DSR with invalid request_type
resp = requests.post(f"{BASE_URL}/privacy/requests", headers=customer_headers,
                     json={"request_type": "BOGUS"})
test("DSR15: POST /privacy/requests (invalid type)", resp.status_code == 400, f"HTTP {resp.status_code}")

# DSR16: GET my DSRs
resp = requests.get(f"{BASE_URL}/privacy/requests/mine", headers=customer_headers)
test("DSR16: GET /privacy/requests/mine", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    my_dsrs = resp.json()
    test("DSR16: Contains created DSR", len(my_dsrs) >= 1, f"Count: {len(my_dsrs)}")

# DSR17: Admin GET/GET{id}/PUT{id}/status
resp = requests.get(f"{BASE_URL}/admin/privacy/requests", headers=admin_headers)
test("DSR17: GET /admin/privacy/requests", resp.status_code == 200, f"HTTP {resp.status_code}")

if dsr_id:
    resp = requests.get(f"{BASE_URL}/admin/privacy/requests/{dsr_id}", headers=admin_headers)
    test("DSR17: GET /admin/privacy/requests/{id}", resp.status_code == 200, f"HTTP {resp.status_code}")
    
    resp = requests.put(f"{BASE_URL}/admin/privacy/requests/{dsr_id}/status", headers=admin_headers,
                        json={"status": "COMPLETED", "resolution_notes": "done"})
    test("DSR17: PUT /admin/privacy/requests/{id}/status", resp.status_code == 200, f"HTTP {resp.status_code}")
    if resp.status_code == 200:
        resolved = resp.json()
        test("DSR17: resolved_at set", resolved.get("resolved_at") is not None, f"resolved_at: {resolved.get('resolved_at')}")
        test("DSR17: resolved_by set", resolved.get("resolved_by") is not None, f"resolved_by: {resolved.get('resolved_by')}")
else:
    test("DSR17: Admin DSR operations", False, "Skipped - no dsr_id from DSR14")

# DSR18: PERMISSION - create finance_accountant admin and test 403
resp = requests.post(f"{BASE_URL}/admin/admins", headers=admin_headers,
                     json={"name": "ops", "email": "ops_priv@cargo.om", "password": "ops12345", "admin_role_key": "finance_accountant"})
test("DSR18: Create finance_accountant admin", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    # Login as finance_accountant
    resp = requests.post(f"{BASE_URL}/auth/admin/login", json={"email": "ops_priv@cargo.om", "password": "ops12345"})
    test("DSR18: Login finance_accountant", resp.status_code == 200, f"HTTP {resp.status_code}")
    if resp.status_code == 200:
        finance_token = resp.json()["token"]
        finance_headers = {"Authorization": f"Bearer {finance_token}"}
        
        # Try to access privacy requests - should be 403
        resp = requests.get(f"{BASE_URL}/admin/privacy/requests", headers=finance_headers)
        test("DSR18: finance_accountant GET /admin/privacy/requests", resp.status_code == 403, f"HTTP {resp.status_code}")
        if resp.status_code == 403:
            print(f"   ✅ finance_accountant lacks privacy.requests permission")

# Driver token GET /admin/privacy/requests -> 403
resp = requests.get(f"{BASE_URL}/admin/privacy/requests", headers=driver_headers)
test("DSR18: driver GET /admin/privacy/requests", resp.status_code == 403, f"HTTP {resp.status_code}")

# ==================== [RoPA] ====================
section("[RoPA] RECORDS OF PROCESSING ACTIVITIES")

# RoPA19: GET RoPA (>=2 seeded), POST, PUT
resp = requests.get(f"{BASE_URL}/admin/privacy/ropa", headers=admin_headers)
test("RoPA19: GET /admin/privacy/ropa", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    ropa_list = resp.json()
    test("RoPA19: Seeded RoPA (>=2)", len(ropa_list) >= 2, f"Count: {len(ropa_list)}")
    print(f"   Sample: {ropa_list[0].get('name') if ropa_list else 'None'}")

resp = requests.post(f"{BASE_URL}/admin/privacy/ropa", headers=admin_headers,
                     json={"name": "Test activity", "purpose": "p", "data_categories": ["PERSONAL"], "legal_basis": "consent"})
test("RoPA19: POST /admin/privacy/ropa", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    ropa = resp.json()
    ropa_id = ropa.get("id")
    print(f"   RoPA ID: {ropa_id}")
    
    if ropa_id:
        resp = requests.put(f"{BASE_URL}/admin/privacy/ropa/{ropa_id}", headers=admin_headers,
                            json={"status": "ACTIVE"})
        test("RoPA19: PUT /admin/privacy/ropa/{id}", resp.status_code == 200, f"HTTP {resp.status_code}")

# ==================== [RETENTION] ====================
section("[RETENTION] RETENTION POLICIES")

# RETENTION20: GET retention, POST, PUT
resp = requests.get(f"{BASE_URL}/admin/privacy/retention", headers=admin_headers)
test("RETENTION20: GET /admin/privacy/retention", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    retention_list = resp.json()
    test("RETENTION20: Seeded DRAFT placeholders", len(retention_list) > 0, f"Count: {len(retention_list)}")
    if retention_list:
        sample = retention_list[0]
        test("RETENTION20: retention_period empty", sample.get("retention_period") == "", 
             f"retention_period: '{sample.get('retention_period')}'")
        print(f"   Sample: {sample.get('data_category')} - status: {sample.get('status')}")

resp = requests.post(f"{BASE_URL}/admin/privacy/retention", headers=admin_headers,
                     json={"data_category": "PERSONAL", "retention_period": "", "retention_basis": "pending", "status": "DRAFT"})
test("RETENTION20: POST /admin/privacy/retention", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    retention = resp.json()
    retention_id = retention.get("id")
    print(f"   Retention ID: {retention_id}")
    
    if retention_id:
        resp = requests.put(f"{BASE_URL}/admin/privacy/retention/{retention_id}", headers=admin_headers,
                            json={"status": "ACTIVE"})
        test("RETENTION20: PUT /admin/privacy/retention/{id}", resp.status_code == 200, f"HTTP {resp.status_code}")

# Confirm nothing got deleted
resp = requests.get(f"{BASE_URL}/auth/me", headers=customer_headers)
test("RETENTION20: Customer account still exists (no deletion)", resp.status_code == 200, f"HTTP {resp.status_code}")

# ==================== [BREACH] ====================
section("[BREACH] DATA BREACHES")

# BREACH21: POST breach
resp = requests.post(f"{BASE_URL}/admin/privacy/breaches", headers=admin_headers,
                     json={"severity": "HIGH", "affected_data_categories": ["PERSONAL", "LOCATION"], 
                           "affected_users_count": 3, "description": "test"})
test("BREACH21: POST /admin/privacy/breaches", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    breach = resp.json()
    breach_id = breach.get("id")
    test("BREACH21: status=OPEN", breach.get("status") == "OPEN", f"Status: {breach.get('status')}")
    test("BREACH21: authority_notification_status=NOT_NOTIFIED", 
         breach.get("authority_notification_status") == "NOT_NOTIFIED", 
         f"authority_notification_status: {breach.get('authority_notification_status')}")
    print(f"   Breach ID: {breach_id}")
else:
    breach_id = None

# BREACH22: GET breaches list and by ID
resp = requests.get(f"{BASE_URL}/admin/privacy/breaches", headers=admin_headers)
test("BREACH22: GET /admin/privacy/breaches", resp.status_code == 200, f"HTTP {resp.status_code}")

if breach_id:
    resp = requests.get(f"{BASE_URL}/admin/privacy/breaches/{breach_id}", headers=admin_headers)
    test("BREACH22: GET /admin/privacy/breaches/{id}", resp.status_code == 200, f"HTTP {resp.status_code}")
else:
    test("BREACH22: GET /admin/privacy/breaches/{id}", False, "Skipped - no breach_id from BREACH21")

# BREACH23: PUT breach status multiple times
if breach_id:
    resp = requests.put(f"{BASE_URL}/admin/privacy/breaches/{breach_id}/status", headers=admin_headers,
                        json={"status": "INVESTIGATING"})
    test("BREACH23: PUT status=INVESTIGATING", resp.status_code == 200, f"HTTP {resp.status_code}")
    
    resp = requests.put(f"{BASE_URL}/admin/privacy/breaches/{breach_id}/status", headers=admin_headers,
                        json={"status": "CLOSED"})
    test("BREACH23: PUT status=CLOSED", resp.status_code == 200, f"HTTP {resp.status_code}")
    if resp.status_code == 200:
        closed_breach = resp.json()
        test("BREACH23: closed_at set", closed_breach.get("closed_at") is not None, 
             f"closed_at: {closed_breach.get('closed_at')}")
        test("BREACH23: history has multiple entries", len(closed_breach.get("history", [])) > 1, 
             f"History count: {len(closed_breach.get('history', []))}")
else:
    test("BREACH23: PUT breach status", False, "Skipped - no breach_id from BREACH21")

# BREACH24: PERMISSION - finance_accountant cannot access breaches
if 'finance_headers' in locals():
    resp = requests.get(f"{BASE_URL}/admin/privacy/breaches", headers=finance_headers)
    test("BREACH24: finance_accountant GET /admin/privacy/breaches", resp.status_code == 403, f"HTTP {resp.status_code}")
else:
    test("BREACH24: finance_accountant GET /admin/privacy/breaches", False, "Skipped - finance_accountant not created")

# ==================== [PROCESSORS/TRANSFERS] ====================
section("[PROCESSORS/TRANSFERS] DATA PROCESSORS & CROSS-BORDER TRANSFERS")

# PROCESSORS25: GET processors, POST new processor
resp = requests.get(f"{BASE_URL}/admin/privacy/processors", headers=admin_headers)
test("PROCESSORS25: GET /admin/privacy/processors", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    processors = resp.json()
    nominatim = [p for p in processors if "Nominatim" in p.get("provider_name", "")]
    test("PROCESSORS25: Includes OpenStreetMap Nominatim", len(nominatim) > 0, f"Found: {len(nominatim)}")
    if nominatim:
        test("PROCESSORS25: Nominatim transfer_outside_oman=true", 
             nominatim[0].get("transfer_outside_oman") == True, 
             f"transfer_outside_oman: {nominatim[0].get('transfer_outside_oman')}")
        print(f"   Nominatim: {nominatim[0].get('provider_name')}")

resp = requests.post(f"{BASE_URL}/admin/privacy/processors", headers=admin_headers,
                     json={"provider_name": "TestSMS", "service_type": "SMS", "country": "X"})
test("PROCESSORS25: POST /admin/privacy/processors", resp.status_code == 200, f"HTTP {resp.status_code}")

# TRANSFERS26: GET transfers, POST new transfer
resp = requests.get(f"{BASE_URL}/admin/privacy/transfers", headers=admin_headers)
test("TRANSFERS26: GET /admin/privacy/transfers", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    transfers = resp.json()
    nominatim_transfer = [t for t in transfers if "Nominatim" in t.get("recipient", "")]
    test("TRANSFERS26: Includes Nominatim transfer", len(nominatim_transfer) > 0, f"Found: {len(nominatim_transfer)}")
    if nominatim_transfer:
        test("TRANSFERS26: approval_status=PENDING", 
             nominatim_transfer[0].get("approval_status") == "PENDING", 
             f"approval_status: {nominatim_transfer[0].get('approval_status')}")

resp = requests.post(f"{BASE_URL}/admin/privacy/transfers", headers=admin_headers,
                     json={"data_categories": ["PERSONAL"], "destination_country": "X", 
                           "recipient": "TestSMS", "approval_status": "PENDING"})
test("TRANSFERS26: POST /admin/privacy/transfers", resp.status_code == 200, f"HTTP {resp.status_code}")

# ==================== [DPO/RESIDENCY] ====================
section("[DPO/RESIDENCY] DPO & DATA RESIDENCY")

# DPO27: GET DPO, PUT DPO
resp = requests.get(f"{BASE_URL}/admin/privacy/dpo", headers=admin_headers)
test("DPO27: GET /admin/privacy/dpo", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    dpo = resp.json()
    test("DPO27: dpo_status=NOT_APPOINTED", dpo.get("dpo_status") == "NOT_APPOINTED", 
         f"dpo_status: {dpo.get('dpo_status')}")
    print(f"   DPO: {dpo}")

resp = requests.put(f"{BASE_URL}/admin/privacy/dpo", headers=admin_headers,
                    json={"dpo_name": "A", "dpo_status": "APPOINTED", "privacy_contact_email": "dpo@cargo.om"})
test("DPO27: PUT /admin/privacy/dpo", resp.status_code == 200, f"HTTP {resp.status_code}")

# RESIDENCY28: GET residency, PUT residency
resp = requests.get(f"{BASE_URL}/admin/privacy/residency", headers=admin_headers)
test("RESIDENCY28: GET /admin/privacy/residency", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    residency = resp.json()
    test("RESIDENCY28: environment=development", residency.get("environment") == "development", 
         f"environment: {residency.get('environment')}")
    test("RESIDENCY28: regions UNKNOWN (NOT claiming Oman)", 
         "UNKNOWN" in str(residency), 
         f"Residency: {residency}")
    print(f"   Residency: {residency}")

resp = requests.put(f"{BASE_URL}/admin/privacy/residency", headers=admin_headers,
                    json={"environment": "staging"})
test("RESIDENCY28: PUT /admin/privacy/residency", resp.status_code == 200, f"HTTP {resp.status_code}")

# ==================== [AUDIT] ====================
section("[AUDIT] AUDIT LOG")

# AUDIT29: GET audit logs and verify privacy actions
resp = requests.get(f"{BASE_URL}/admin/audit-logs", headers=admin_headers)
test("AUDIT29: GET /admin/audit-logs", resp.status_code == 200, f"HTTP {resp.status_code}")
if resp.status_code == 200:
    audit_logs = resp.json()
    actions = [log.get("action") for log in audit_logs]
    
    expected_actions = [
        "consent_recorded", "consent_withdrawn", "privacy_policy_accepted",
        "data_subject_request_created", "data_subject_request_resolved",
        "breach_created", "breach_status_changed", "processor_added", "transfer_recorded"
    ]
    
    found_actions = []
    for action in expected_actions:
        if action in actions:
            found_actions.append(action)
    
    test("AUDIT29: Contains privacy actions", len(found_actions) >= 5, 
         f"Found {len(found_actions)}/{len(expected_actions)}: {found_actions}")
    print(f"   Total audit logs: {len(audit_logs)}")
    print(f"   Privacy actions found: {found_actions}")

# ==================== [RBAC NEGATIVE] ====================
section("[RBAC NEGATIVE] RBAC ENFORCEMENT")

# RBAC30: Customer and driver cannot access /admin/privacy/*
resp = requests.get(f"{BASE_URL}/admin/privacy/classifications", headers=customer_headers)
test("RBAC30: Customer GET /admin/privacy/classifications", resp.status_code == 403, f"HTTP {resp.status_code}")

resp = requests.get(f"{BASE_URL}/admin/privacy/classifications", headers=driver_headers)
test("RBAC30: Driver GET /admin/privacy/classifications", resp.status_code == 403, f"HTTP {resp.status_code}")

# ==================== [REGRESSION LIGHT] ====================
section("[REGRESSION LIGHT] BASIC FUNCTIONALITY")

# REGRESSION31: Basic auth and operations still work
resp = requests.post(f"{BASE_URL}/auth/admin/login", json={"email": "admin@cargo.om", "password": "admin123"})
test("REGRESSION31: Admin login", resp.status_code == 200, f"HTTP {resp.status_code}")

resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": "+96890000001", "role": "customer"})
test("REGRESSION31: Customer OTP", resp.status_code == 200, f"HTTP {resp.status_code}")

resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": "+96890000002", "role": "driver"})
test("REGRESSION31: Driver OTP", resp.status_code == 200, f"HTTP {resp.status_code}")

resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": "+96890000005", "role": "provider"})
test("REGRESSION31: Provider OTP", resp.status_code == 200, f"HTTP {resp.status_code}")

# Customer POST shipment
resp = requests.post(f"{BASE_URL}/shipments", headers=customer_headers,
                     json={
                         "title": "Test shipment privacy",
                         "description": "Test",
                         "category": "GENERAL",
                         "weight": 10,
                         "pickup_location": {"address": "Muscat", "lat": 23.5880, "lng": 58.3829, "city": "Muscat", "area": "", "country": "Oman"},
                         "delivery_location": {"address": "Salalah", "lat": 17.0150, "lng": 54.0924, "city": "Salalah", "area": "", "country": "Oman"},
                         "status": "PUBLISHED"
                     })
test("REGRESSION31: Customer POST /shipments (PUBLISHED)", resp.status_code == 200, f"HTTP {resp.status_code}")

# Provider POST vehicle
resp = requests.post(f"{BASE_URL}/provider/vehicles", headers=provider_headers,
                     json={"plate_number": "PV-REG-9"})
test("REGRESSION31: Provider POST /provider/vehicles", resp.status_code == 200, f"HTTP {resp.status_code}")

# ==================== SUMMARY ====================
section("TEST SUMMARY")
print(f"\n{'='*80}")
print(f"  TOTAL TESTS: {total_tests}")
print(f"  ✅ PASSED: {passed_tests}")
print(f"  ❌ FAILED: {failed_tests}")
print(f"  SUCCESS RATE: {(passed_tests/total_tests*100):.1f}%")
print(f"{'='*80}\n")

if failed_tests == 0:
    print("🎉 ALL TESTS PASSED!")
    sys.exit(0)
else:
    print(f"⚠️  {failed_tests} TEST(S) FAILED")
    sys.exit(1)
