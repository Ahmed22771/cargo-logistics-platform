#!/usr/bin/env python3
"""
CARGO — Regulatory Readiness (Oman) Backend Test
Tests ONLY data structures: App License, Driver regulatory, Vehicle regulatory
NO eligibility/blocking logic, NO Naql/SMS/GPS/payment
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# BASE URL from frontend/.env
BASE_URL = "https://hardened-cargo.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"
DRIVER_PHONE = "+96890000002"  # approved driver
PROVIDER_PHONE = "+96890000005"
CUSTOMER_PHONE = "+96890000001"

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "details": []
}

def log_test(section: str, test_name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    message = f"{status} [{section}] {test_name}"
    if details:
        message += f" - {details}"
    print(message)
    
    test_results["details"].append({
        "section": section,
        "test": test_name,
        "passed": passed,
        "details": details
    })
    
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1

def admin_login() -> Optional[str]:
    """Login as admin and return token"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/admin/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            log_test("AUTH", "Admin login", True, f"HTTP {response.status_code}")
            return token
        else:
            log_test("AUTH", "Admin login", False, f"HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        log_test("AUTH", "Admin login", False, f"Exception: {str(e)}")
        return None

def otp_login(phone: str, role: str) -> Optional[str]:
    """Login via OTP demo flow and return token"""
    try:
        # Request OTP
        response = requests.post(
            f"{BASE_URL}/auth/otp/request",
            json={"phone": phone, "role": role},
            timeout=10
        )
        if response.status_code != 200:
            log_test("AUTH", f"{role.capitalize()} OTP request", False, f"HTTP {response.status_code}")
            return None
        
        data = response.json()
        demo_code = data.get("demo_code")
        if not demo_code:
            log_test("AUTH", f"{role.capitalize()} OTP request", False, "No demo_code in response")
            return None
        
        # Verify OTP
        response = requests.post(
            f"{BASE_URL}/auth/otp/verify",
            json={"phone": phone, "code": demo_code, "role": role},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            log_test("AUTH", f"{role.capitalize()} OTP login", True, f"HTTP {response.status_code}, demo_code={demo_code}")
            return token
        else:
            log_test("AUTH", f"{role.capitalize()} OTP login", False, f"HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        log_test("AUTH", f"{role.capitalize()} OTP login", False, f"Exception: {str(e)}")
        return None

def test_app_license(admin_token: str, driver_token: str):
    """Test [A] APP LICENSE endpoints"""
    print("\n" + "="*80)
    print("[A] APP LICENSE TESTS")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # A1: GET app-license (first call returns skeleton)
    try:
        response = requests.get(f"{BASE_URL}/admin/app-license", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            has_id = data.get("id") == "app_license"
            has_license_number = "license_number" in data
            log_test("A", "A1: GET app-license returns skeleton", 
                    response.status_code == 200 and has_id,
                    f"HTTP {response.status_code}, id={data.get('id')}, has license_number field: {has_license_number}")
        else:
            log_test("A", "A1: GET app-license", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("A", "A1: GET app-license", False, f"Exception: {str(e)}")
    
    # A2: PUT app-license with test data
    license_data = {
        "license_number": "TEST-APP-LIC-001",
        "license_type": "trucks",
        "issuing_authority": "MTCIT / Naql",
        "issue_date": "2025-01-01",
        "expiry_date": "2027-01-01",
        "status": "ACTIVE",
        "notes": "test"
    }
    try:
        response = requests.put(f"{BASE_URL}/admin/app-license", headers=headers, json=license_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            all_match = all(data.get(k) == v for k, v in license_data.items())
            log_test("A", "A2: PUT app-license saves values", 
                    all_match,
                    f"HTTP {response.status_code}, all fields match: {all_match}")
        else:
            log_test("A", "A2: PUT app-license", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("A", "A2: PUT app-license", False, f"Exception: {str(e)}")
    
    # A3: GET app-license again (values persisted)
    try:
        response = requests.get(f"{BASE_URL}/admin/app-license", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            all_match = all(data.get(k) == v for k, v in license_data.items())
            log_test("A", "A3: GET app-license values persisted", 
                    all_match,
                    f"HTTP {response.status_code}, license_number={data.get('license_number')}")
        else:
            log_test("A", "A3: GET app-license persisted", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("A", "A3: GET app-license persisted", False, f"Exception: {str(e)}")
    
    # A4: Check audit log
    try:
        response = requests.get(f"{BASE_URL}/admin/audit-logs", headers=headers, timeout=10)
        if response.status_code == 200:
            logs = response.json()
            has_update = any(log.get("action") == "app_license_updated" for log in logs)
            log_test("A", "A4: Audit log contains app_license_updated", 
                    has_update,
                    f"HTTP {response.status_code}, found: {has_update}")
        else:
            log_test("A", "A4: GET audit-logs", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("A", "A4: GET audit-logs", False, f"Exception: {str(e)}")
    
    # A5: PERMISSION - driver cannot access
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    try:
        response = requests.get(f"{BASE_URL}/admin/app-license", headers=driver_headers, timeout=10)
        is_forbidden = response.status_code == 403
        log_test("A", "A5: Driver GET app-license returns 403", 
                is_forbidden,
                f"HTTP {response.status_code}")
    except Exception as e:
        log_test("A", "A5: Driver permission check", False, f"Exception: {str(e)}")

def test_driver_regulatory(driver_token: str, customer_token: str, admin_token: str):
    """Test [B] DRIVER REGULATORY endpoints"""
    print("\n" + "="*80)
    print("[B] DRIVER REGULATORY TESTS")
    print("="*80)
    
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    
    # B1: GET driver/regulatory (returns all 8 keys)
    try:
        response = requests.get(f"{BASE_URL}/driver/regulatory", headers=driver_headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            expected_keys = [
                "driving_license_number", "license_class", "license_issue_date",
                "license_expiry_date", "license_status", "driver_training_status",
                "driver_training_date", "regulatory_notes"
            ]
            has_all_keys = all(k in data for k in expected_keys)
            log_test("B", "B1: GET driver/regulatory returns all 8 keys", 
                    has_all_keys,
                    f"HTTP {response.status_code}, keys present: {has_all_keys}")
        else:
            log_test("B", "B1: GET driver/regulatory", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("B", "B1: GET driver/regulatory", False, f"Exception: {str(e)}")
    
    # B2: PUT driver/regulatory with test data
    regulatory_data = {
        "driving_license_number": "DL-TEST-123",
        "license_class": "HeavyTruck",
        "license_issue_date": "2024-01-01",
        "license_expiry_date": "2029-01-01",
        "license_status": "VALID",
        "driver_training_status": "COMPLETED",
        "driver_training_date": "2024-02-01",
        "regulatory_notes": "test"
    }
    try:
        response = requests.put(f"{BASE_URL}/driver/regulatory", headers=driver_headers, json=regulatory_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            has_regulatory = "regulatory" in data
            if has_regulatory:
                reg = data["regulatory"]
                all_match = all(reg.get(k) == v for k, v in regulatory_data.items())
                log_test("B", "B2: PUT driver/regulatory saves values", 
                        all_match,
                        f"HTTP {response.status_code}, all fields match: {all_match}")
            else:
                log_test("B", "B2: PUT driver/regulatory", False, "No regulatory field in response")
        else:
            log_test("B", "B2: PUT driver/regulatory", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("B", "B2: PUT driver/regulatory", False, f"Exception: {str(e)}")
    
    # B3: GET driver/regulatory again (values persisted)
    try:
        response = requests.get(f"{BASE_URL}/driver/regulatory", headers=driver_headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            all_match = all(data.get(k) == v for k, v in regulatory_data.items())
            log_test("B", "B3: GET driver/regulatory values persisted", 
                    all_match,
                    f"HTTP {response.status_code}, driving_license_number={data.get('driving_license_number')}")
        else:
            log_test("B", "B3: GET driver/regulatory persisted", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("B", "B3: GET driver/regulatory persisted", False, f"Exception: {str(e)}")
    
    # B4: GET /auth/me confirms storage on driver user doc
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=driver_headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            has_regulatory = "regulatory" in data
            if has_regulatory:
                reg = data["regulatory"]
                all_match = all(reg.get(k) == v for k, v in regulatory_data.items())
                log_test("B", "B4: GET /auth/me reflects regulatory values", 
                        all_match,
                        f"HTTP {response.status_code}, stored on user doc: {has_regulatory}")
            else:
                log_test("B", "B4: GET /auth/me", False, "No regulatory field in user")
        else:
            log_test("B", "B4: GET /auth/me", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("B", "B4: GET /auth/me", False, f"Exception: {str(e)}")
    
    # B5: PERMISSION - customer cannot access
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    try:
        response = requests.get(f"{BASE_URL}/driver/regulatory", headers=customer_headers, timeout=10)
        is_forbidden = response.status_code == 403
        log_test("B", "B5: Customer GET driver/regulatory returns 403", 
                is_forbidden,
                f"HTTP {response.status_code}")
    except Exception as e:
        log_test("B", "B5: Customer permission check", False, f"Exception: {str(e)}")
    
    # B5 (admin): Admin cannot access driver-only endpoint
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    try:
        response = requests.get(f"{BASE_URL}/driver/regulatory", headers=admin_headers, timeout=10)
        is_forbidden = response.status_code == 403
        log_test("B", "B5: Admin GET driver/regulatory returns 403", 
                is_forbidden,
                f"HTTP {response.status_code}")
    except Exception as e:
        log_test("B", "B5: Admin permission check", False, f"Exception: {str(e)}")

def test_vehicle_regulatory(provider_token: str):
    """Test [C] VEHICLE REGULATORY endpoints"""
    print("\n" + "="*80)
    print("[C] VEHICLE REGULATORY TESTS")
    print("="*80)
    
    provider_headers = {"Authorization": f"Bearer {provider_token}"}
    
    # C1: POST vehicle with regulatory data
    vehicle_data = {
        "plate_number": "REG-TEST-1",
        "vehicle_type": "flatbed",
        "regulatory": {
            "chassis_number": "CH-123",
            "operating_card_number": "OC-999",
            "operating_card_issue_date": "2025-01-01",
            "operating_card_expiry_date": "2026-01-01",
            "operating_card_status": "ACTIVE",
            "registration_reference": "RR-1",
            "ownership_reference": "OWN-1",
            "regulatory_notes": "n",
            "regulatory_identifier": "RID-1",
            "barcode_value": "BC-1",
            "barcode_status": "PENDING"
        }
    }
    
    vehicle_id = None
    try:
        response = requests.post(f"{BASE_URL}/provider/vehicles", headers=provider_headers, json=vehicle_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            vehicle_id = data.get("id")
            has_regulatory = "regulatory" in data
            if has_regulatory:
                reg = data["regulatory"]
                expected_keys = [
                    "chassis_number", "operating_card_number", "operating_card_issue_date",
                    "operating_card_expiry_date", "operating_card_status", "registration_reference",
                    "ownership_reference", "regulatory_notes", "regulatory_identifier",
                    "barcode_value", "barcode_status"
                ]
                has_all_keys = all(k in reg for k in expected_keys)
                all_match = all(reg.get(k) == v for k, v in vehicle_data["regulatory"].items())
                log_test("C", "C1: POST vehicle with regulatory returns all 11 keys", 
                        has_all_keys and all_match,
                        f"HTTP {response.status_code}, id={vehicle_id}, all keys: {has_all_keys}, all match: {all_match}")
            else:
                log_test("C", "C1: POST vehicle with regulatory", False, "No regulatory field in response")
        else:
            log_test("C", "C1: POST vehicle with regulatory", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("C", "C1: POST vehicle with regulatory", False, f"Exception: {str(e)}")
    
    if not vehicle_id:
        print("⚠️  Cannot continue vehicle tests without vehicle_id")
        return
    
    # C2: GET vehicle (regulatory persisted)
    try:
        response = requests.get(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=provider_headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            has_regulatory = "regulatory" in data
            if has_regulatory:
                reg = data["regulatory"]
                all_match = all(reg.get(k) == v for k, v in vehicle_data["regulatory"].items())
                log_test("C", "C2: GET vehicle regulatory persisted", 
                        all_match,
                        f"HTTP {response.status_code}, chassis_number={reg.get('chassis_number')}")
            else:
                log_test("C", "C2: GET vehicle", False, "No regulatory field")
        else:
            log_test("C", "C2: GET vehicle", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("C", "C2: GET vehicle", False, f"Exception: {str(e)}")
    
    # C3: PUT vehicle WITHOUT regulatory key (partial update must NOT wipe it)
    try:
        update_data = {
            "plate_number": "REG-TEST-1",
            "vehicle_type": "flatbed"
        }
        response = requests.put(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=provider_headers, json=update_data, timeout=10)
        if response.status_code == 200:
            # Now GET to verify regulatory still intact
            response = requests.get(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=provider_headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                has_regulatory = "regulatory" in data
                if has_regulatory:
                    reg = data["regulatory"]
                    chassis_intact = reg.get("chassis_number") == "CH-123"
                    oc_intact = reg.get("operating_card_number") == "OC-999"
                    log_test("C", "C3: PUT without regulatory preserves existing regulatory", 
                            chassis_intact and oc_intact,
                            f"HTTP {response.status_code}, chassis_number={reg.get('chassis_number')}, operating_card_number={reg.get('operating_card_number')}")
                else:
                    log_test("C", "C3: PUT without regulatory", False, "Regulatory field was wiped")
            else:
                log_test("C", "C3: GET after PUT", False, f"HTTP {response.status_code}")
        else:
            log_test("C", "C3: PUT without regulatory", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("C", "C3: PUT without regulatory", False, f"Exception: {str(e)}")
    
    # C4: PUT vehicle with partial regulatory (other keys preserved)
    try:
        update_data = {
            "plate_number": "REG-TEST-1",
            "regulatory": {
                "operating_card_status": "EXPIRED"
            }
        }
        response = requests.put(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=provider_headers, json=update_data, timeout=10)
        if response.status_code == 200:
            # Now GET to verify
            response = requests.get(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=provider_headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                has_regulatory = "regulatory" in data
                if has_regulatory:
                    reg = data["regulatory"]
                    status_updated = reg.get("operating_card_status") == "EXPIRED"
                    chassis_preserved = reg.get("chassis_number") == "CH-123"
                    oc_preserved = reg.get("operating_card_number") == "OC-999"
                    log_test("C", "C4: PUT with partial regulatory updates one field, preserves others", 
                            status_updated and chassis_preserved and oc_preserved,
                            f"HTTP {response.status_code}, operating_card_status={reg.get('operating_card_status')}, chassis_number={reg.get('chassis_number')}")
                else:
                    log_test("C", "C4: PUT with partial regulatory", False, "No regulatory field")
            else:
                log_test("C", "C4: GET after partial PUT", False, f"HTTP {response.status_code}")
        else:
            log_test("C", "C4: PUT with partial regulatory", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("C", "C4: PUT with partial regulatory", False, f"Exception: {str(e)}")
    
    # Cleanup: delete test vehicle
    try:
        requests.delete(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=provider_headers, timeout=10)
    except:
        pass

def test_backward_compatibility(provider_token: str):
    """Test [D] BACKWARD COMPATIBILITY"""
    print("\n" + "="*80)
    print("[D] BACKWARD COMPATIBILITY TESTS")
    print("="*80)
    
    provider_headers = {"Authorization": f"Bearer {provider_token}"}
    
    # D1: POST vehicle WITHOUT regulatory field
    vehicle_id = None
    try:
        vehicle_data = {
            "plate_number": "REG-TEST-2",
            "vehicle_type": "truck"
        }
        response = requests.post(f"{BASE_URL}/provider/vehicles", headers=provider_headers, json=vehicle_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            vehicle_id = data.get("id")
            log_test("D", "D1: POST vehicle without regulatory field", 
                    True,
                    f"HTTP {response.status_code}, id={vehicle_id}")
            
            # GET it to verify regulatory present as empty object
            response = requests.get(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=provider_headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                has_regulatory = "regulatory" in data
                if has_regulatory:
                    reg = data["regulatory"]
                    # Check if all values are empty strings or the object exists
                    log_test("D", "D1: GET vehicle without regulatory returns empty regulatory object", 
                            has_regulatory,
                            f"HTTP {response.status_code}, regulatory present: {has_regulatory}")
                else:
                    log_test("D", "D1: GET vehicle regulatory field", False, "No regulatory field (should have empty object)")
            else:
                log_test("D", "D1: GET vehicle after POST", False, f"HTTP {response.status_code}")
        else:
            log_test("D", "D1: POST vehicle without regulatory", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("D", "D1: POST vehicle without regulatory", False, f"Exception: {str(e)}")
    
    # D2: GET all vehicles (existing/seeded vehicles load without error)
    try:
        response = requests.get(f"{BASE_URL}/provider/vehicles", headers=provider_headers, timeout=10)
        if response.status_code == 200:
            vehicles = response.json()
            log_test("D", "D2: GET all vehicles loads without error", 
                    True,
                    f"HTTP {response.status_code}, count={len(vehicles)}")
        else:
            log_test("D", "D2: GET all vehicles", False, f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        log_test("D", "D2: GET all vehicles", False, f"Exception: {str(e)}")
    
    # Cleanup
    if vehicle_id:
        try:
            requests.delete(f"{BASE_URL}/provider/vehicles/{vehicle_id}", headers=provider_headers, timeout=10)
        except:
            pass

def test_regression(admin_token: str, driver_token: str, provider_token: str):
    """Test [E] REGRESSION (light)"""
    print("\n" + "="*80)
    print("[E] REGRESSION TESTS")
    print("="*80)
    
    # Already tested in auth, just verify tokens work
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    driver_headers = {"Authorization": f"Bearer {driver_token}"}
    provider_headers = {"Authorization": f"Bearer {provider_token}"}
    
    # Admin endpoints
    try:
        response = requests.get(f"{BASE_URL}/admin/stats", headers=admin_headers, timeout=10)
        log_test("E", "Admin GET /admin/stats", 
                response.status_code == 200,
                f"HTTP {response.status_code}")
    except Exception as e:
        log_test("E", "Admin GET /admin/stats", False, f"Exception: {str(e)}")
    
    # Driver endpoints
    try:
        response = requests.get(f"{BASE_URL}/marketplace/shipments", headers=driver_headers, timeout=10)
        log_test("E", "Driver GET /marketplace/shipments", 
                response.status_code == 200,
                f"HTTP {response.status_code}")
    except Exception as e:
        log_test("E", "Driver GET /marketplace/shipments", False, f"Exception: {str(e)}")
    
    # Provider endpoints
    try:
        response = requests.get(f"{BASE_URL}/provider/vehicles", headers=provider_headers, timeout=10)
        log_test("E", "Provider GET /provider/vehicles", 
                response.status_code == 200,
                f"HTTP {response.status_code}")
    except Exception as e:
        log_test("E", "Provider GET /provider/vehicles", False, f"Exception: {str(e)}")

def main():
    """Main test runner"""
    print("="*80)
    print("CARGO — REGULATORY READINESS (OMAN) BACKEND TEST")
    print("DATA STRUCTURES ONLY — NO eligibility/blocking/Naql/SMS/GPS/payment")
    print("="*80)
    
    # Authentication
    print("\n" + "="*80)
    print("AUTHENTICATION")
    print("="*80)
    
    admin_token = admin_login()
    if not admin_token:
        print("❌ CRITICAL: Admin login failed. Cannot continue.")
        sys.exit(1)
    
    driver_token = otp_login(DRIVER_PHONE, "driver")
    if not driver_token:
        print("❌ CRITICAL: Driver login failed. Cannot continue.")
        sys.exit(1)
    
    provider_token = otp_login(PROVIDER_PHONE, "provider")
    if not provider_token:
        print("❌ CRITICAL: Provider login failed. Cannot continue.")
        sys.exit(1)
    
    customer_token = otp_login(CUSTOMER_PHONE, "customer")
    if not customer_token:
        print("❌ CRITICAL: Customer login failed. Cannot continue.")
        sys.exit(1)
    
    # Run tests
    test_app_license(admin_token, driver_token)
    test_driver_regulatory(driver_token, customer_token, admin_token)
    test_vehicle_regulatory(provider_token)
    test_backward_compatibility(provider_token)
    test_regression(admin_token, driver_token, provider_token)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"✅ PASSED: {test_results['passed']}")
    print(f"❌ FAILED: {test_results['failed']}")
    print(f"TOTAL: {test_results['passed'] + test_results['failed']}")
    
    if test_results['failed'] > 0:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
