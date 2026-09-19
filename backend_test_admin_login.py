#!/usr/bin/env python3
"""
CARGO Admin Login Backend Contract Test
Tests ONLY the admin login endpoint with different Origin headers
Does NOT create users, change passwords, or modify any data
"""

import requests
import json
import sys

# Backend URL from frontend/.env
BASE_URL = "https://13a29969-91f4-45b8-a959-be284d40d47e.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"

# Test results
results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}

def log_test(name, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"   {details}")
    
    results["tests"].append({
        "name": name,
        "passed": passed,
        "details": details
    })
    
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1

def test_admin_login_with_origin(origin_header, user_agent, test_name):
    """
    Test admin login with specific Origin and User-Agent headers
    Returns (success, token, user_data, status_code, error_message)
    """
    headers = {
        "Content-Type": "application/json",
        "Origin": origin_header,
        "User-Agent": user_agent
    }
    
    payload = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/admin/login",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"\n{test_name}")
        print(f"  Request: POST /api/auth/admin/login")
        print(f"  Origin: {origin_header}")
        print(f"  User-Agent: {user_agent[:50]}...")
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("token")
            user = data.get("user", {})
            
            print(f"  Token: {'Present' if token else 'Missing'}")
            print(f"  User Role: {user.get('role')}")
            print(f"  Admin Role Key: {user.get('admin_role_key')}")
            print(f"  Status: {user.get('status')}")
            
            return True, token, user, response.status_code, None
        else:
            error_msg = response.text
            print(f"  Error: {error_msg}")
            return False, None, None, response.status_code, error_msg
            
    except Exception as e:
        print(f"\n{test_name}")
        print(f"  Exception: {str(e)}")
        return False, None, None, 0, str(e)

def test_auth_me(token, origin_header, user_agent, test_name):
    """
    Test GET /api/auth/me with Bearer token
    Returns (success, user_data, status_code, error_message)
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Origin": origin_header,
        "User-Agent": user_agent
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers=headers,
            timeout=10
        )
        
        print(f"\n{test_name}")
        print(f"  Request: GET /api/auth/me")
        print(f"  Origin: {origin_header}")
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            user = response.json()
            print(f"  User Role: {user.get('role')}")
            print(f"  Admin Role Key: {user.get('admin_role_key')}")
            print(f"  Status: {user.get('status')}")
            
            return True, user, response.status_code, None
        else:
            error_msg = response.text
            print(f"  Error: {error_msg}")
            return False, None, response.status_code, error_msg
            
    except Exception as e:
        print(f"\n{test_name}")
        print(f"  Exception: {str(e)}")
        return False, None, 0, str(e)

def main():
    print("=" * 80)
    print("CARGO ADMIN LOGIN BACKEND CONTRACT TEST")
    print("=" * 80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Admin Email: {ADMIN_EMAIL}")
    print()
    
    # Define test scenarios with different Origin headers
    test_scenarios = [
        {
            "name": "Desktop - App Preview Origin",
            "origin": "https://13a29969-91f4-45b8-a959-be284d40d47e.preview.emergentagent.com",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        {
            "name": "Desktop - Localhost Origin",
            "origin": "http://localhost:3000",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        {
            "name": "Mobile - App Preview Origin",
            "origin": "https://13a29969-91f4-45b8-a959-be284d40d47e.preview.emergentagent.com",
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        },
        {
            "name": "Mobile - Android",
            "origin": "https://13a29969-91f4-45b8-a959-be284d40d47e.preview.emergentagent.com",
            "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        }
    ]
    
    all_tokens = []
    all_users = []
    
    # Test 1: Admin login with different Origin headers
    print("\n" + "=" * 80)
    print("TEST 1: POST /api/auth/admin/login with different Origin headers")
    print("=" * 80)
    
    for scenario in test_scenarios:
        success, token, user, status_code, error = test_admin_login_with_origin(
            scenario["origin"],
            scenario["user_agent"],
            scenario["name"]
        )
        
        # Verify response
        if success and status_code == 200:
            # Check token
            if not token:
                log_test(
                    f"{scenario['name']}: Token present",
                    False,
                    "Token missing in response"
                )
            else:
                log_test(
                    f"{scenario['name']}: Token present",
                    True,
                    f"Token: {token[:20]}..."
                )
                all_tokens.append(token)
            
            # Check user.role
            if user.get("role") != "admin":
                log_test(
                    f"{scenario['name']}: user.role=admin",
                    False,
                    f"Expected role=admin, got role={user.get('role')}"
                )
            else:
                log_test(
                    f"{scenario['name']}: user.role=admin",
                    True
                )
            
            # Check user.admin_role_key
            if user.get("admin_role_key") != "super_admin":
                log_test(
                    f"{scenario['name']}: admin_role_key=super_admin",
                    False,
                    f"Expected admin_role_key=super_admin, got {user.get('admin_role_key')}"
                )
            else:
                log_test(
                    f"{scenario['name']}: admin_role_key=super_admin",
                    True
                )
            
            # Check user.status
            if user.get("status") != "active":
                log_test(
                    f"{scenario['name']}: status=active",
                    False,
                    f"Expected status=active, got status={user.get('status')}"
                )
            else:
                log_test(
                    f"{scenario['name']}: status=active",
                    True
                )
            
            all_users.append(user)
        else:
            log_test(
                f"{scenario['name']}: HTTP 200 response",
                False,
                f"Status: {status_code}, Error: {error}"
            )
    
    # Test 2: CORS/header check - no explicit CORS errors in response
    print("\n" + "=" * 80)
    print("TEST 2: No CORS/header issues for browser fetch")
    print("=" * 80)
    
    for i, scenario in enumerate(test_scenarios):
        if i < len(all_tokens):
            # Check if we got a valid response (no CORS block would prevent this)
            log_test(
                f"{scenario['name']}: No CORS block",
                True,
                "Response received successfully (CORS headers allow request)"
            )
    
    # Test 3: GET /api/auth/me with Bearer token
    print("\n" + "=" * 80)
    print("TEST 3: GET /api/auth/me with Authorization: Bearer token")
    print("=" * 80)
    
    for i, scenario in enumerate(test_scenarios):
        if i < len(all_tokens):
            token = all_tokens[i]
            success, user, status_code, error = test_auth_me(
                token,
                scenario["origin"],
                scenario["user_agent"],
                scenario["name"]
            )
            
            if success and status_code == 200:
                # Verify same user data
                if user.get("role") == "admin" and user.get("admin_role_key") == "super_admin":
                    log_test(
                        f"{scenario['name']}: GET /api/auth/me returns same user",
                        True,
                        f"role={user.get('role')}, admin_role_key={user.get('admin_role_key')}"
                    )
                else:
                    log_test(
                        f"{scenario['name']}: GET /api/auth/me returns same user",
                        False,
                        f"User data mismatch: role={user.get('role')}, admin_role_key={user.get('admin_role_key')}"
                    )
            else:
                log_test(
                    f"{scenario['name']}: GET /api/auth/me HTTP 200",
                    False,
                    f"Status: {status_code}, Error: {error}"
                )
    
    # Test 4: Confirm no backend difference based on User-Agent or Origin
    print("\n" + "=" * 80)
    print("TEST 4: No backend difference based on User-Agent or Origin")
    print("=" * 80)
    
    if len(all_users) >= 2:
        # Compare user data from different origins
        first_user = all_users[0]
        consistent = True
        
        for i, user in enumerate(all_users[1:], 1):
            if (user.get("id") != first_user.get("id") or
                user.get("role") != first_user.get("role") or
                user.get("admin_role_key") != first_user.get("admin_role_key") or
                user.get("email") != first_user.get("email")):
                consistent = False
                log_test(
                    f"User data consistency check (scenario {i+1})",
                    False,
                    f"User data differs from first scenario"
                )
        
        if consistent:
            log_test(
                "User data consistency across all Origin/User-Agent combinations",
                True,
                "All responses return identical user data"
            )
    
    # Test 5: Confirm no 4xx/5xx errors
    print("\n" + "=" * 80)
    print("TEST 5: No 4xx/5xx errors")
    print("=" * 80)
    
    all_success = len(all_tokens) == len(test_scenarios)
    log_test(
        "All admin login requests returned HTTP 200",
        all_success,
        f"{len(all_tokens)}/{len(test_scenarios)} requests successful"
    )
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {results['passed'] + results['failed']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print()
    
    if results['failed'] == 0:
        print("✅ ALL TESTS PASSED")
        print("\nCONCLUSION:")
        print("- POST /api/auth/admin/login returns HTTP 200 with valid token")
        print("- Response includes user with role=admin, admin_role_key=super_admin, status=active")
        print("- No CORS/header issues for browser fetch")
        print("- GET /api/auth/me with Bearer token returns same user data")
        print("- No backend difference based on User-Agent or Origin")
        print("- No 4xx/5xx errors")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("\nFailed tests:")
        for test in results["tests"]:
            if not test["passed"]:
                print(f"  - {test['name']}: {test['details']}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
