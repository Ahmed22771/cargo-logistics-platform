#!/usr/bin/env python3
"""
Phase 2B Backend Security Verification
CARGO RBAC Authorization Matrix + Privilege Escalation + Object-Level Isolation Testing
"""
import os
import sys
import json
import requests
from typing import Dict, List, Optional, Tuple

# Backend URL - use localhost since we're testing backend directly
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api"

# Test credentials from /app/memory/test_credentials.md
SUPER_ADMIN_EMAIL = "admin@cargo.om"
SUPER_ADMIN_PASSWORD = "admin123"
PROVIDER_PHONE = "+96890000005"

# Test state
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "sections": {}
}

disposable_admins = {}  # Store created test admin users
super_admin_token = None
super_admin_id = None
all_roles = []


def log(msg: str, level: str = "INFO"):
    """Log test messages"""
    prefix = {
        "INFO": "ℹ️",
        "PASS": "✅",
        "FAIL": "❌",
        "WARN": "⚠️",
        "SECTION": "📋"
    }.get(level, "  ")
    print(f"{prefix} {msg}")


def record_test(section: str, test_name: str, passed: bool, details: str = ""):
    """Record test result"""
    test_results["total"] += 1
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
    
    if section not in test_results["sections"]:
        test_results["sections"][section] = {"passed": 0, "failed": 0, "tests": []}
    
    test_results["sections"][section]["tests"].append({
        "name": test_name,
        "passed": passed,
        "details": details
    })
    
    if passed:
        test_results["sections"][section]["passed"] += 1
    else:
        test_results["sections"][section]["failed"] += 1


def admin_login(email: str, password: str) -> Tuple[Optional[str], Optional[dict]]:
    """Login as admin and return (token, user)"""
    try:
        resp = requests.post(f"{API_BASE}/auth/admin/login", json={
            "email": email,
            "password": password
        }, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("token"), data.get("user")
        return None, None
    except Exception as e:
        log(f"Admin login error: {e}", "FAIL")
        return None, None


def otp_login(phone: str, role: str = "provider") -> Tuple[Optional[str], Optional[dict]]:
    """OTP login for customer/driver/provider"""
    try:
        # Request OTP
        resp = requests.post(f"{API_BASE}/auth/otp/request", json={
            "phone": phone,
            "role": role
        }, timeout=10)
        if resp.status_code != 200:
            return None, None
        
        demo_code = resp.json().get("demo_code")
        if not demo_code:
            return None, None
        
        # Verify OTP
        resp = requests.post(f"{API_BASE}/auth/otp/verify", json={
            "phone": phone,
            "role": role,
            "code": demo_code,
            "name": phone
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get("token"), data.get("user")
        return None, None
    except Exception as e:
        log(f"OTP login error: {e}", "FAIL")
        return None, None


def get_with_auth(endpoint: str, token: str, params: dict = None) -> requests.Response:
    """GET request with auth token"""
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{API_BASE}{endpoint}", headers=headers, params=params, timeout=10)


def post_with_auth(endpoint: str, token: str, data: dict) -> requests.Response:
    """POST request with auth token"""
    headers = {"Authorization": f"Bearer {token}"}
    return requests.post(f"{API_BASE}{endpoint}", headers=headers, json=data, timeout=10)


def put_with_auth(endpoint: str, token: str, data: dict) -> requests.Response:
    """PUT request with auth token"""
    headers = {"Authorization": f"Bearer {token}"}
    return requests.put(f"{API_BASE}{endpoint}", headers=headers, json=data, timeout=10)


def section_a_authenticate_and_identify():
    """Section A: Authenticate as super_admin and identify protected account + all roles"""
    global super_admin_token, super_admin_id, all_roles
    
    log("=" * 80, "SECTION")
    log("SECTION A: Authenticate as super_admin and identify protected account + roles", "SECTION")
    log("=" * 80, "SECTION")
    
    # A1: Super admin login
    log("A1: Authenticating as super_admin (admin@cargo.om/admin123)...")
    token, user = admin_login(SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD)
    
    if token and user:
        super_admin_token = token
        super_admin_id = user.get("id")
        admin_role_key = user.get("admin_role_key")
        
        log(f"PASS: Super admin login successful", "PASS")
        log(f"  Super admin ID: {super_admin_id}")
        log(f"  Admin role key: {admin_role_key}")
        record_test("A_Authentication", "A1_super_admin_login", True, 
                   f"Token obtained, ID={super_admin_id}, role={admin_role_key}")
        
        if admin_role_key != "super_admin":
            log(f"FAIL: Expected admin_role_key='super_admin', got '{admin_role_key}'", "FAIL")
            record_test("A_Authentication", "A1_super_admin_role_check", False,
                       f"Expected super_admin, got {admin_role_key}")
        else:
            record_test("A_Authentication", "A1_super_admin_role_check", True,
                       "admin_role_key is super_admin")
    else:
        log("FAIL: Super admin login failed", "FAIL")
        record_test("A_Authentication", "A1_super_admin_login", False, "Login failed")
        sys.exit(1)
    
    # A2: Get all roles
    log("\nA2: Fetching all canonical roles...")
    resp = get_with_auth("/admin/roles", super_admin_token)
    
    if resp.status_code == 200:
        all_roles = resp.json()
        log(f"PASS: Retrieved {len(all_roles)} roles", "PASS")
        
        role_keys = [r.get("key") for r in all_roles]
        log(f"  Available roles: {', '.join(role_keys)}")
        
        # Check for required canonical roles
        required_roles = ["super_admin", "manager", "supervisor", "document_reviewer", 
                         "finance_accountant", "ministry_supervisor"]
        missing_roles = [r for r in required_roles if r not in role_keys]
        
        if missing_roles:
            log(f"WARN: Missing canonical roles: {', '.join(missing_roles)}", "WARN")
            record_test("A_Authentication", "A2_canonical_roles_present", False,
                       f"Missing: {', '.join(missing_roles)}")
        else:
            log(f"PASS: All 6 canonical roles present", "PASS")
            record_test("A_Authentication", "A2_canonical_roles_present", True,
                       "All 6 canonical roles found")
        
        # Display permissions for each role
        for role in all_roles:
            perms = role.get("permissions", [])
            log(f"  {role['key']}: {len(perms)} permissions")
    else:
        log(f"FAIL: Failed to retrieve roles (HTTP {resp.status_code})", "FAIL")
        record_test("A_Authentication", "A2_get_roles", False, 
                   f"HTTP {resp.status_code}: {resp.text[:200]}")


def section_b_create_disposable_admins():
    """Section B: Create disposable admin users for each lower-level role"""
    global disposable_admins
    
    log("\n" + "=" * 80, "SECTION")
    log("SECTION B: Create disposable admin users for testing", "SECTION")
    log("=" * 80, "SECTION")
    
    # Roles to create (excluding super_admin)
    test_roles = ["manager", "supervisor", "document_reviewer", "finance_accountant", "ministry_supervisor"]
    
    import time
    timestamp = int(time.time())
    
    for role_key in test_roles:
        log(f"\nB: Creating disposable admin with role '{role_key}'...")
        
        email = f"test_{role_key}_{timestamp}@cargo.test"
        password = f"test_{role_key}_123"
        
        resp = post_with_auth("/admin/admins", super_admin_token, {
            "name": f"Test {role_key.replace('_', ' ').title()}",
            "email": email,
            "password": password,
            "admin_role_key": role_key
        })
        
        if resp.status_code == 200:
            data = resp.json()
            admin_id = data.get("id")
            
            # Login as this admin to get token
            token, user = admin_login(email, password)
            
            if token and user:
                disposable_admins[role_key] = {
                    "id": admin_id,
                    "email": email,
                    "password": password,
                    "token": token,
                    "user": user
                }
                log(f"PASS: Created and authenticated {role_key} (ID: {admin_id})", "PASS")
                record_test("B_Create_Admins", f"B_create_{role_key}", True,
                           f"ID={admin_id}, email={email}")
            else:
                log(f"FAIL: Created {role_key} but login failed", "FAIL")
                record_test("B_Create_Admins", f"B_create_{role_key}", False,
                           "Admin created but login failed")
        else:
            log(f"FAIL: Failed to create {role_key} (HTTP {resp.status_code})", "FAIL")
            record_test("B_Create_Admins", f"B_create_{role_key}", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
    
    log(f"\nCreated {len(disposable_admins)} disposable admin users")


def section_c_authorization_matrix():
    """Section C: Test authorization matrix - lower-level roles cannot modify super_admin"""
    log("\n" + "=" * 80, "SECTION")
    log("SECTION C: Authorization Matrix - Protected Super Admin Account", "SECTION")
    log("=" * 80, "SECTION")
    
    if not super_admin_id:
        log("FAIL: Super admin ID not available", "FAIL")
        return
    
    # Test each lower-level role attempting to modify super_admin
    for role_key, admin_data in disposable_admins.items():
        log(f"\n--- Testing {role_key} attempting to modify super_admin ---")
        token = admin_data["token"]
        actor_id = admin_data["id"]
        
        # C1: Attempt PUT /api/admin/users/{super_admin_id} (name/notes)
        log(f"C1.{role_key}: Attempting PUT /admin/users/{super_admin_id} (update name/notes)...")
        resp = put_with_auth(f"/admin/users/{super_admin_id}", token, {
            "name": "HACKED NAME",
            "notes": "This should be blocked"
        })
        
        if resp.status_code == 403:
            detail = resp.json().get("detail", "")
            if "SUPER_ADMIN_PROTECTED" in detail or "PLATFORM_ADMIN_ROLE_REQUIRED" in detail:
                log(f"PASS: {role_key} blocked from updating super_admin (403 {detail})", "PASS")
                record_test("C_Authorization_Matrix", f"C1_{role_key}_update_super_admin", True,
                           f"403 {detail}")
            else:
                log(f"PASS: {role_key} blocked (403) but unexpected detail: {detail}", "PASS")
                record_test("C_Authorization_Matrix", f"C1_{role_key}_update_super_admin", True,
                           f"403 {detail}")
        else:
            log(f"FAIL: {role_key} got HTTP {resp.status_code} (expected 403)", "FAIL")
            record_test("C_Authorization_Matrix", f"C1_{role_key}_update_super_admin", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        # C2: Attempt PUT /api/admin/users/{super_admin_id} with admin_role_key change
        log(f"C2.{role_key}: Attempting PUT /admin/users/{super_admin_id} (change admin_role_key)...")
        resp = put_with_auth(f"/admin/users/{super_admin_id}", token, {
            "admin_role_key": "manager"
        })
        
        if resp.status_code == 403:
            detail = resp.json().get("detail", "")
            log(f"PASS: {role_key} blocked from changing super_admin role (403 {detail})", "PASS")
            record_test("C_Authorization_Matrix", f"C2_{role_key}_change_super_admin_role", True,
                       f"403 {detail}")
        else:
            log(f"FAIL: {role_key} got HTTP {resp.status_code} (expected 403)", "FAIL")
            record_test("C_Authorization_Matrix", f"C2_{role_key}_change_super_admin_role", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        # C3: Attempt POST /api/admin/users/{super_admin_id}/reset-password
        log(f"C3.{role_key}: Attempting POST /admin/users/{super_admin_id}/reset-password...")
        resp = post_with_auth(f"/admin/users/{super_admin_id}/reset-password", token, {
            "password": "hacked123"
        })
        
        if resp.status_code == 403:
            detail = resp.json().get("detail", "")
            log(f"PASS: {role_key} blocked from resetting super_admin password (403 {detail})", "PASS")
            record_test("C_Authorization_Matrix", f"C3_{role_key}_reset_super_admin_password", True,
                       f"403 {detail}")
        else:
            log(f"FAIL: {role_key} got HTTP {resp.status_code} (expected 403)", "FAIL")
            record_test("C_Authorization_Matrix", f"C3_{role_key}_reset_super_admin_password", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        # C4: Attempt POST /api/admin/users/{super_admin_id}/status (disable)
        log(f"C4.{role_key}: Attempting POST /admin/users/{super_admin_id}/status (disable)...")
        resp = post_with_auth(f"/admin/users/{super_admin_id}/status", token, {
            "status": "disabled"
        })
        
        if resp.status_code in [400, 403]:
            detail = resp.json().get("detail", "")
            log(f"PASS: {role_key} blocked from disabling super_admin ({resp.status_code} {detail})", "PASS")
            record_test("C_Authorization_Matrix", f"C4_{role_key}_disable_super_admin", True,
                       f"{resp.status_code} {detail}")
        else:
            log(f"FAIL: {role_key} got HTTP {resp.status_code} (expected 400/403)", "FAIL")
            record_test("C_Authorization_Matrix", f"C4_{role_key}_disable_super_admin", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        # C5: Attempt POST /api/admin/users/{super_admin_id}/suspend
        log(f"C5.{role_key}: Attempting POST /admin/users/{super_admin_id}/suspend...")
        resp = post_with_auth(f"/admin/users/{super_admin_id}/suspend", token, {
            "reason": "Test suspension"
        })
        
        if resp.status_code in [400, 403]:
            detail = resp.json().get("detail", "")
            log(f"PASS: {role_key} blocked from suspending super_admin ({resp.status_code} {detail})", "PASS")
            record_test("C_Authorization_Matrix", f"C5_{role_key}_suspend_super_admin", True,
                       f"{resp.status_code} {detail}")
        else:
            log(f"FAIL: {role_key} got HTTP {resp.status_code} (expected 400/403)", "FAIL")
            record_test("C_Authorization_Matrix", f"C5_{role_key}_suspend_super_admin", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        # C6: Attempt POST /api/admin/users/{super_admin_id}/activate
        log(f"C6.{role_key}: Attempting POST /admin/users/{super_admin_id}/activate...")
        resp = post_with_auth(f"/admin/users/{super_admin_id}/activate", token, {})
        
        if resp.status_code == 403:
            detail = resp.json().get("detail", "")
            log(f"PASS: {role_key} blocked from activating super_admin (403 {detail})", "PASS")
            record_test("C_Authorization_Matrix", f"C6_{role_key}_activate_super_admin", True,
                       f"403 {detail}")
        else:
            log(f"FAIL: {role_key} got HTTP {resp.status_code} (expected 403)", "FAIL")
            record_test("C_Authorization_Matrix", f"C6_{role_key}_activate_super_admin", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        # C7: Attempt PUT /api/admin/admins/{super_admin_id}/role
        log(f"C7.{role_key}: Attempting PUT /admin/admins/{super_admin_id}/role...")
        resp = put_with_auth(f"/admin/admins/{super_admin_id}/role", token, {
            "admin_role_key": "manager"
        })
        
        if resp.status_code == 403:
            detail = resp.json().get("detail", "")
            log(f"PASS: {role_key} blocked from changing super_admin role (403 {detail})", "PASS")
            record_test("C_Authorization_Matrix", f"C7_{role_key}_change_role_endpoint", True,
                       f"403 {detail}")
        else:
            log(f"FAIL: {role_key} got HTTP {resp.status_code} (expected 403)", "FAIL")
            record_test("C_Authorization_Matrix", f"C7_{role_key}_change_role_endpoint", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")


def section_d_self_protection():
    """Section D: Test self-protection - users cannot suspend/disable themselves"""
    log("\n" + "=" * 80, "SECTION")
    log("SECTION D: Self-Protection Testing", "SECTION")
    log("=" * 80, "SECTION")
    
    # Test with manager role
    if "manager" in disposable_admins:
        manager = disposable_admins["manager"]
        manager_id = manager["id"]
        manager_token = manager["token"]
        
        log(f"\nD1: Manager attempting to suspend self (ID: {manager_id})...")
        resp = post_with_auth(f"/admin/users/{manager_id}/suspend", manager_token, {
            "reason": "Self-suspend test"
        })
        
        if resp.status_code == 400:
            detail = resp.json().get("detail", "")
            if "CANNOT_SUSPEND_SELF" in detail:
                log(f"PASS: Self-suspension blocked (400 {detail})", "PASS")
                record_test("D_Self_Protection", "D1_manager_cannot_suspend_self", True,
                           f"400 {detail}")
            else:
                log(f"PASS: Self-suspension blocked (400) but unexpected detail: {detail}", "PASS")
                record_test("D_Self_Protection", "D1_manager_cannot_suspend_self", True,
                           f"400 {detail}")
        else:
            log(f"FAIL: Got HTTP {resp.status_code} (expected 400 CANNOT_SUSPEND_SELF)", "FAIL")
            record_test("D_Self_Protection", "D1_manager_cannot_suspend_self", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        log(f"\nD2: Manager attempting to disable self via /status endpoint...")
        resp = post_with_auth(f"/admin/users/{manager_id}/status", manager_token, {
            "status": "disabled"
        })
        
        if resp.status_code == 400:
            detail = resp.json().get("detail", "")
            if "CANNOT_DISABLE_SELF" in detail:
                log(f"PASS: Self-disable blocked (400 {detail})", "PASS")
                record_test("D_Self_Protection", "D2_manager_cannot_disable_self", True,
                           f"400 {detail}")
            else:
                log(f"PASS: Self-disable blocked (400) but unexpected detail: {detail}", "PASS")
                record_test("D_Self_Protection", "D2_manager_cannot_disable_self", True,
                           f"400 {detail}")
        else:
            log(f"FAIL: Got HTTP {resp.status_code} (expected 400 CANNOT_DISABLE_SELF)", "FAIL")
            record_test("D_Self_Protection", "D2_manager_cannot_disable_self", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")


def section_e_last_super_admin_protection():
    """Section E: Test last active super_admin protection"""
    log("\n" + "=" * 80, "SECTION")
    log("SECTION E: Last Active Super Admin Protection", "SECTION")
    log("=" * 80, "SECTION")
    
    log("\nE1: Attempting to suspend the only active super_admin...")
    resp = post_with_auth(f"/admin/users/{super_admin_id}/suspend", super_admin_token, {
        "reason": "Test last super admin protection"
    })
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "CANNOT_SUSPEND_LAST_SUPER_ADMIN" in detail or "CANNOT_SUSPEND_SELF" in detail:
            log(f"PASS: Last super admin suspension blocked (400 {detail})", "PASS")
            record_test("E_Last_Super_Admin", "E1_cannot_suspend_last_super_admin", True,
                       f"400 {detail}")
        else:
            log(f"PASS: Suspension blocked (400) but unexpected detail: {detail}", "PASS")
            record_test("E_Last_Super_Admin", "E1_cannot_suspend_last_super_admin", True,
                       f"400 {detail}")
    else:
        log(f"FAIL: Got HTTP {resp.status_code} (expected 400)", "FAIL")
        record_test("E_Last_Super_Admin", "E1_cannot_suspend_last_super_admin", False,
                   f"HTTP {resp.status_code}: {resp.text[:200]}")


def section_f_privilege_escalation():
    """Section F: Test privilege escalation prevention"""
    log("\n" + "=" * 80, "SECTION")
    log("SECTION F: Privilege Escalation Prevention", "SECTION")
    log("=" * 80, "SECTION")
    
    import time
    timestamp = int(time.time())
    
    for role_key, admin_data in disposable_admins.items():
        log(f"\n--- Testing {role_key} privilege escalation attempts ---")
        token = admin_data["token"]
        actor_id = admin_data["id"]
        
        # F1: Attempt to create new admin with super_admin role
        log(f"F1.{role_key}: Attempting POST /admin/admins with admin_role_key=super_admin...")
        resp = post_with_auth("/admin/admins", token, {
            "name": f"Escalation Test {timestamp}",
            "email": f"escalation_{role_key}_{timestamp}@cargo.test",
            "password": "test123",
            "admin_role_key": "super_admin"
        })
        
        if resp.status_code == 403:
            detail = resp.json().get("detail", "")
            if "PLATFORM_ADMIN_ROLE_REQUIRED" in detail:
                log(f"PASS: {role_key} blocked from creating super_admin (403 {detail})", "PASS")
                record_test("F_Privilege_Escalation", f"F1_{role_key}_create_super_admin", True,
                           f"403 {detail}")
            else:
                log(f"PASS: {role_key} blocked (403) but unexpected detail: {detail}", "PASS")
                record_test("F_Privilege_Escalation", f"F1_{role_key}_create_super_admin", True,
                           f"403 {detail}")
        else:
            log(f"FAIL: {role_key} got HTTP {resp.status_code} (expected 403)", "FAIL")
            record_test("F_Privilege_Escalation", f"F1_{role_key}_create_super_admin", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        # F2: Attempt to escalate own role to super_admin via PUT /admin/users/{id}
        log(f"F2.{role_key}: Attempting PUT /admin/users/{actor_id} with admin_role_key=super_admin...")
        resp = put_with_auth(f"/admin/users/{actor_id}", token, {
            "admin_role_key": "super_admin"
        })
        
        if resp.status_code == 403:
            detail = resp.json().get("detail", "")
            if "PLATFORM_ADMIN_ROLE_REQUIRED" in detail:
                log(f"PASS: {role_key} blocked from self-escalation (403 {detail})", "PASS")
                record_test("F_Privilege_Escalation", f"F2_{role_key}_self_escalate_users", True,
                           f"403 {detail}")
            else:
                log(f"PASS: {role_key} blocked (403) but unexpected detail: {detail}", "PASS")
                record_test("F_Privilege_Escalation", f"F2_{role_key}_self_escalate_users", True,
                           f"403 {detail}")
        else:
            log(f"FAIL: {role_key} got HTTP {resp.status_code} (expected 403)", "FAIL")
            record_test("F_Privilege_Escalation", f"F2_{role_key}_self_escalate_users", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        # F3: Attempt to escalate own role via PUT /admin/admins/{id}/role
        log(f"F3.{role_key}: Attempting PUT /admin/admins/{actor_id}/role with admin_role_key=super_admin...")
        resp = put_with_auth(f"/admin/admins/{actor_id}/role", token, {
            "admin_role_key": "super_admin"
        })
        
        if resp.status_code == 403:
            detail = resp.json().get("detail", "")
            if "PLATFORM_ADMIN_ROLE_REQUIRED" in detail:
                log(f"PASS: {role_key} blocked from role escalation (403 {detail})", "PASS")
                record_test("F_Privilege_Escalation", f"F3_{role_key}_self_escalate_role", True,
                           f"403 {detail}")
            else:
                log(f"PASS: {role_key} blocked (403) but unexpected detail: {detail}", "PASS")
                record_test("F_Privilege_Escalation", f"F3_{role_key}_self_escalate_role", True,
                           f"403 {detail}")
        else:
            log(f"FAIL: {role_key} got HTTP {resp.status_code} (expected 403)", "FAIL")
            record_test("F_Privilege_Escalation", f"F3_{role_key}_self_escalate_role", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")


def section_g_super_admin_can_manage_normal_staff():
    """Section G: Verify super_admin CAN manage normal (non-super-admin) staff"""
    log("\n" + "=" * 80, "SECTION")
    log("SECTION G: Super Admin Can Manage Normal Staff", "SECTION")
    log("=" * 80, "SECTION")
    
    # Test with manager role
    if "manager" in disposable_admins:
        manager = disposable_admins["manager"]
        manager_id = manager["id"]
        
        log(f"\nG1: Super admin updating manager notes...")
        resp = put_with_auth(f"/admin/users/{manager_id}", super_admin_token, {
            "notes": "Updated by super admin - test"
        })
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("notes") == "Updated by super admin - test":
                log(f"PASS: Super admin successfully updated manager notes", "PASS")
                record_test("G_Super_Admin_Management", "G1_super_admin_update_manager", True,
                           "Notes updated successfully")
            else:
                log(f"FAIL: Update returned 200 but notes not changed", "FAIL")
                record_test("G_Super_Admin_Management", "G1_super_admin_update_manager", False,
                           "Notes not updated")
        else:
            log(f"FAIL: Super admin got HTTP {resp.status_code} (expected 200)", "FAIL")
            record_test("G_Super_Admin_Management", "G1_super_admin_update_manager", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")
        
        log(f"\nG2: Super admin changing manager role to supervisor...")
        resp = put_with_auth(f"/admin/admins/{manager_id}/role", super_admin_token, {
            "admin_role_key": "supervisor"
        })
        
        if resp.status_code == 200:
            log(f"PASS: Super admin successfully changed manager role", "PASS")
            record_test("G_Super_Admin_Management", "G2_super_admin_change_manager_role", True,
                       "Role changed to supervisor")
            
            # Change it back
            log(f"  Changing role back to manager...")
            resp = put_with_auth(f"/admin/admins/{manager_id}/role", super_admin_token, {
                "admin_role_key": "manager"
            })
            if resp.status_code == 200:
                log(f"  Role restored to manager")
        else:
            log(f"FAIL: Super admin got HTTP {resp.status_code} (expected 200)", "FAIL")
            record_test("G_Super_Admin_Management", "G2_super_admin_change_manager_role", False,
                       f"HTTP {resp.status_code}: {resp.text[:200]}")


def section_h_provider_model():
    """Section H: Test provider/company model and isolation"""
    log("\n" + "=" * 80, "SECTION")
    log("SECTION H: Provider/Company Model Testing", "SECTION")
    log("=" * 80, "SECTION")
    
    log("\nH1: Authenticating as provider (+96890000005)...")
    provider_token, provider_user = otp_login(PROVIDER_PHONE, "provider")
    
    if not provider_token or not provider_user:
        log("FAIL: Provider login failed", "FAIL")
        record_test("H_Provider_Model", "H1_provider_login", False, "Login failed")
        return
    
    provider_id = provider_user.get("id")
    company_role = provider_user.get("company_role")
    company_name = provider_user.get("company_name")
    
    log(f"PASS: Provider login successful", "PASS")
    log(f"  Provider ID: {provider_id}")
    log(f"  Company role: {company_role}")
    log(f"  Company name: {company_name}")
    record_test("H_Provider_Model", "H1_provider_login", True,
               f"ID={provider_id}, company_role={company_role}")
    
    # H2: Verify provider CANNOT access platform admin endpoints
    admin_endpoints = [
        "/admin/users",
        "/admin/admins",
        "/admin/roles",
        "/admin/finance/stats"
    ]
    
    for endpoint in admin_endpoints:
        log(f"\nH2: Provider attempting GET {endpoint}...")
        resp = get_with_auth(endpoint, provider_token)
        
        if resp.status_code == 403:
            log(f"PASS: Provider blocked from {endpoint} (403)", "PASS")
            record_test("H_Provider_Model", f"H2_provider_blocked_{endpoint.replace('/', '_')}", True,
                       "403 Forbidden")
        else:
            log(f"FAIL: Provider got HTTP {resp.status_code} for {endpoint} (expected 403)", "FAIL")
            record_test("H_Provider_Model", f"H2_provider_blocked_{endpoint.replace('/', '_')}", False,
                       f"HTTP {resp.status_code}")
    
    # H3: Verify provider CANNOT modify super_admin
    log(f"\nH3: Provider attempting PUT /admin/users/{super_admin_id}...")
    resp = put_with_auth(f"/admin/users/{super_admin_id}", provider_token, {
        "notes": "Provider hack attempt"
    })
    
    if resp.status_code == 403:
        log(f"PASS: Provider blocked from modifying super_admin (403)", "PASS")
        record_test("H_Provider_Model", "H3_provider_cannot_modify_super_admin", True,
                   "403 Forbidden")
    else:
        log(f"FAIL: Provider got HTTP {resp.status_code} (expected 403)", "FAIL")
        record_test("H_Provider_Model", "H3_provider_cannot_modify_super_admin", False,
                   f"HTTP {resp.status_code}")
    
    # H4: Check if company manager/supervisor roles exist
    log(f"\nH4: Checking for company-specific roles...")
    company_roles = [r for r in all_roles if "company" in r.get("key", "").lower()]
    
    if company_roles:
        log(f"INFO: Found {len(company_roles)} company-related roles:", "INFO")
        for r in company_roles:
            log(f"  - {r.get('key')}: {r.get('name_en')}")
        record_test("H_Provider_Model", "H4_company_roles_exist", True,
                   f"Found {len(company_roles)} company roles")
    else:
        log(f"INFO: No company-specific roles found in this build", "INFO")
        log(f"  Available roles: {', '.join([r.get('key') for r in all_roles])}")
        record_test("H_Provider_Model", "H4_company_roles_exist", True,
                   "No company roles in this build (as expected)")
    
    # H5: Test provider access to own data
    log(f"\nH5: Provider accessing own opportunities...")
    resp = get_with_auth("/provider/opportunities", provider_token)
    
    if resp.status_code == 200:
        opportunities = resp.json()
        log(f"PASS: Provider can access opportunities ({len(opportunities)} found)", "PASS")
        record_test("H_Provider_Model", "H5_provider_access_opportunities", True,
                   f"{len(opportunities)} opportunities")
    else:
        log(f"FAIL: Provider got HTTP {resp.status_code} (expected 200)", "FAIL")
        record_test("H_Provider_Model", "H5_provider_access_opportunities", False,
                   f"HTTP {resp.status_code}")
    
    log(f"\nH6: Provider accessing own summary...")
    resp = get_with_auth("/provider/summary", provider_token)
    
    if resp.status_code == 200:
        summary = resp.json()
        log(f"PASS: Provider can access summary", "PASS")
        log(f"  Opportunities: {summary.get('opportunities')}")
        log(f"  Trips: {summary.get('trips')}")
        record_test("H_Provider_Model", "H6_provider_access_summary", True,
                   f"Summary retrieved")
    else:
        log(f"FAIL: Provider got HTTP {resp.status_code} (expected 200)", "FAIL")
        record_test("H_Provider_Model", "H6_provider_access_summary", False,
                   f"HTTP {resp.status_code}")


def section_i_object_level_isolation():
    """Section I: Test object-level isolation for providers"""
    log("\n" + "=" * 80, "SECTION")
    log("SECTION I: Object-Level Isolation Testing", "SECTION")
    log("=" * 80, "SECTION")
    
    log("\nI1: Authenticating as provider...")
    provider_token, provider_user = otp_login(PROVIDER_PHONE, "provider")
    
    if not provider_token:
        log("FAIL: Provider login failed", "FAIL")
        return
    
    provider_id = provider_user.get("id")
    
    # I2: Get provider's own transactions
    log(f"\nI2: Provider accessing own transactions...")
    resp = get_with_auth("/provider/transactions", provider_token)
    
    if resp.status_code == 200:
        transactions = resp.json()
        log(f"PASS: Provider can access own transactions ({len(transactions)} found)", "PASS")
        record_test("I_Object_Isolation", "I2_provider_own_transactions", True,
                   f"{len(transactions)} transactions")
        
        # Verify all transactions belong to this provider
        other_provider_txns = [t for t in transactions if t.get("account_id") != provider_id]
        if other_provider_txns:
            log(f"FAIL: Found {len(other_provider_txns)} transactions not belonging to provider", "FAIL")
            record_test("I_Object_Isolation", "I2_provider_transaction_isolation", False,
                       f"Found {len(other_provider_txns)} other provider transactions")
        else:
            log(f"PASS: All transactions belong to provider (isolation verified)", "PASS")
            record_test("I_Object_Isolation", "I2_provider_transaction_isolation", True,
                       "All transactions belong to provider")
    else:
        log(f"FAIL: Provider got HTTP {resp.status_code} (expected 200)", "FAIL")
        record_test("I_Object_Isolation", "I2_provider_own_transactions", False,
                   f"HTTP {resp.status_code}")
    
    # I3: Attempt to access another user's data via admin endpoints
    log(f"\nI3: Provider attempting to access admin finance account endpoint...")
    # Try to access a customer's finance account
    resp = get_with_auth("/admin/finance/account/some-customer-id", provider_token)
    
    if resp.status_code == 403:
        log(f"PASS: Provider blocked from admin finance endpoint (403)", "PASS")
        record_test("I_Object_Isolation", "I3_provider_blocked_admin_finance", True,
                   "403 Forbidden")
    else:
        log(f"FAIL: Provider got HTTP {resp.status_code} (expected 403)", "FAIL")
        record_test("I_Object_Isolation", "I3_provider_blocked_admin_finance", False,
                   f"HTTP {resp.status_code}")


def section_j_regression_super_admin_access():
    """Section J: Regression - verify legitimate super_admin access"""
    log("\n" + "=" * 80, "SECTION")
    log("SECTION J: Regression - Legitimate Super Admin Access", "SECTION")
    log("=" * 80, "SECTION")
    
    admin_endpoints = [
        "/admin/stats",
        "/admin/users",
        "/admin/roles",
        "/admin/finance/stats",
        "/admin/finance/transactions",
        "/admin/documents",
        "/admin/audit-logs",
        "/admin/ops-stats"
    ]
    
    for endpoint in admin_endpoints:
        log(f"\nJ: Super admin accessing {endpoint}...")
        resp = get_with_auth(endpoint, super_admin_token)
        
        if resp.status_code == 200:
            log(f"PASS: Super admin can access {endpoint}", "PASS")
            record_test("J_Regression", f"J_super_admin_access_{endpoint.replace('/', '_')}", True,
                       "200 OK")
        else:
            log(f"FAIL: Super admin got HTTP {resp.status_code} for {endpoint}", "FAIL")
            record_test("J_Regression", f"J_super_admin_access_{endpoint.replace('/', '_')}", False,
                       f"HTTP {resp.status_code}")


def print_summary():
    """Print test summary"""
    log("\n" + "=" * 80, "SECTION")
    log("TEST SUMMARY", "SECTION")
    log("=" * 80, "SECTION")
    
    total = test_results["total"]
    passed = test_results["passed"]
    failed = test_results["failed"]
    
    log(f"\nTotal Tests: {total}")
    log(f"Passed: {passed} ({100*passed//total if total > 0 else 0}%)", "PASS")
    log(f"Failed: {failed} ({100*failed//total if total > 0 else 0}%)", "FAIL" if failed > 0 else "INFO")
    
    log("\n--- Results by Section ---")
    for section, data in test_results["sections"].items():
        section_total = data["passed"] + data["failed"]
        log(f"\n{section}: {data['passed']}/{section_total} passed")
        
        if data["failed"] > 0:
            log(f"  Failed tests:")
            for test in data["tests"]:
                if not test["passed"]:
                    log(f"    ❌ {test['name']}: {test['details']}")
    
    # Overall result
    log("\n" + "=" * 80)
    if failed == 0:
        log("✅ ALL TESTS PASSED - SECURITY VERIFICATION COMPLETE", "PASS")
    else:
        log(f"❌ {failed} TEST(S) FAILED - REVIEW REQUIRED", "FAIL")
    log("=" * 80)


def main():
    """Main test execution"""
    log("=" * 80, "SECTION")
    log("CARGO Phase 2B Backend Security Verification", "SECTION")
    log("Testing RBAC Authorization Matrix + Privilege Escalation + Object Isolation", "SECTION")
    log("=" * 80, "SECTION")
    log(f"Backend URL: {API_BASE}\n")
    
    try:
        section_a_authenticate_and_identify()
        section_b_create_disposable_admins()
        section_c_authorization_matrix()
        section_d_self_protection()
        section_e_last_super_admin_protection()
        section_f_privilege_escalation()
        section_g_super_admin_can_manage_normal_staff()
        section_h_provider_model()
        section_i_object_level_isolation()
        section_j_regression_super_admin_access()
        
        print_summary()
        
        # Exit with appropriate code
        sys.exit(0 if test_results["failed"] == 0 else 1)
        
    except KeyboardInterrupt:
        log("\n\nTest interrupted by user", "WARN")
        sys.exit(1)
    except Exception as e:
        log(f"\n\nFATAL ERROR: {e}", "FAIL")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
