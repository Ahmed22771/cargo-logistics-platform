#!/usr/bin/env python3
"""Quick test to debug the 4 failing authorization tests"""
import requests
import json

BASE_URL = "https://shipment-flow-58.preview.emergentagent.com/api"

# Login super admin
print("1. Login super admin...")
resp = requests.post(f"{BASE_URL}/auth/admin/login", 
                     json={"email": "admin@cargo.om", "password": "admin123"}, timeout=20)
print(f"   Status: {resp.status_code}")
super_admin_token = resp.json().get("token")
super_admin_id = resp.json().get("user", {}).get("id")
print(f"   Token: {super_admin_token[:20]}...")
print(f"   Admin ID: {super_admin_id}")

# Login document_reviewer (need to create first or use existing)
print("\n2. Get existing document_reviewer admin...")
resp = requests.get(f"{BASE_URL}/admin/admins", 
                   headers={"Authorization": f"Bearer {super_admin_token}"}, timeout=20)
admins = resp.json()
doc_reviewer = next((a for a in admins if a.get("admin_role_key") == "document_reviewer"), None)
if doc_reviewer:
    print(f"   Found: {doc_reviewer.get('email')}")
    # Try to login
    print("\n3. Login document_reviewer...")
    # We don't know the password, so let's reset it first
    resp = requests.post(f"{BASE_URL}/admin/users/{doc_reviewer['id']}/reset-password",
                        headers={"Authorization": f"Bearer {super_admin_token}"},
                        json={"password": "test123"}, timeout=20)
    print(f"   Reset password status: {resp.status_code}")
    
    resp = requests.post(f"{BASE_URL}/auth/admin/login",
                        json={"email": doc_reviewer['email'], "password": "test123"}, timeout=20)
    print(f"   Login status: {resp.status_code}")
    if resp.status_code == 200:
        dr_token = resp.json().get("token")
        print(f"   Token: {dr_token[:20]}...")
        
        # Test 1: document_reviewer tries to access finance stats (should be 403)
        print("\n4. TEST: document_reviewer GET /admin/finance/stats (expect 403)...")
        try:
            resp = requests.get(f"{BASE_URL}/admin/finance/stats",
                              headers={"Authorization": f"Bearer {dr_token}"}, timeout=20)
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
        except Exception as e:
            print(f"   ERROR: {type(e).__name__}: {str(e)}")

# Test 2: No Authorization header (should be 401)
print("\n5. TEST: No Authorization header GET /admin/finance/stats (expect 401)...")
try:
    resp = requests.get(f"{BASE_URL}/admin/finance/stats", timeout=20)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.text[:200]}")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {str(e)}")

# Test 3: Disabled customer login (should be 403)
print("\n6. TEST: Disabled customer login (expect 403)...")
# First disable the customer
customer_id = "5e177fa7-3136-4d2a-ba50-bb44cae2920e"  # From previous test
resp = requests.post(f"{BASE_URL}/admin/users/{customer_id}/status",
                    headers={"Authorization": f"Bearer {super_admin_token}"},
                    json={"status": "disabled"}, timeout=20)
print(f"   Disable status: {resp.status_code}")

# Try to login
try:
    resp = requests.post(f"{BASE_URL}/auth/otp/request",
                        json={"phone": "+96890000001", "role": "customer"}, timeout=20)
    print(f"   OTP request status: {resp.status_code}")
    if resp.status_code == 200:
        demo_code = resp.json().get("demo_code")
        print(f"   Demo code: {demo_code}")
        
        resp = requests.post(f"{BASE_URL}/auth/otp/verify",
                            json={"phone": "+96890000001", "role": "customer", "code": demo_code}, timeout=20)
        print(f"   OTP verify status: {resp.status_code}")
        print(f"   Response: {resp.text[:200]}")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {str(e)}")

# Re-enable customer
resp = requests.post(f"{BASE_URL}/admin/users/{customer_id}/status",
                    headers={"Authorization": f"Bearer {super_admin_token}"},
                    json={"status": "active"}, timeout=20)
print(f"   Re-enable status: {resp.status_code}")

# Test 4: Disable self (should be 400)
print("\n7. TEST: Super admin disable self (expect 400 CANNOT_DISABLE_SELF)...")
try:
    resp = requests.post(f"{BASE_URL}/admin/users/{super_admin_id}/status",
                        headers={"Authorization": f"Bearer {super_admin_token}"},
                        json={"status": "disabled"}, timeout=20)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.text[:200]}")
except Exception as e:
    print(f"   ERROR: {type(e).__name__}: {str(e)}")

print("\nDone!")
