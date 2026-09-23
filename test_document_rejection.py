#!/usr/bin/env python3
"""Test document rejection"""
import requests
import json

BASE_URL = "https://hardened-cargo.preview.emergentagent.com/api"

# Login as driver to upload a document
resp = requests.post(f"{BASE_URL}/auth/otp/request", json={
    "phone": "+96890000002",
    "role": "driver"
})
demo_code = resp.json().get("demo_code")
resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
    "phone": "+96890000002",
    "role": "driver",
    "code": demo_code
})
driver_token = resp.json()["token"]
driver_headers = {"Authorization": f"Bearer {driver_token}"}

print("Uploading a new document as driver...")
resp = requests.post(f"{BASE_URL}/documents", headers=driver_headers, json={
    "doc_type_key": "health_certificate",
    "reference": "HC-TEST-001",
    "expiry": "2027-12-31"
})
print(f"Upload status: {resp.status_code}")
if resp.status_code == 200:
    doc_id = resp.json()["id"]
    print(f"Document ID: {doc_id}")
    
    # Login as document reviewer
    resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
        "email": "docrev_p4_1789745103@cargo.om",
        "password": "test12345"
    })
    if resp.status_code == 200:
        docrev_token = resp.json()["token"]
        docrev_headers = {"Authorization": f"Bearer {docrev_token}"}
        
        print("\nRejecting document as document reviewer...")
        resp = requests.post(f"{BASE_URL}/admin/documents/{doc_id}/review", 
                            headers=docrev_headers, json={
                                "action": "reject",
                                "reason": "Document quality insufficient for testing"
                            })
        print(f"Rejection status: {resp.status_code}")
        if resp.status_code == 200:
            doc = resp.json()
            print(f"Document status: {doc.get('status')}")
            print(f"Rejection reason: {doc.get('rejection_reason')}")
            
            # Check audit log
            resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
                "email": "admin@cargo.om",
                "password": "admin123"
            })
            super_token = resp.json()["token"]
            super_headers = {"Authorization": f"Bearer {super_token}"}
            
            resp = requests.get(f"{BASE_URL}/admin/audit-logs", headers=super_headers)
            if resp.status_code == 200:
                logs = resp.json()
                reject_logs = [l for l in logs if l.get("action") == "DOCUMENT_REJECTED"]
                print(f"\nFound {len(reject_logs)} DOCUMENT_REJECTED audit log entries")
                if len(reject_logs) > 0:
                    latest = reject_logs[0]
                    print(f"Latest rejection:")
                    print(f"  - Entity ID: {latest.get('entity_id')}")
                    print(f"  - Old status: {latest.get('old_value', {}).get('status')}")
                    print(f"  - New status: {latest.get('new_value', {}).get('status')}")
                    print(f"  - Reason: {latest.get('reason')}")
                    print(f"  - Actor: {latest.get('actor_name')}")
