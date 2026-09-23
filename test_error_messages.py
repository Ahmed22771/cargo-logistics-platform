#!/usr/bin/env python3
"""Check exact error messages"""
import requests
import json

BASE_URL = "https://hardened-cargo.preview.emergentagent.com/api"

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

print("TEST 1: Try to suspend self")
resp = requests.post(f"{BASE_URL}/admin/users/{original_id}/suspend", 
                    headers=headers, json={"reason": "test"})
print(f"Status: {resp.status_code}")
print(f"Detail: {resp.json().get('detail')}")
print()

# Now suspend all other super admins to make this the last one
resp = requests.get(f"{BASE_URL}/admin/users?role=admin", headers=headers)
admins = resp.json()
super_admins = [a for a in admins if a.get("admin_role_key") == "super_admin" and a["id"] != original_id]

print(f"Found {len(super_admins)} other super admins")
for sa in super_admins:
    if sa.get("status", "active") == "active":
        print(f"Suspending {sa.get('name')}...")
        resp = requests.post(f"{BASE_URL}/admin/users/{sa['id']}/suspend", 
                            headers=headers, json={"reason": "test"})
        print(f"  Status: {resp.status_code}")

print("\nTEST 2: Try to suspend last super admin (self)")
resp = requests.post(f"{BASE_URL}/admin/users/{original_id}/suspend", 
                    headers=headers, json={"reason": "test"})
print(f"Status: {resp.status_code}")
print(f"Detail: {resp.json().get('detail')}")
print()

# Reactivate others
for sa in super_admins:
    resp = requests.post(f"{BASE_URL}/admin/users/{sa['id']}/activate", headers=headers)
    print(f"Reactivated {sa.get('name')}: {resp.status_code}")
