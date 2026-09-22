#!/usr/bin/env python3
"""
CARGO Regulatory Core Backend Test
Tests: Eligibility Service + Transport Document + Integration into bid/trip flow
"""
import os
import sys
import requests
import json
from datetime import datetime, timedelta

# Get base URL from frontend .env
BASE_URL = "https://06e06483-77fb-4d0b-98ef-6858f2868e3e.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"
CUSTOMER_PHONE = "+96890000001"
DRIVER_PHONE = "+96890000002"
PROVIDER_PHONE = "+96890000005"

# Global tokens
admin_token = None
customer_token = None
driver_token = None
provider_token = None

# Test data IDs
driver_id = None
provider_id = None
shipment_id = None
bid_id = None
trip_id = None
transport_doc_id = None
vehicle_id = None

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def admin_login():
    global admin_token
    log("=== Admin Login ===")
    r = requests.post(f"{BASE_URL}/auth/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    log(f"POST /api/auth/admin/login -> {r.status_code}")
    if r.status_code == 200:
        admin_token = r.json()["token"]
        log(f"✅ Admin login successful, token obtained")
        return True
    else:
        log(f"❌ Admin login failed: {r.text}")
        return False

def otp_login(phone, role):
    log(f"=== OTP Login: {phone} ({role}) ===")
    # Request OTP
    r1 = requests.post(f"{BASE_URL}/auth/otp/request", json={
        "phone": phone,
        "role": role
    })
    log(f"POST /api/auth/otp/request -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ OTP request failed: {r1.text}")
        return None
    
    demo_code = r1.json().get("demo_code")
    log(f"Demo OTP code: {demo_code}")
    
    # Verify OTP
    r2 = requests.post(f"{BASE_URL}/auth/otp/verify", json={
        "phone": phone,
        "code": demo_code,
        "role": role
    })
    log(f"POST /api/auth/otp/verify -> {r2.status_code}")
    if r2.status_code == 200:
        token = r2.json()["token"]
        user_id = r2.json()["user"]["id"]
        log(f"✅ OTP login successful, token obtained, user_id={user_id}")
        return token, user_id
    else:
        log(f"❌ OTP verify failed: {r2.text}")
        return None

def get_driver_id():
    global driver_id
    log("=== Get Driver ID ===")
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{BASE_URL}/admin/users?role=driver", headers=headers)
    log(f"GET /api/admin/users?role=driver -> {r.status_code}")
    if r.status_code == 200:
        users = r.json()
        for u in users:
            if u.get("phone") == DRIVER_PHONE:
                driver_id = u["id"]
                log(f"✅ Found driver {DRIVER_PHONE}: id={driver_id}")
                return driver_id
    log(f"❌ Failed to get driver ID")
    return None

def get_provider_id():
    global provider_id
    log("=== Get Provider ID ===")
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{BASE_URL}/admin/users?role=provider", headers=headers)
    log(f"GET /api/admin/users?role=provider -> {r.status_code}")
    if r.status_code == 200:
        users = r.json()
        for u in users:
            if u.get("phone") == PROVIDER_PHONE:
                provider_id = u["id"]
                log(f"✅ Found provider {PROVIDER_PHONE}: id={provider_id}")
                return provider_id
    log(f"❌ Failed to get provider ID")
    return None

# ==================================================================================
# [E] ELIGIBILITY SERVICE via admin visibility endpoints
# ==================================================================================
def test_e1_application_eligibility():
    log("\n=== [E1] GET /api/admin/compliance/application ===")
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{BASE_URL}/admin/compliance/application", headers=headers)
    log(f"GET /api/admin/compliance/application -> {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        log(f"Response: {json.dumps(data, indent=2)}")
        if data.get("license_status") == "ACTIVE" and data.get("eligible") == True:
            log(f"✅ E1 PASS: license_status=ACTIVE, eligible=true")
            return True
        else:
            log(f"❌ E1 FAIL: Expected license_status=ACTIVE and eligible=true, got {data}")
            return False
    else:
        log(f"❌ E1 FAIL: {r.status_code} {r.text}")
        return False

def test_e2_driver_eligibility():
    log("\n=== [E2] GET /api/admin/compliance/check/driver/{id} ===")
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{BASE_URL}/admin/compliance/check/driver/{driver_id}", headers=headers)
    log(f"GET /api/admin/compliance/check/driver/{driver_id} -> {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        log(f"Response: {json.dumps(data, indent=2)}")
        if data.get("eligible") == True:
            log(f"✅ E2 PASS: driver eligible=true (training COMPLETED seeded)")
            return True
        else:
            log(f"❌ E2 FAIL: Expected eligible=true, got {data}")
            return False
    else:
        log(f"❌ E2 FAIL: {r.status_code} {r.text}")
        return False

def test_e3_provider_eligibility():
    log("\n=== [E3] GET /api/admin/compliance/check/provider/{id} ===")
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{BASE_URL}/admin/compliance/check/provider/{provider_id}", headers=headers)
    log(f"GET /api/admin/compliance/check/provider/{provider_id} -> {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        log(f"Response: {json.dumps(data, indent=2)}")
        if data.get("eligible") == True:
            log(f"✅ E3 PASS: provider eligible=true (carrier_license ACTIVE seeded)")
            return True
        else:
            log(f"❌ E3 FAIL: Expected eligible=true, got {data}")
            return False
    else:
        log(f"❌ E3 FAIL: {r.status_code} {r.text}")
        return False

def test_e4_block_driver_training():
    log("\n=== [E4] BLOCK DRIVER TRAINING ===")
    headers = {"Authorization": f"Bearer {driver_token}"}
    
    # Set training to IN_PROGRESS
    log("Step 1: Set driver_training_status to IN_PROGRESS")
    r1 = requests.put(f"{BASE_URL}/driver/regulatory", headers=headers, json={
        "driver_training_status": "IN_PROGRESS"
    })
    log(f"PUT /api/driver/regulatory -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ E4 FAIL: Failed to update driver regulatory: {r1.text}")
        return False
    
    # Check eligibility - should be false
    log("Step 2: Check driver eligibility (should be false)")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    r2 = requests.get(f"{BASE_URL}/admin/compliance/check/driver/{driver_id}", headers=admin_headers)
    log(f"GET /api/admin/compliance/check/driver/{driver_id} -> {r2.status_code}")
    if r2.status_code == 200:
        data = r2.json()
        log(f"Response: {json.dumps(data, indent=2)}")
        if data.get("eligible") == False:
            reasons = data.get("reasons", [])
            codes = [r.get("code") for r in reasons]
            if "DRIVER_APP_TRAINING_NOT_COMPLETED" in codes:
                log(f"✅ E4 PASS (blocked): eligible=false, reason DRIVER_APP_TRAINING_NOT_COMPLETED")
            else:
                log(f"❌ E4 FAIL: Expected DRIVER_APP_TRAINING_NOT_COMPLETED in reasons, got {codes}")
                return False
        else:
            log(f"❌ E4 FAIL: Expected eligible=false, got {data}")
            return False
    else:
        log(f"❌ E4 FAIL: {r2.status_code} {r2.text}")
        return False
    
    # RESTORE training to COMPLETED
    log("Step 3: RESTORE driver_training_status to COMPLETED")
    r3 = requests.put(f"{BASE_URL}/driver/regulatory", headers=headers, json={
        "driver_training_status": "COMPLETED"
    })
    log(f"PUT /api/driver/regulatory -> {r3.status_code}")
    if r3.status_code != 200:
        log(f"❌ E4 FAIL: Failed to restore driver regulatory: {r3.text}")
        return False
    
    # Verify restored
    r4 = requests.get(f"{BASE_URL}/admin/compliance/check/driver/{driver_id}", headers=admin_headers)
    log(f"GET /api/admin/compliance/check/driver/{driver_id} -> {r4.status_code}")
    if r4.status_code == 200:
        data = r4.json()
        if data.get("eligible") == True:
            log(f"✅ E4 PASS (restored): eligible=true after COMPLETED")
            return True
        else:
            log(f"❌ E4 FAIL: Expected eligible=true after restore, got {data}")
            return False
    else:
        log(f"❌ E4 FAIL: {r4.status_code} {r4.text}")
        return False

def test_e4_block_vehicle_operating_card():
    global vehicle_id
    log("\n=== [E4] BLOCK VEHICLE OPERATING CARD ===")
    headers = {"Authorization": f"Bearer {provider_token}"}
    
    # Create vehicle with EXPIRED operating card (use timestamp for unique plate)
    import time
    unique_plate = f"ELIG-{int(time.time()) % 10000}"
    log(f"Step 1: Create vehicle with operating_card_status=EXPIRED (plate: {unique_plate})")
    r1 = requests.post(f"{BASE_URL}/provider/vehicles", headers=headers, json={
        "plate_number": unique_plate,
        "regulatory": {
            "operating_card_status": "EXPIRED"
        }
    })
    log(f"POST /api/provider/vehicles -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ E4 FAIL: Failed to create vehicle: {r1.text}")
        return False
    
    vehicle_id = r1.json()["id"]
    log(f"Vehicle created: id={vehicle_id}")
    
    # Check vehicle eligibility - should be false with EXPIRED
    log("Step 2: Check vehicle eligibility (should be false, EXPIRED)")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    r2 = requests.get(f"{BASE_URL}/admin/compliance/check/vehicle/{vehicle_id}", headers=admin_headers)
    log(f"GET /api/admin/compliance/check/vehicle/{vehicle_id} -> {r2.status_code}")
    if r2.status_code == 200:
        data = r2.json()
        log(f"Response: {json.dumps(data, indent=2)}")
        if data.get("eligible") == False:
            reasons = data.get("reasons", [])
            codes = [r.get("code") for r in reasons]
            if "VEHICLE_OPERATING_CARD_EXPIRED" in codes:
                log(f"✅ E4 PASS: EXPIRED blocked correctly")
            else:
                log(f"❌ E4 FAIL: Expected VEHICLE_OPERATING_CARD_EXPIRED, got {codes}")
                return False
        else:
            log(f"❌ E4 FAIL: Expected eligible=false for EXPIRED, got {data}")
            return False
    else:
        log(f"❌ E4 FAIL: {r2.status_code} {r2.text}")
        return False
    
    # Test SUSPENDED
    log("Step 3: Update to SUSPENDED")
    r3 = requests.put(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=headers, json={
        "plate_number": unique_plate,
        "regulatory": {
            "operating_card_status": "SUSPENDED"
        }
    })
    log(f"PUT /api/provider/vehicles/{vehicle_id} -> {r3.status_code}")
    if r3.status_code != 200:
        log(f"❌ E4 FAIL: Failed to update vehicle: {r3.text}")
        return False
    
    r4 = requests.get(f"{BASE_URL}/admin/compliance/check/vehicle/{vehicle_id}", headers=admin_headers)
    if r4.status_code == 200:
        data = r4.json()
        if data.get("eligible") == False:
            codes = [r.get("code") for r in data.get("reasons", [])]
            if "VEHICLE_OPERATING_CARD_SUSPENDED" in codes:
                log(f"✅ E4 PASS: SUSPENDED blocked correctly")
            else:
                log(f"❌ E4 FAIL: Expected VEHICLE_OPERATING_CARD_SUSPENDED, got {codes}")
                return False
        else:
            log(f"❌ E4 FAIL: Expected eligible=false for SUSPENDED")
            return False
    
    # Test INACTIVE
    log("Step 4: Update to INACTIVE")
    r5 = requests.put(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=headers, json={
        "plate_number": unique_plate,
        "regulatory": {
            "operating_card_status": "INACTIVE"
        }
    })
    log(f"PUT /api/provider/vehicles/{vehicle_id} -> {r5.status_code}")
    
    r6 = requests.get(f"{BASE_URL}/admin/compliance/check/vehicle/{vehicle_id}", headers=admin_headers)
    if r6.status_code == 200:
        data = r6.json()
        if data.get("eligible") == False:
            codes = [r.get("code") for r in data.get("reasons", [])]
            if "VEHICLE_OPERATING_CARD_INACTIVE" in codes:
                log(f"✅ E4 PASS: INACTIVE blocked correctly")
            else:
                log(f"❌ E4 FAIL: Expected VEHICLE_OPERATING_CARD_INACTIVE, got {codes}")
                return False
        else:
            log(f"❌ E4 FAIL: Expected eligible=false for INACTIVE")
            return False
    
    # RESTORE to ACTIVE
    log("Step 5: RESTORE to ACTIVE")
    r7 = requests.put(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=headers, json={
        "plate_number": unique_plate,
        "regulatory": {
            "operating_card_status": "ACTIVE"
        }
    })
    log(f"PUT /api/provider/vehicles/{vehicle_id} -> {r7.status_code}")
    
    r8 = requests.get(f"{BASE_URL}/admin/compliance/check/vehicle/{vehicle_id}", headers=admin_headers)
    if r8.status_code == 200:
        data = r8.json()
        if data.get("eligible") == True:
            log(f"✅ E4 PASS (restored): ACTIVE eligible=true")
            return True
        else:
            log(f"❌ E4 FAIL: Expected eligible=true for ACTIVE, got {data}")
            return False
    else:
        log(f"❌ E4 FAIL: {r8.status_code} {r8.text}")
        return False

def test_e4_block_application_license():
    log("\n=== [E4] BLOCK APPLICATION LICENSE ===")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get current app license
    log("Step 1: Get current app license")
    r0 = requests.get(f"{BASE_URL}/admin/app-license", headers=headers)
    log(f"GET /api/admin/app-license -> {r0.status_code}")
    if r0.status_code != 200:
        log(f"❌ E4 FAIL: Failed to get app license: {r0.text}")
        return False
    
    current_license = r0.json()
    log(f"Current license: {json.dumps(current_license, indent=2)}")
    
    # Set to EXPIRED
    log("Step 2: Set app_license status to EXPIRED")
    r1 = requests.put(f"{BASE_URL}/admin/app-license", headers=headers, json={
        "license_number": current_license.get("license_number", ""),
        "license_type": current_license.get("license_type", "trucks"),
        "issuing_authority": current_license.get("issuing_authority", "MTCIT / Naql"),
        "issue_date": current_license.get("issue_date", ""),
        "expiry_date": current_license.get("expiry_date", ""),
        "status": "EXPIRED",
        "notes": "test"
    })
    log(f"PUT /api/admin/app-license -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ E4 FAIL: Failed to update app license: {r1.text}")
        return False
    
    # Check application eligibility
    log("Step 3: Check application eligibility (should be false)")
    r2 = requests.get(f"{BASE_URL}/admin/compliance/application", headers=headers)
    log(f"GET /api/admin/compliance/application -> {r2.status_code}")
    if r2.status_code == 200:
        data = r2.json()
        log(f"Response: {json.dumps(data, indent=2)}")
        if data.get("eligible") == False:
            reasons = data.get("reasons", [])
            codes = [r.get("code") for r in reasons]
            if "APPLICATION_LICENSE_EXPIRED" in codes:
                log(f"✅ E4 PASS: APPLICATION_LICENSE_EXPIRED blocked correctly")
            else:
                log(f"❌ E4 FAIL: Expected APPLICATION_LICENSE_EXPIRED, got {codes}")
                return False
        else:
            log(f"❌ E4 FAIL: Expected eligible=false, got {data}")
            return False
    else:
        log(f"❌ E4 FAIL: {r2.status_code} {r2.text}")
        return False
    
    # Check driver also returns this reason (global gate)
    log("Step 4: Check driver eligibility (should also have APPLICATION_LICENSE_EXPIRED)")
    r3 = requests.get(f"{BASE_URL}/admin/compliance/check/driver/{driver_id}", headers=headers)
    log(f"GET /api/admin/compliance/check/driver/{driver_id} -> {r3.status_code}")
    if r3.status_code == 200:
        data = r3.json()
        if data.get("eligible") == False:
            codes = [r.get("code") for r in data.get("reasons", [])]
            if "APPLICATION_LICENSE_EXPIRED" in codes:
                log(f"✅ E4 PASS: Driver check also returns APPLICATION_LICENSE_EXPIRED (global gate)")
            else:
                log(f"❌ E4 FAIL: Expected APPLICATION_LICENSE_EXPIRED in driver check, got {codes}")
                return False
        else:
            log(f"❌ E4 FAIL: Expected driver eligible=false")
            return False
    
    # RESTORE to ACTIVE
    log("Step 5: RESTORE app_license status to ACTIVE")
    r4 = requests.put(f"{BASE_URL}/admin/app-license", headers=headers, json={
        "license_number": current_license.get("license_number", ""),
        "license_type": current_license.get("license_type", "trucks"),
        "issuing_authority": current_license.get("issuing_authority", "MTCIT / Naql"),
        "issue_date": current_license.get("issue_date", ""),
        "expiry_date": current_license.get("expiry_date", ""),
        "status": "ACTIVE",
        "notes": "restored"
    })
    log(f"PUT /api/admin/app-license -> {r4.status_code}")
    if r4.status_code != 200:
        log(f"❌ E4 FAIL: Failed to restore app license: {r4.text}")
        return False
    
    # Verify restored
    r5 = requests.get(f"{BASE_URL}/admin/compliance/application", headers=headers)
    if r5.status_code == 200:
        data = r5.json()
        if data.get("eligible") == True:
            log(f"✅ E4 PASS (restored): app_license ACTIVE, eligible=true")
            return True
        else:
            log(f"❌ E4 FAIL: Expected eligible=true after restore, got {data}")
            return False
    else:
        log(f"❌ E4 FAIL: {r5.status_code} {r5.text}")
        return False

def test_e5_multiple_reasons():
    log("\n=== [E5] MULTIPLE REASONS ===")
    headers = {"Authorization": f"Bearer {admin_token}"}
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    
    # Get current app license
    r0 = requests.get(f"{BASE_URL}/admin/app-license", headers=headers)
    current_license = r0.json()
    
    # Set app-license to SUSPENDED
    log("Step 1: Set app_license status to SUSPENDED")
    r1 = requests.put(f"{BASE_URL}/admin/app-license", headers=headers, json={
        "license_number": current_license.get("license_number", ""),
        "license_type": current_license.get("license_type", "trucks"),
        "issuing_authority": current_license.get("issuing_authority", "MTCIT / Naql"),
        "issue_date": current_license.get("issue_date", ""),
        "expiry_date": current_license.get("expiry_date", ""),
        "status": "SUSPENDED",
        "notes": "test"
    })
    log(f"PUT /api/admin/app-license -> {r1.status_code}")
    
    # Set driver training to IN_PROGRESS
    log("Step 2: Set driver_training_status to IN_PROGRESS")
    r2 = requests.put(f"{BASE_URL}/driver/regulatory", headers=driver_headers, json={
        "driver_training_status": "IN_PROGRESS"
    })
    log(f"PUT /api/driver/regulatory -> {r2.status_code}")
    
    # Check driver eligibility - should have BOTH reasons
    log("Step 3: Check driver eligibility (should have BOTH reasons)")
    r3 = requests.get(f"{BASE_URL}/admin/compliance/check/driver/{driver_id}", headers=headers)
    log(f"GET /api/admin/compliance/check/driver/{driver_id} -> {r3.status_code}")
    if r3.status_code == 200:
        data = r3.json()
        log(f"Response: {json.dumps(data, indent=2)}")
        if data.get("eligible") == False:
            codes = [r.get("code") for r in data.get("reasons", [])]
            has_app = "APPLICATION_LICENSE_SUSPENDED" in codes
            has_training = "DRIVER_APP_TRAINING_NOT_COMPLETED" in codes
            if has_app and has_training:
                log(f"✅ E5 PASS: Both APPLICATION_LICENSE_SUSPENDED and DRIVER_APP_TRAINING_NOT_COMPLETED present")
            else:
                log(f"❌ E5 FAIL: Expected both reasons, got {codes}")
                return False
        else:
            log(f"❌ E5 FAIL: Expected eligible=false, got {data}")
            return False
    else:
        log(f"❌ E5 FAIL: {r3.status_code} {r3.text}")
        return False
    
    # RESTORE both
    log("Step 4: RESTORE app_license to ACTIVE")
    r4 = requests.put(f"{BASE_URL}/admin/app-license", headers=headers, json={
        "license_number": current_license.get("license_number", ""),
        "license_type": current_license.get("license_type", "trucks"),
        "issuing_authority": current_license.get("issuing_authority", "MTCIT / Naql"),
        "issue_date": current_license.get("issue_date", ""),
        "expiry_date": current_license.get("expiry_date", ""),
        "status": "ACTIVE",
        "notes": "restored"
    })
    log(f"PUT /api/admin/app-license -> {r4.status_code}")
    
    log("Step 5: RESTORE driver_training_status to COMPLETED")
    r5 = requests.put(f"{BASE_URL}/driver/regulatory", headers=driver_headers, json={
        "driver_training_status": "COMPLETED"
    })
    log(f"PUT /api/driver/regulatory -> {r5.status_code}")
    
    # Verify restored
    r6 = requests.get(f"{BASE_URL}/admin/compliance/check/driver/{driver_id}", headers=headers)
    if r6.status_code == 200:
        data = r6.json()
        if data.get("eligible") == True:
            log(f"✅ E5 PASS (restored): eligible=true after both restored")
            return True
        else:
            log(f"❌ E5 FAIL: Expected eligible=true after restore, got {data}")
            return False
    else:
        log(f"❌ E5 FAIL: {r6.status_code} {r6.text}")
        return False

def test_e6_audit_logs():
    log("\n=== [E6] AUDIT LOGS ===")
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = requests.get(f"{BASE_URL}/admin/audit-logs", headers=headers)
    log(f"GET /api/admin/audit-logs -> {r.status_code}")
    if r.status_code == 200:
        logs = r.json()
        compliance_checked = [l for l in logs if l.get("action") == "compliance_status_checked"]
        eligibility_blocked = [l for l in logs if l.get("action") == "eligibility_blocked"]
        log(f"Found {len(compliance_checked)} compliance_status_checked entries")
        log(f"Found {len(eligibility_blocked)} eligibility_blocked entries")
        if len(compliance_checked) > 0:
            log(f"✅ E6 PASS: compliance_status_checked entries found")
            return True
        else:
            log(f"❌ E6 FAIL: No compliance_status_checked entries")
            return False
    else:
        log(f"❌ E6 FAIL: {r.status_code} {r.text}")
        return False

# ==================================================================================
# [F] INTEGRATION into real flow
# ==================================================================================
def test_f1_happy_path():
    global shipment_id, bid_id, trip_id
    log("\n=== [F1] HAPPY PATH - Eligible demo flow ===")
    
    # Customer creates shipment
    log("Step 1: Customer creates shipment")
    headers = {"Authorization": f"Bearer {customer_token}"}
    r1 = requests.post(f"{BASE_URL}/shipments", headers=headers, json={
        "title": "reg core",
        "description": "x",
        "weight": "100",
        "pickup_location": {
            "address": "مسقط",
            "lat": 23.58,
            "lng": 58.40
        },
        "delivery_location": {
            "address": "صحار",
            "lat": 24.34,
            "lng": 56.70
        },
        "pickup_date": "2026-08-01",
        "delivery_date": "2026-08-02",
        "status": "PUBLISHED"
    })
    log(f"POST /api/shipments -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ F1 FAIL: Failed to create shipment: {r1.text}")
        return False
    
    shipment_id = r1.json()["id"]
    log(f"Shipment created: id={shipment_id}")
    
    # Driver submits bid (eligible)
    log("Step 2: Driver submits bid (eligible)")
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    r2 = requests.post(f"{BASE_URL}/shipments/{shipment_id}/bids", headers=driver_headers, json={
        "price": 40
    })
    log(f"POST /api/shipments/{shipment_id}/bids -> {r2.status_code}")
    if r2.status_code != 200:
        log(f"❌ F1 FAIL: Driver bid failed: {r2.text}")
        return False
    
    bid_id = r2.json()["id"]
    log(f"✅ Bid submitted: id={bid_id}")
    
    # Customer accepts bid
    log("Step 3: Customer accepts bid")
    r3 = requests.post(f"{BASE_URL}/bids/{bid_id}/accept", headers=headers)
    log(f"POST /api/bids/{bid_id}/accept -> {r3.status_code}")
    if r3.status_code != 200:
        log(f"❌ F1 FAIL: Bid acceptance failed: {r3.text}")
        return False
    
    trip_data = r3.json()
    trip_id = trip_data.get("id") or trip_data.get("trip_id")
    log(f"✅ Trip created: id={trip_id}")
    
    # Customer pays
    log("Step 4: Customer pays")
    r4 = requests.post(f"{BASE_URL}/trips/{trip_id}/pay", headers=headers)
    log(f"POST /api/trips/{trip_id}/pay -> {r4.status_code}")
    if r4.status_code != 200:
        log(f"❌ F1 FAIL: Payment failed: {r4.text}")
        return False
    log(f"✅ Payment HELD")
    
    # Driver starts trip (DRIVER_EN_ROUTE)
    log("Step 5: Driver starts trip (DRIVER_EN_ROUTE)")
    r5 = requests.post(f"{BASE_URL}/trips/{trip_id}/status", headers=driver_headers, json={
        "status": "DRIVER_EN_ROUTE"
    })
    log(f"POST /api/trips/{trip_id}/status -> {r5.status_code}")
    if r5.status_code == 200:
        log(f"✅ F1 PASS: Trip start passed eligibility check")
        return True
    else:
        log(f"❌ F1 FAIL: Trip start failed: {r5.text}")
        return False

def test_f2_block_bidding():
    log("\n=== [F2] BLOCK BIDDING - Ineligible driver ===")
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    
    # Set driver training to IN_PROGRESS
    log("Step 1: Set driver_training_status to IN_PROGRESS")
    r1 = requests.put(f"{BASE_URL}/driver/regulatory", headers=driver_headers, json={
        "driver_training_status": "IN_PROGRESS"
    })
    log(f"PUT /api/driver/regulatory -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ F2 FAIL: Failed to update driver regulatory: {r1.text}")
        return False
    
    # Create another shipment
    log("Step 2: Customer creates another shipment")
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    r2 = requests.post(f"{BASE_URL}/shipments", headers=customer_headers, json={
        "title": "test block",
        "description": "x",
        "weight": "50",
        "pickup_location": {
            "address": "مسقط",
            "lat": 23.58,
            "lng": 58.40
        },
        "delivery_location": {
            "address": "صحار",
            "lat": 24.34,
            "lng": 56.70
        },
        "pickup_date": "2026-08-01",
        "delivery_date": "2026-08-02",
        "status": "PUBLISHED"
    })
    log(f"POST /api/shipments -> {r2.status_code}")
    if r2.status_code != 200:
        log(f"❌ F2 FAIL: Failed to create shipment: {r2.text}")
        return False
    
    shipment_id2 = r2.json()["id"]
    log(f"Shipment created: id={shipment_id2}")
    
    # Driver tries to bid (should be blocked)
    log("Step 3: Driver tries to bid (should be blocked)")
    r3 = requests.post(f"{BASE_URL}/shipments/{shipment_id2}/bids", headers=driver_headers, json={
        "price": 30
    })
    log(f"POST /api/shipments/{shipment_id2}/bids -> {r3.status_code}")
    if r3.status_code == 403:
        data = r3.json()
        log(f"Response: {json.dumps(data, indent=2)}")
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            code = detail.get("code")
            reasons = detail.get("reasons", [])
            codes = [r.get("code") for r in reasons]
            if code == "NOT_ELIGIBLE" and "DRIVER_APP_TRAINING_NOT_COMPLETED" in codes:
                log(f"✅ F2 PASS (blocked): 403 NOT_ELIGIBLE with DRIVER_APP_TRAINING_NOT_COMPLETED")
            else:
                log(f"❌ F2 FAIL: Expected NOT_ELIGIBLE with DRIVER_APP_TRAINING_NOT_COMPLETED, got {data}")
                return False
        else:
            log(f"❌ F2 FAIL: Expected detail object with code and reasons, got {data}")
            return False
    else:
        log(f"❌ F2 FAIL: Expected 403, got {r3.status_code} {r3.text}")
        return False
    
    # Check audit log for eligibility_blocked
    log("Step 4: Check audit log for eligibility_blocked")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    r4 = requests.get(f"{BASE_URL}/admin/audit-logs", headers=admin_headers)
    if r4.status_code == 200:
        logs = r4.json()
        blocked = [l for l in logs if l.get("action") == "eligibility_blocked"]
        if len(blocked) > 0:
            log(f"✅ F2 PASS: eligibility_blocked audit entry found")
        else:
            log(f"❌ F2 FAIL: No eligibility_blocked audit entry")
            return False
    
    # RESTORE training to COMPLETED
    log("Step 5: RESTORE driver_training_status to COMPLETED")
    r5 = requests.put(f"{BASE_URL}/driver/regulatory", headers=driver_headers, json={
        "driver_training_status": "COMPLETED"
    })
    log(f"PUT /api/driver/regulatory -> {r5.status_code}")
    if r5.status_code != 200:
        log(f"❌ F2 FAIL: Failed to restore driver regulatory: {r5.text}")
        return False
    
    # Try bid again (should succeed)
    log("Step 6: Driver tries bid again (should succeed)")
    r6 = requests.post(f"{BASE_URL}/shipments/{shipment_id2}/bids", headers=driver_headers, json={
        "price": 30
    })
    log(f"POST /api/shipments/{shipment_id2}/bids -> {r6.status_code}")
    if r6.status_code == 200:
        log(f"✅ F2 PASS (restored): Bid succeeded after COMPLETED")
        return True
    else:
        log(f"❌ F2 FAIL: Bid failed after restore: {r6.text}")
        return False

# ==================================================================================
# [T] TRANSPORT DOCUMENT lifecycle & relationship
# ==================================================================================
def test_t1_create_transport_document():
    global transport_doc_id
    log("\n=== [T1] CREATE TRANSPORT DOCUMENT ===")
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    
    log(f"Step 1: Create transport document for trip {trip_id}")
    r1 = requests.post(f"{BASE_URL}/trips/{trip_id}/transport-document", headers=driver_headers, json={
        "cargo": {
            "cargo_description": "steel",
            "cargo_weight": "100",
            "dangerous_goods": False
        },
        "freight": {
            "payment_payer": "SHIPPER"
        }
    })
    log(f"POST /api/trips/{trip_id}/transport-document -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ T1 FAIL: Failed to create transport document: {r1.text}")
        return False
    
    data = r1.json()
    log(f"Response: {json.dumps(data, indent=2)[:500]}...")
    transport_doc_id = data["id"]
    
    # Verify response
    checks = []
    checks.append(("status=DRAFT", data.get("status") == "DRAFT"))
    checks.append(("trip_id matches", data.get("trip_id") == trip_id))
    checks.append(("shipment_id set", data.get("shipment_id") is not None))
    checks.append(("shipper group present", data.get("shipper") is not None))
    checks.append(("carrier group present", data.get("carrier") is not None))
    checks.append(("delivery group present", data.get("delivery") is not None))
    checks.append(("integration_source=INTERNAL", data.get("integration", {}).get("integration_source") == "INTERNAL"))
    
    all_pass = all(c[1] for c in checks)
    for name, result in checks:
        log(f"  {name}: {'✅' if result else '❌'}")
    
    if not all_pass:
        log(f"❌ T1 FAIL: Some checks failed")
        return False
    
    # Check audit log
    log("Step 2: Check audit log for transport_document_created")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    r2 = requests.get(f"{BASE_URL}/admin/audit-logs", headers=admin_headers)
    if r2.status_code == 200:
        logs = r2.json()
        created = [l for l in logs if l.get("action") == "transport_document_created" and l.get("entity_id") == transport_doc_id]
        if len(created) > 0:
            log(f"✅ T1 PASS: transport_document_created audit entry found")
            return True
        else:
            log(f"❌ T1 FAIL: No transport_document_created audit entry")
            return False
    else:
        log(f"❌ T1 FAIL: Failed to get audit logs: {r2.text}")
        return False

def test_t2_duplicate_transport_document():
    log("\n=== [T2] DUPLICATE TRANSPORT DOCUMENT ===")
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    
    r = requests.post(f"{BASE_URL}/trips/{trip_id}/transport-document", headers=driver_headers, json={
        "cargo": {
            "cargo_description": "test",
            "cargo_weight": "50"
        }
    })
    log(f"POST /api/trips/{trip_id}/transport-document -> {r.status_code}")
    if r.status_code == 409:
        data = r.json()
        if data.get("detail") == "TRANSPORT_DOCUMENT_EXISTS":
            log(f"✅ T2 PASS: 409 TRANSPORT_DOCUMENT_EXISTS")
            return True
        else:
            log(f"❌ T2 FAIL: Expected TRANSPORT_DOCUMENT_EXISTS, got {data}")
            return False
    else:
        log(f"❌ T2 FAIL: Expected 409, got {r.status_code} {r.text}")
        return False

def test_t3_get_transport_document():
    log("\n=== [T3] GET TRANSPORT DOCUMENT ===")
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    
    # GET via trip
    log("Step 1: GET /api/trips/{tid}/transport-document")
    r1 = requests.get(f"{BASE_URL}/trips/{trip_id}/transport-document", headers=driver_headers)
    log(f"GET /api/trips/{trip_id}/transport-document -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ T3 FAIL: {r1.status_code} {r1.text}")
        return False
    
    # GET via doc id
    log("Step 2: GET /api/transport-documents/{doc_id}")
    r2 = requests.get(f"{BASE_URL}/transport-documents/{transport_doc_id}", headers=driver_headers)
    log(f"GET /api/transport-documents/{transport_doc_id} -> {r2.status_code}")
    if r2.status_code == 200:
        log(f"✅ T3 PASS: Both GET methods work")
        return True
    else:
        log(f"❌ T3 FAIL: {r2.status_code} {r2.text}")
        return False

def test_t4_update_transport_document():
    log("\n=== [T4] UPDATE TRANSPORT DOCUMENT ===")
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    
    log("Step 1: PUT /api/transport-documents/{doc_id}")
    r1 = requests.put(f"{BASE_URL}/transport-documents/{transport_doc_id}", headers=driver_headers, json={
        "carrier": {
            "carrier_name": "Gulf Transport"
        },
        "cargo": {
            "quantity": "5"
        }
    })
    log(f"PUT /api/transport-documents/{transport_doc_id} -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ T4 FAIL: Update failed: {r1.text}")
        return False
    
    data = r1.json()
    
    # Verify partial merge
    carrier_name = data.get("carrier", {}).get("carrier_name")
    cargo_desc = data.get("cargo", {}).get("cargo_description")
    cargo_qty = data.get("cargo", {}).get("quantity")
    
    checks = []
    checks.append(("carrier_name updated to Gulf Transport", carrier_name == "Gulf Transport"))
    checks.append(("cargo_description still steel", cargo_desc == "steel"))
    checks.append(("cargo quantity updated to 5", cargo_qty == "5"))
    checks.append(("history has updated entry", len(data.get("history", [])) > 1))
    
    all_pass = all(c[1] for c in checks)
    for name, result in checks:
        log(f"  {name}: {'✅' if result else '❌'}")
    
    if not all_pass:
        log(f"❌ T4 FAIL: Some checks failed")
        return False
    
    # Check audit log
    log("Step 2: Check audit log for transport_document_updated")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    r2 = requests.get(f"{BASE_URL}/admin/audit-logs", headers=admin_headers)
    if r2.status_code == 200:
        logs = r2.json()
        updated = [l for l in logs if l.get("action") == "transport_document_updated" and l.get("entity_id") == transport_doc_id]
        if len(updated) > 0:
            log(f"✅ T4 PASS: transport_document_updated audit entry found")
            return True
        else:
            log(f"❌ T4 FAIL: No transport_document_updated audit entry")
            return False
    else:
        log(f"❌ T4 FAIL: Failed to get audit logs: {r2.text}")
        return False

def test_t5_lifecycle():
    log("\n=== [T5] TRANSPORT DOCUMENT LIFECYCLE ===")
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    
    # DRAFT -> READY
    log("Step 1: DRAFT -> READY")
    r1 = requests.post(f"{BASE_URL}/transport-documents/{transport_doc_id}/status", headers=driver_headers, json={
        "status": "READY"
    })
    log(f"POST /api/transport-documents/{transport_doc_id}/status -> {r1.status_code}")
    if r1.status_code != 200 or r1.json().get("status") != "READY":
        log(f"❌ T5 FAIL: READY transition failed: {r1.text}")
        return False
    log(f"✅ Status: READY")
    
    # READY -> ISSUED
    log("Step 2: READY -> ISSUED")
    r2 = requests.post(f"{BASE_URL}/transport-documents/{transport_doc_id}/status", headers=driver_headers, json={
        "status": "ISSUED"
    })
    log(f"POST /api/transport-documents/{transport_doc_id}/status -> {r2.status_code}")
    if r2.status_code != 200 or r2.json().get("status") != "ISSUED":
        log(f"❌ T5 FAIL: ISSUED transition failed: {r2.text}")
        return False
    log(f"✅ Status: ISSUED")
    
    # Check audit for transport_document_issued
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    r_audit = requests.get(f"{BASE_URL}/admin/audit-logs", headers=admin_headers)
    if r_audit.status_code == 200:
        logs = r_audit.json()
        issued = [l for l in logs if l.get("action") == "transport_document_issued" and l.get("entity_id") == transport_doc_id]
        if len(issued) > 0:
            log(f"✅ transport_document_issued audit entry found")
        else:
            log(f"⚠️  No transport_document_issued audit entry")
    
    # ISSUED -> DELIVERED (invalid, should be IN_TRANSIT first)
    log("Step 3: ISSUED -> DELIVERED (invalid)")
    r3 = requests.post(f"{BASE_URL}/transport-documents/{transport_doc_id}/status", headers=driver_headers, json={
        "status": "DELIVERED"
    })
    log(f"POST /api/transport-documents/{transport_doc_id}/status -> {r3.status_code}")
    if r3.status_code == 400:
        data = r3.json()
        if data.get("detail") == "INVALID_TRANSPORT_DOCUMENT_TRANSITION":
            log(f"✅ 400 INVALID_TRANSPORT_DOCUMENT_TRANSITION")
        else:
            log(f"❌ T5 FAIL: Expected INVALID_TRANSPORT_DOCUMENT_TRANSITION, got {data}")
            return False
    else:
        log(f"❌ T5 FAIL: Expected 400, got {r3.status_code}")
        return False
    
    # ISSUED -> IN_TRANSIT
    log("Step 4: ISSUED -> IN_TRANSIT")
    r4 = requests.post(f"{BASE_URL}/transport-documents/{transport_doc_id}/status", headers=driver_headers, json={
        "status": "IN_TRANSIT"
    })
    log(f"POST /api/transport-documents/{transport_doc_id}/status -> {r4.status_code}")
    if r4.status_code != 200 or r4.json().get("status") != "IN_TRANSIT":
        log(f"❌ T5 FAIL: IN_TRANSIT transition failed: {r4.text}")
        return False
    log(f"✅ Status: IN_TRANSIT")
    
    # IN_TRANSIT -> DELIVERED
    log("Step 5: IN_TRANSIT -> DELIVERED")
    r5 = requests.post(f"{BASE_URL}/transport-documents/{transport_doc_id}/status", headers=driver_headers, json={
        "status": "DELIVERED"
    })
    log(f"POST /api/transport-documents/{transport_doc_id}/status -> {r5.status_code}")
    if r5.status_code != 200 or r5.json().get("status") != "DELIVERED":
        log(f"❌ T5 FAIL: DELIVERED transition failed: {r5.text}")
        return False
    log(f"✅ Status: DELIVERED (terminal)")
    
    # Try to update fields (should be locked)
    log("Step 6: Try PUT fields (should be locked)")
    r6 = requests.put(f"{BASE_URL}/transport-documents/{transport_doc_id}", headers=driver_headers, json={
        "cargo": {
            "cargo_description": "test"
        }
    })
    log(f"PUT /api/transport-documents/{transport_doc_id} -> {r6.status_code}")
    if r6.status_code == 400:
        data = r6.json()
        if data.get("detail") == "TRANSPORT_DOCUMENT_LOCKED":
            log(f"✅ 400 TRANSPORT_DOCUMENT_LOCKED")
        else:
            log(f"❌ T5 FAIL: Expected TRANSPORT_DOCUMENT_LOCKED, got {data}")
            return False
    else:
        log(f"❌ T5 FAIL: Expected 400, got {r6.status_code}")
        return False
    
    # Try to cancel (should fail, terminal)
    log("Step 7: Try CANCELLED (should fail, terminal)")
    r7 = requests.post(f"{BASE_URL}/transport-documents/{transport_doc_id}/status", headers=driver_headers, json={
        "status": "CANCELLED"
    })
    log(f"POST /api/transport-documents/{transport_doc_id}/status -> {r7.status_code}")
    if r7.status_code == 400:
        log(f"✅ 400 (terminal state, cannot transition)")
        return True
    else:
        log(f"❌ T5 FAIL: Expected 400, got {r7.status_code}")
        return False

def test_t6_permissions():
    log("\n=== [T6] TRANSPORT DOCUMENT PERMISSIONS ===")
    
    # Customer (shipper) can read
    log("Step 1: Customer (shipper) GET transport document")
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    r1 = requests.get(f"{BASE_URL}/transport-documents/{transport_doc_id}", headers=customer_headers)
    log(f"GET /api/transport-documents/{transport_doc_id} -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ T6 FAIL: Customer should be able to read: {r1.text}")
        return False
    log(f"✅ Customer can read")
    
    # Unrelated driver cannot read
    log("Step 2: Unrelated driver GET transport document (should be 403)")
    # Login as another driver
    result = otp_login("+96890000004", "driver")  # pending driver
    if result:
        other_driver_token, _ = result
        other_driver_headers = {"Authorization": f"Bearer {other_driver_token}"}
        r2 = requests.get(f"{BASE_URL}/transport-documents/{transport_doc_id}", headers=other_driver_headers)
        log(f"GET /api/transport-documents/{transport_doc_id} -> {r2.status_code}")
        if r2.status_code == 403:
            log(f"✅ Unrelated driver blocked (403)")
        else:
            log(f"❌ T6 FAIL: Expected 403, got {r2.status_code}")
            return False
    else:
        log(f"⚠️  Could not login other driver, skipping unrelated driver test")
    
    # Admin can list all
    log("Step 3: Admin GET /api/admin/transport-documents")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    r3 = requests.get(f"{BASE_URL}/admin/transport-documents", headers=admin_headers)
    log(f"GET /api/admin/transport-documents -> {r3.status_code}")
    if r3.status_code == 200:
        docs = r3.json()
        doc_ids = [d.get("id") for d in docs]
        if transport_doc_id in doc_ids:
            log(f"✅ T6 PASS: Admin can list all, includes our doc")
            return True
        else:
            log(f"❌ T6 FAIL: Admin list doesn't include our doc")
            return False
    else:
        log(f"❌ T6 FAIL: Admin list failed: {r3.text}")
        return False

# ==================================================================================
# [R] REGRESSION light
# ==================================================================================
def test_r_regression():
    log("\n=== [R] REGRESSION LIGHT ===")
    
    # Admin login
    log("Step 1: Admin login")
    r1 = requests.post(f"{BASE_URL}/auth/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    log(f"POST /api/auth/admin/login -> {r1.status_code}")
    if r1.status_code != 200:
        log(f"❌ R FAIL: Admin login failed")
        return False
    
    # Driver OTP
    log("Step 2: Driver OTP login")
    result = otp_login(DRIVER_PHONE, "driver")
    if not result:
        log(f"❌ R FAIL: Driver OTP failed")
        return False
    
    # Provider OTP
    log("Step 3: Provider OTP login")
    result = otp_login(PROVIDER_PHONE, "provider")
    if not result:
        log(f"❌ R FAIL: Provider OTP failed")
        return False
    
    # Shipment creation
    log("Step 4: Shipment creation")
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    r4 = requests.post(f"{BASE_URL}/shipments", headers=customer_headers, json={
        "title": "regression test",
        "description": "x",
        "weight": "50",
        "pickup_location": {"address": "مسقط", "lat": 23.58, "lng": 58.40},
        "delivery_location": {"address": "صحار", "lat": 24.34, "lng": 56.70},
        "pickup_date": "2026-08-01",
        "delivery_date": "2026-08-02",
        "status": "PUBLISHED"
    })
    log(f"POST /api/shipments -> {r4.status_code}")
    if r4.status_code != 200:
        log(f"❌ R FAIL: Shipment creation failed")
        return False
    
    # Marketplace access (driver with COMPLETED training)
    log("Step 5: GET /api/marketplace/shipments (driver)")
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    r5 = requests.get(f"{BASE_URL}/marketplace/shipments", headers=driver_headers)
    log(f"GET /api/marketplace/shipments -> {r5.status_code}")
    if r5.status_code == 200:
        log(f"✅ R PASS: All regression tests passed")
        return True
    else:
        log(f"❌ R FAIL: Marketplace access failed: {r5.text}")
        return False

# ==================================================================================
# MAIN
# ==================================================================================
def main():
    log("=" * 80)
    log("CARGO REGULATORY CORE BACKEND TEST")
    log("=" * 80)
    
    # Setup
    if not admin_login():
        log("FATAL: Admin login failed")
        return
    
    global customer_token, driver_token, provider_token
    result = otp_login(CUSTOMER_PHONE, "customer")
    if result:
        customer_token, _ = result
    else:
        log("FATAL: Customer login failed")
        return
    
    result = otp_login(DRIVER_PHONE, "driver")
    if result:
        driver_token, driver_id_temp = result
        global driver_id
        driver_id = driver_id_temp
    else:
        log("FATAL: Driver login failed")
        return
    
    result = otp_login(PROVIDER_PHONE, "provider")
    if result:
        provider_token, provider_id_temp = result
        global provider_id
        provider_id = provider_id_temp
    else:
        log("FATAL: Provider login failed")
        return
    
    # Also get driver/provider IDs via admin API for compliance checks
    get_driver_id()
    get_provider_id()
    
    # Run tests
    results = {}
    
    log("\n" + "=" * 80)
    log("[E] ELIGIBILITY SERVICE")
    log("=" * 80)
    results["E1"] = test_e1_application_eligibility()
    results["E2"] = test_e2_driver_eligibility()
    results["E3"] = test_e3_provider_eligibility()
    results["E4a"] = test_e4_block_driver_training()
    results["E4b"] = test_e4_block_vehicle_operating_card()
    results["E4c"] = test_e4_block_application_license()
    results["E5"] = test_e5_multiple_reasons()
    results["E6"] = test_e6_audit_logs()
    
    log("\n" + "=" * 80)
    log("[F] INTEGRATION INTO REAL FLOW")
    log("=" * 80)
    results["F1"] = test_f1_happy_path()
    results["F2"] = test_f2_block_bidding()
    
    log("\n" + "=" * 80)
    log("[T] TRANSPORT DOCUMENT")
    log("=" * 80)
    results["T1"] = test_t1_create_transport_document()
    results["T2"] = test_t2_duplicate_transport_document()
    results["T3"] = test_t3_get_transport_document()
    results["T4"] = test_t4_update_transport_document()
    results["T5"] = test_t5_lifecycle()
    results["T6"] = test_t6_permissions()
    
    log("\n" + "=" * 80)
    log("[R] REGRESSION")
    log("=" * 80)
    results["R"] = test_r_regression()
    
    # Summary
    log("\n" + "=" * 80)
    log("SUMMARY")
    log("=" * 80)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    log(f"PASSED: {passed}/{total}")
    log("")
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        log(f"  {test}: {status}")
    
    log("\n" + "=" * 80)
    log("TEST COMPLETE")
    log("=" * 80)

if __name__ == "__main__":
    main()
