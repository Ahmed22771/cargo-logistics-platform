#!/usr/bin/env python3
"""Quick test to check last super admin protection details"""
import requests
import json

BASE_URL = "https://cargo-readiness-om.preview.emergentagent.com/api"

# Login as super admin
resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
    "email": "admin@cargo.om",
    "password": "admin123"
})
token = resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Get current super admin ID
resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
original_id = resp.json()["id"]
print(f"Original super admin ID: {original_id}")

# Count active super admins
resp = requests.get(f"{BASE_URL}/admin/users?role=admin", headers=headers)
admins = resp.json()
super_admins = [a for a in admins if a.get("admin_role_key") == "super_admin"]
active_super_admins = [a for a in super_admins if a.get("status", "active") == "active"]
print(f"\nTotal super admins: {len(super_admins)}")
print(f"Active super admins: {len(active_super_admins)}")
for sa in active_super_admins:
    print(f"  - {sa.get('name')} ({sa.get('email')}) - status: {sa.get('status', 'active')}")

# Try to suspend the original when there's only 1 active
if len(active_super_admins) == 1:
    print(f"\n\nAttempting to suspend the ONLY active super admin...")
    resp = requests.post(f"{BASE_URL}/admin/users/{original_id}/suspend", 
                        headers=headers, json={"reason": "test"})
    print(f"Status code: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
