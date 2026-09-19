#!/usr/bin/env python3
"""
CARGO Admin Credential Verification Test
Scope: STRICTLY admin login verification only
- POST /api/auth/admin/login with admin@cargo.om / admin123
- Verify HTTP 200, token, user.role=admin, user.admin_role_key=super_admin, active status
- GET /api/auth/me with Bearer token
- Verify HTTP 200 and same admin identity
"""

import requests
import sys
import os

# Get backend URL from environment
BACKEND_URL = "https://13a29969-91f4-45b8-a959-be284d40d47e.preview.emergentagent.com/api"

def test_admin_login():
    """Test admin login with admin@cargo.om / admin123"""
    print("\n" + "="*80)
    print("CARGO ADMIN CREDENTIAL VERIFICATION TEST")
    print("="*80)
    
    # Test 1: POST /api/auth/admin/login
    print("\n[TEST 1] POST /api/auth/admin/login")
    print(f"  Email: admin@cargo.om")
    print(f"  Password: admin123")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/admin/login",
            json={
                "email": "admin@cargo.om",
                "password": "admin123"
            },
            timeout=10
        )
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"  ❌ FAIL: Expected 200, got {response.status_code}")
            print(f"  Response: {response.text}")
            return False, None, f"Login failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"  ✅ PASS: HTTP 200")
        
        # Verify response structure
        if "token" not in data:
            print(f"  ❌ FAIL: No token in response")
            print(f"  Response: {data}")
            return False, None, "No token in login response"
        
        token = data["token"]
        print(f"  ✅ Token received: {token[:20]}...")
        
        if "user" not in data:
            print(f"  ❌ FAIL: No user in response")
            print(f"  Response: {data}")
            return False, token, "No user object in login response"
        
        user = data["user"]
        print(f"  User data:")
        print(f"    - id: {user.get('id')}")
        print(f"    - email: {user.get('email')}")
        print(f"    - name: {user.get('name')}")
        print(f"    - role: {user.get('role')}")
        print(f"    - admin_role_key: {user.get('admin_role_key')}")
        print(f"    - status: {user.get('status')}")
        
        # Verify user.role = admin
        if user.get("role") != "admin":
            print(f"  ❌ FAIL: Expected user.role='admin', got '{user.get('role')}'")
            return False, token, f"user.role is '{user.get('role')}', expected 'admin'"
        print(f"  ✅ user.role = admin")
        
        # Verify user.admin_role_key = super_admin
        if user.get("admin_role_key") != "super_admin":
            print(f"  ❌ FAIL: Expected user.admin_role_key='super_admin', got '{user.get('admin_role_key')}'")
            return False, token, f"user.admin_role_key is '{user.get('admin_role_key')}', expected 'super_admin'"
        print(f"  ✅ user.admin_role_key = super_admin")
        
        # Verify status = active
        if user.get("status") != "active":
            print(f"  ❌ FAIL: Expected user.status='active', got '{user.get('status')}'")
            return False, token, f"user.status is '{user.get('status')}', expected 'active'"
        print(f"  ✅ user.status = active")
        
        print(f"\n  ✅ TEST 1 PASSED: Admin login successful with correct credentials")
        return True, token, None
        
    except requests.exceptions.RequestException as e:
        print(f"  ❌ FAIL: Request error: {e}")
        return False, None, f"Request error: {e}"
    except Exception as e:
        print(f"  ❌ FAIL: Unexpected error: {e}")
        return False, None, f"Unexpected error: {e}"


def test_auth_me(token):
    """Test GET /api/auth/me with Bearer token"""
    print("\n[TEST 2] GET /api/auth/me")
    print(f"  Using Bearer token: {token[:20]}...")
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/auth/me",
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=10
        )
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"  ❌ FAIL: Expected 200, got {response.status_code}")
            print(f"  Response: {response.text}")
            return False, f"/auth/me failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"  ✅ PASS: HTTP 200")
        
        print(f"  User data:")
        print(f"    - id: {data.get('id')}")
        print(f"    - email: {data.get('email')}")
        print(f"    - name: {data.get('name')}")
        print(f"    - role: {data.get('role')}")
        print(f"    - admin_role_key: {data.get('admin_role_key')}")
        print(f"    - status: {data.get('status')}")
        
        # Verify same admin identity
        if data.get("role") != "admin":
            print(f"  ❌ FAIL: Expected role='admin', got '{data.get('role')}'")
            return False, f"role is '{data.get('role')}', expected 'admin'"
        print(f"  ✅ role = admin")
        
        if data.get("admin_role_key") != "super_admin":
            print(f"  ❌ FAIL: Expected admin_role_key='super_admin', got '{data.get('admin_role_key')}'")
            return False, f"admin_role_key is '{data.get('admin_role_key')}', expected 'super_admin'"
        print(f"  ✅ admin_role_key = super_admin")
        
        if data.get("email") != "admin@cargo.om":
            print(f"  ❌ FAIL: Expected email='admin@cargo.om', got '{data.get('email')}'")
            return False, f"email is '{data.get('email')}', expected 'admin@cargo.om'"
        print(f"  ✅ email = admin@cargo.om")
        
        if data.get("status") != "active":
            print(f"  ❌ FAIL: Expected status='active', got '{data.get('status')}'")
            return False, f"status is '{data.get('status')}', expected 'active'"
        print(f"  ✅ status = active")
        
        print(f"\n  ✅ TEST 2 PASSED: /auth/me returned same admin identity")
        return True, None
        
    except requests.exceptions.RequestException as e:
        print(f"  ❌ FAIL: Request error: {e}")
        return False, f"Request error: {e}"
    except Exception as e:
        print(f"  ❌ FAIL: Unexpected error: {e}")
        return False, f"Unexpected error: {e}"


def main():
    """Run admin credential verification tests"""
    
    # Test 1: Admin login
    login_passed, token, login_error = test_admin_login()
    
    if not login_passed:
        print("\n" + "="*80)
        print("FINAL RESULT: ❌ FAIL")
        print("="*80)
        print(f"Admin login failed: {login_error}")
        print("\nNo password reset was performed.")
        sys.exit(1)
    
    # Test 2: Auth me
    me_passed, me_error = test_auth_me(token)
    
    if not me_passed:
        print("\n" + "="*80)
        print("FINAL RESULT: ❌ FAIL")
        print("="*80)
        print(f"Admin login succeeded but /auth/me failed: {me_error}")
        print("\nNo password reset was performed.")
        sys.exit(1)
    
    # All tests passed
    print("\n" + "="*80)
    print("FINAL RESULT: ✅ PASS")
    print("="*80)
    print("Admin credential verification successful:")
    print("  ✅ POST /api/auth/admin/login returned HTTP 200")
    print("  ✅ Token received")
    print("  ✅ user.role = admin")
    print("  ✅ user.admin_role_key = super_admin")
    print("  ✅ user.status = active")
    print("  ✅ GET /api/auth/me returned HTTP 200")
    print("  ✅ Same admin identity verified")
    print("\nNo password reset was performed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
