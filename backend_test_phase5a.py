#!/usr/bin/env python3
"""
Phase 5A Backend Testing — POD requirement + confirm-to-COMPLETED + dispute + lazy auto-completion
"""
import os
import sys
import requests
import json
from datetime import datetime, timedelta, timezone

BASE_URL = os.getenv("REACT_APP_BACKEND_URL", "https://hardened-cargo.preview.emergentagent.com")
API_BASE = f"{BASE_URL}/api"

# Test credentials
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"
CUSTOMER_PHONE = "+96890000001"
DRIVER_PHONE = "+96890000002"
DRIVER2_PHONE = "+96890000003"

# POD photo (1x1 transparent PNG)
POD_PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def log(msg):
    print(f"[TEST] {msg}")

def login_customer():
    r = requests.post(f"{API_BASE}/auth/otp/request", json={"phone": CUSTOMER_PHONE, "role": "customer"})
    assert r.status_code == 200, f"OTP request failed: {r.status_code} {r.text}"
    code = r.json()["demo_code"]
    r = requests.post(f"{API_BASE}/auth/otp/verify", json={"phone": CUSTOMER_PHONE, "code": code, "role": "customer"})
    assert r.status_code == 200, f"OTP verify failed: {r.status_code} {r.text}"
    return r.json()["token"]

def login_driver(phone=DRIVER_PHONE):
    r = requests.post(f"{API_BASE}/auth/otp/request", json={"phone": phone, "role": "driver"})
    assert r.status_code == 200, f"Driver OTP request failed: {r.status_code} {r.text}"
    code = r.json()["demo_code"]
    r = requests.post(f"{API_BASE}/auth/otp/verify", json={"phone": phone, "code": code, "role": "driver"})
    assert r.status_code == 200, f"Driver OTP verify failed: {r.status_code} {r.text}"
    return r.json()["token"]

def login_admin():
    r = requests.post(f"{API_BASE}/auth/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]

def create_shipment(token):
    """Create and publish a shipment as customer."""
    payload = {
        "title": f"Phase5A Test Shipment {datetime.now().isoformat()}",
        "category": "general",
        "weight": "50",
        "pickup_location": {"address": "Muscat", "lat": 23.5880, "lng": 58.3829, "city": "Muscat", "country": "Oman"},
        "delivery_location": {"address": "Salalah", "lat": 17.0150, "lng": 54.0924, "city": "Salalah", "country": "Oman"},
        "status": "DRAFT"
    }
    r = requests.post(f"{API_BASE}/shipments", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Create shipment failed: {r.status_code} {r.text}"
    sid = r.json()["id"]
    r = requests.post(f"{API_BASE}/shipments/{sid}/publish", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Publish shipment failed: {r.status_code} {r.text}"
    return sid

def submit_bid(sid, driver_token, price=30):
    """Driver submits a bid."""
    r = requests.post(f"{API_BASE}/shipments/{sid}/bids", json={"price": price}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 200, f"Submit bid failed: {r.status_code} {r.text}"
    return r.json()["id"]

def accept_bid(bid_id, customer_token):
    """Customer accepts bid, creates trip."""
    r = requests.post(f"{API_BASE}/bids/{bid_id}/accept", headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"Accept bid failed: {r.status_code} {r.text}"
    return r.json()["id"]

def advance_trip_to_arrived_destination(trip_id, driver_token):
    """Walk trip through linear flow to DRIVER_ARRIVED_DESTINATION."""
    states = ["DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "LOADING", "LOADED", "IN_TRANSIT", "NEAR_DESTINATION", "DRIVER_ARRIVED_DESTINATION"]
    for state in states:
        r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": state}, headers={"Authorization": f"Bearer {driver_token}"})
        assert r.status_code == 200, f"Advance to {state} failed: {r.status_code} {r.text}"
    return True

def run_section_a():
    """A) HAPPY PATH — POD + CONFIRM → COMPLETED + LEDGER"""
    log("=== SECTION A: HAPPY PATH ===")
    customer_token = login_customer()
    driver_token = login_driver()
    
    # A1-A3: Create shipment, bid, accept
    sid = create_shipment(customer_token)
    bid_id = submit_bid(sid, driver_token)
    trip_id = accept_bid(bid_id, customer_token)
    log(f"A1-A3: Created trip {trip_id}")
    
    # A4: Advance to DRIVER_ARRIVED_DESTINATION
    advance_trip_to_arrived_destination(trip_id, driver_token)
    log("A4: Advanced to DRIVER_ARRIVED_DESTINATION")
    
    # A5: POD REQUIRED — no pod_photo
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "DELIVERED_PENDING_CONFIRMATION"}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 400, f"A5: Expected 400, got {r.status_code}"
    assert r.json()["detail"] == "POD_REQUIRED", f"A5: Expected POD_REQUIRED, got {r.json()['detail']}"
    log("A5: ✅ POD_REQUIRED enforced (no pod_photo)")
    
    # A6: With pod_photo
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={
        "status": "DELIVERED_PENDING_CONFIRMATION",
        "pod_photo": POD_PHOTO,
        "pod_notes": "Delivered to Ahmed at front gate"
    }, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 200, f"A6: POD submission failed: {r.status_code} {r.text}"
    trip = r.json()
    assert trip["status"] == "DELIVERED_PENDING_CONFIRMATION", f"A6: Expected DELIVERED_PENDING_CONFIRMATION, got {trip['status']}"
    assert "delivery_proof" in trip, "A6: delivery_proof missing"
    assert trip["delivery_proof"]["photo"] == POD_PHOTO, "A6: POD photo mismatch"
    assert trip["delivery_proof"]["notes"] == "Delivered to Ahmed at front gate", "A6: POD notes mismatch"
    log("A6: ✅ POD submitted successfully")
    
    # A7: Customer confirm → COMPLETED
    r = requests.post(f"{API_BASE}/trips/{trip_id}/confirm-delivery", json={
        "reference": "",
        "delivered_to_name": "Ahmed"
    }, headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"A7: Confirm delivery failed: {r.status_code} {r.text}"
    trip = r.json()
    assert trip["status"] == "COMPLETED", f"A7: Expected COMPLETED, got {trip['status']}"
    assert trip["customer_confirmed"] == True, "A7: customer_confirmed not True"
    assert "completed_at" in trip, "A7: completed_at missing"
    log("A7: ✅ Customer confirm → COMPLETED")
    
    # A8: LEDGER — 3 transactions (idempotent)
    admin_token = login_admin()
    r = requests.get(f"{API_BASE}/admin/finance/transactions?trip_id={trip_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"A8: Get transactions failed: {r.status_code} {r.text}"
    txns = r.json()
    # Filter to only this trip's transactions
    trip_txns = [t for t in txns if t.get("trip_id") == trip_id]
    if len(trip_txns) != 3:
        log(f"A8: DEBUG - Found {len(trip_txns)} transactions for trip {trip_id}")
        for t in trip_txns:
            log(f"  - {t['type']}: {t['amount']} {t.get('currency', 'OMR')}")
    assert len(trip_txns) == 3, f"A8: Expected 3 transactions, got {len(trip_txns)}"
    types = {t["type"] for t in trip_txns}
    assert types == {"customer_payment", "platform_commission", "driver_earning"}, f"A8: Transaction types mismatch: {types}"
    log("A8: ✅ Ledger created (3 transactions, idempotent)")
    
    # A9: Rating still works after COMPLETED
    r = requests.post(f"{API_BASE}/trips/{trip_id}/review", json={
        "overall": 5,
        "service_quality": 5,
        "communication": 5,
        "on_time": 5,
        "comment": "good"
    }, headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"A9: Review failed: {r.status_code} {r.text}"
    log("A9: ✅ Rating works after COMPLETED")
    
    # A10: Audit log
    r = requests.get(f"{API_BASE}/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"A10: Get audit logs failed: {r.status_code} {r.text}"
    logs = r.json()
    pod_log = [l for l in logs if l["action"] == "TRIP_POD_SUBMITTED" and l["entity_id"] == trip_id]
    confirm_log = [l for l in logs if l["action"] == "TRIP_DELIVERY_CONFIRMED" and l["entity_id"] == trip_id]
    assert len(pod_log) > 0, "A10: TRIP_POD_SUBMITTED audit log missing"
    assert len(confirm_log) > 0, "A10: TRIP_DELIVERY_CONFIRMED audit log missing"
    log("A10: ✅ Audit log entries present")
    
    log("=== SECTION A: ALL TESTS PASSED ===\n")
    return trip_id

def run_section_b():
    """B) POD REJECTION EDGE CASES"""
    log("=== SECTION B: POD REJECTION EDGE CASES ===")
    customer_token = login_customer()
    driver_token = login_driver()
    
    # B1: Create fresh trip
    sid = create_shipment(customer_token)
    bid_id = submit_bid(sid, driver_token)
    trip_id = accept_bid(bid_id, customer_token)
    advance_trip_to_arrived_destination(trip_id, driver_token)
    log("B1: Created fresh trip")
    
    # B2: No pod_photo, no pod_notes
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "DELIVERED_PENDING_CONFIRMATION"}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 400, f"B2: Expected 400, got {r.status_code}"
    assert r.json()["detail"] == "POD_REQUIRED", f"B2: Expected POD_REQUIRED, got {r.json()['detail']}"
    log("B2: ✅ POD_REQUIRED (no pod_photo, no pod_notes)")
    
    # B3: Empty string pod_photo
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "DELIVERED_PENDING_CONFIRMATION", "pod_photo": ""}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 400, f"B3: Expected 400, got {r.status_code}"
    assert r.json()["detail"] == "POD_REQUIRED", f"B3: Expected POD_REQUIRED, got {r.json()['detail']}"
    log("B3: ✅ POD_REQUIRED (empty string)")
    
    # B4: Whitespace only pod_photo
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "DELIVERED_PENDING_CONFIRMATION", "pod_photo": "   "}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 400, f"B4: Expected 400, got {r.status_code}"
    assert r.json()["detail"] == "POD_REQUIRED", f"B4: Expected POD_REQUIRED, got {r.json()['detail']}"
    log("B4: ✅ POD_REQUIRED (whitespace only)")
    
    # B5: Valid pod_photo
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "DELIVERED_PENDING_CONFIRMATION", "pod_photo": POD_PHOTO}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 200, f"B5: POD submission failed: {r.status_code} {r.text}"
    log("B5: ✅ Valid POD accepted")
    
    # B5 continued: Attempting again
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "DELIVERED_PENDING_CONFIRMATION", "pod_photo": POD_PHOTO}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 400, f"B5: Expected 400 for duplicate POD, got {r.status_code}"
    assert r.json()["detail"] in ["INVALID_TRIP_TRANSITION", "TRIP_IN_TERMINAL_STATE"], f"B5: Unexpected error: {r.json()['detail']}"
    log("B5: ✅ Duplicate POD rejected")
    
    log("=== SECTION B: ALL TESTS PASSED ===\n")

def run_section_c():
    """C) DISPUTE PATH"""
    log("=== SECTION C: DISPUTE PATH ===")
    customer_token = login_customer()
    driver_token = login_driver(DRIVER2_PHONE)  # Use different driver to avoid conflicts
    admin_token = login_admin()
    
    # C1: Create trip with POD
    sid = create_shipment(customer_token)
    bid_id = submit_bid(sid, driver_token, price=35)
    trip_id = accept_bid(bid_id, customer_token)
    advance_trip_to_arrived_destination(trip_id, driver_token)
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "DELIVERED_PENDING_CONFIRMATION", "pod_photo": POD_PHOTO}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 200, f"C1: POD submission failed: {r.status_code} {r.text}"
    log("C1: Created trip with POD")
    
    # C2: Empty reason
    r = requests.post(f"{API_BASE}/trips/{trip_id}/dispute", json={"reason": ""}, headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 400, f"C2: Expected 400, got {r.status_code}"
    assert r.json()["detail"] == "DISPUTE_REASON_REQUIRED", f"C2: Expected DISPUTE_REASON_REQUIRED, got {r.json()['detail']}"
    log("C2: ✅ DISPUTE_REASON_REQUIRED enforced")
    
    # C3: Valid dispute
    r = requests.post(f"{API_BASE}/trips/{trip_id}/dispute", json={"reason": "Cargo damaged on arrival", "notes": "Broken box"}, headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"C3: Dispute failed: {r.status_code} {r.text}"
    trip = r.json()
    assert trip["status"] == "DISPUTED", f"C3: Expected DISPUTED, got {trip['status']}"
    assert "dispute" in trip, "C3: dispute field missing"
    assert trip["dispute"]["reason"] == "Cargo damaged on arrival", "C3: Dispute reason mismatch"
    log("C3: ✅ Dispute created")
    
    # C4: Shipment status now DISPUTED
    r = requests.get(f"{API_BASE}/shipments/{sid}", headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"C4: Get shipment failed: {r.status_code} {r.text}"
    assert r.json()["status"] == "DISPUTED", f"C4: Expected shipment status DISPUTED, got {r.json()['status']}"
    log("C4: ✅ Shipment status DISPUTED")
    
    # C5: Ledger NOT triggered
    r = requests.get(f"{API_BASE}/admin/finance/transactions?trip_id={trip_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"C5: Get transactions failed: {r.status_code} {r.text}"
    txns = r.json()
    # Filter to only this trip's transactions
    trip_txns = [t for t in txns if t.get("trip_id") == trip_id]
    if len(trip_txns) != 0:
        log(f"C5: DEBUG - Found {len(trip_txns)} transactions for disputed trip {trip_id}")
        for t in trip_txns:
            log(f"  - {t['type']}: {t['amount']} {t.get('currency', 'OMR')}")
    assert len(trip_txns) == 0, f"C5: Expected 0 transactions for disputed trip, got {len(trip_txns)}"
    log("C5: ✅ Ledger NOT triggered for disputed trip")
    
    # C6: Post-dispute rejection
    # Driver cannot advance
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "COMPLETED"}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 400, f"C6: Expected 400, got {r.status_code}"
    assert r.json()["detail"] == "TRIP_IN_TERMINAL_STATE", f"C6: Expected TRIP_IN_TERMINAL_STATE, got {r.json()['detail']}"
    # Customer cannot confirm
    r = requests.post(f"{API_BASE}/trips/{trip_id}/confirm-delivery", json={}, headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 400, f"C6: Expected 400 for confirm after dispute, got {r.status_code}"
    # Customer cannot dispute again
    r = requests.post(f"{API_BASE}/trips/{trip_id}/dispute", json={"reason": "Another reason"}, headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code in [400, 409], f"C6: Expected 400/409 for duplicate dispute, got {r.status_code}"
    log("C6: ✅ Post-dispute actions blocked")
    
    # C7: Audit log
    r = requests.get(f"{API_BASE}/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"C7: Get audit logs failed: {r.status_code} {r.text}"
    logs = r.json()
    dispute_log = [l for l in logs if l["action"] == "TRIP_DISPUTED" and l["entity_id"] == trip_id]
    assert len(dispute_log) > 0, "C7: TRIP_DISPUTED audit log missing"
    assert dispute_log[0]["reason"] == "Cargo damaged on arrival", "C7: Dispute reason in audit log mismatch"
    log("C7: ✅ Audit log contains TRIP_DISPUTED")
    
    # C8: Admin notification
    r = requests.get(f"{API_BASE}/notifications", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"C8: Get notifications failed: {r.status_code} {r.text}"
    notifs = r.json()
    dispute_notif = [n for n in notifs if n["type"] == "trip_disputed" and n.get("meta", {}).get("trip_id") == trip_id]
    assert len(dispute_notif) > 0, "C8: Admin notification for dispute missing"
    log("C8: ✅ Admin notification for dispute present")
    
    log("=== SECTION C: ALL TESTS PASSED ===\n")

def run_section_d():
    """D) LAZY AUTO-COMPLETION"""
    log("=== SECTION D: LAZY AUTO-COMPLETION ===")
    customer_token = login_customer()
    driver_token = login_driver()
    admin_token = login_admin()
    
    # D1: Create trip with POD
    sid = create_shipment(customer_token)
    bid_id = submit_bid(sid, driver_token)
    trip_id = accept_bid(bid_id, customer_token)
    advance_trip_to_arrived_destination(trip_id, driver_token)
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "DELIVERED_PENDING_CONFIRMATION", "pod_photo": POD_PHOTO}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 200, f"D1: POD submission failed: {r.status_code} {r.text}"
    log("D1: Created trip with POD")
    
    # D2: Simulate stale trip by patching delivered_pending_at to 3 days ago
    import subprocess
    stale_date = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    mongo_cmd = f'db.trips.updateOne({{id:"{trip_id}"}},{{$set:{{delivered_pending_at:"{stale_date}"}}}});'
    result = subprocess.run(
        ["mongosh", "mongodb://localhost:27017/cargo_db", "--quiet", "--eval", mongo_cmd],
        capture_output=True, text=True
    )
    log(f"D2: Patched delivered_pending_at to {stale_date}")
    
    # D2 continued: GET /trips/{id} should auto-complete
    r = requests.get(f"{API_BASE}/trips/{trip_id}", headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"D2: Get trip failed: {r.status_code} {r.text}"
    trip = r.json()
    assert trip["status"] == "COMPLETED", f"D2: Expected COMPLETED, got {trip['status']}"
    assert trip.get("auto_completed") == True, f"D2: Expected auto_completed=True, got {trip.get('auto_completed')}"
    log("D2: ✅ Lazy auto-completion triggered")
    
    # D3: Ledger fired
    r = requests.get(f"{API_BASE}/admin/finance/transactions?trip_id={trip_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"D3: Get transactions failed: {r.status_code} {r.text}"
    txns = r.json()
    # Filter to only this trip's transactions
    trip_txns = [t for t in txns if t.get("trip_id") == trip_id]
    assert len(trip_txns) == 3, f"D3: Expected 3 transactions, got {len(trip_txns)}"
    log("D3: ✅ Ledger fired for auto-completed trip")
    
    # D4: Audit log
    r = requests.get(f"{API_BASE}/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"D4: Get audit logs failed: {r.status_code} {r.text}"
    logs = r.json()
    auto_log = [l for l in logs if l["action"] == "TRIP_AUTO_COMPLETED" and l["entity_id"] == trip_id]
    assert len(auto_log) > 0, "D4: TRIP_AUTO_COMPLETED audit log missing"
    assert "elapsed_hours" in auto_log[0]["new_value"], "D4: elapsed_hours missing in audit log"
    log("D4: ✅ Audit log contains TRIP_AUTO_COMPLETED")
    
    # D5: Customer notification
    r = requests.get(f"{API_BASE}/notifications", headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"D5: Get notifications failed: {r.status_code} {r.text}"
    notifs = r.json()
    auto_notif = [n for n in notifs if n["type"] == "trip_auto_completed" and n.get("meta", {}).get("trip_id") == trip_id]
    assert len(auto_notif) > 0, "D5: Customer notification for auto-completion missing"
    log("D5: ✅ Customer notification for auto-completion present")
    
    # D6: Fresh trip NOT auto-completed
    sid2 = create_shipment(customer_token)
    bid_id2 = submit_bid(sid2, driver_token)
    trip_id2 = accept_bid(bid_id2, customer_token)
    advance_trip_to_arrived_destination(trip_id2, driver_token)
    r = requests.post(f"{API_BASE}/trips/{trip_id2}/status", json={"status": "DELIVERED_PENDING_CONFIRMATION", "pod_photo": POD_PHOTO}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 200, f"D6: POD submission failed: {r.status_code} {r.text}"
    r = requests.get(f"{API_BASE}/trips/{trip_id2}", headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"D6: Get trip failed: {r.status_code} {r.text}"
    trip2 = r.json()
    assert trip2["status"] == "DELIVERED_PENDING_CONFIRMATION", f"D6: Expected DELIVERED_PENDING_CONFIRMATION, got {trip2['status']}"
    log("D6: ✅ Fresh trip NOT auto-completed")
    
    log("=== SECTION D: ALL TESTS PASSED ===\n")

def run_section_e():
    """E) AUTHORIZATION"""
    log("=== SECTION E: AUTHORIZATION ===")
    customer1_token = login_customer()
    driver1_token = login_driver()
    driver2_token = login_driver(DRIVER2_PHONE)
    
    # E1: Create trip A owned by customer1 + driver1
    sid = create_shipment(customer1_token)
    bid_id = submit_bid(sid, driver1_token)
    trip_id = accept_bid(bid_id, customer1_token)
    advance_trip_to_arrived_destination(trip_id, driver1_token)
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "DELIVERED_PENDING_CONFIRMATION", "pod_photo": POD_PHOTO}, headers={"Authorization": f"Bearer {driver1_token}"})
    assert r.status_code == 200, f"E1: POD submission failed: {r.status_code} {r.text}"
    log("E1: Created trip A")
    
    # E1 continued: Create customer2 (use a new phone number)
    customer2_phone = "+96890099999"
    r = requests.post(f"{API_BASE}/auth/otp/request", json={"phone": customer2_phone, "role": "customer", "name": "Test Customer 2"})
    if r.status_code == 200:
        code = r.json()["demo_code"]
        r = requests.post(f"{API_BASE}/auth/otp/verify", json={"phone": customer2_phone, "code": code, "role": "customer", "name": "Test Customer 2"})
        assert r.status_code == 200, f"E1: Customer2 OTP verify failed: {r.status_code} {r.text}"
        customer2_token = r.json()["token"]
        
        # Customer2 tries to confirm trip A
        r = requests.post(f"{API_BASE}/trips/{trip_id}/confirm-delivery", json={}, headers={"Authorization": f"Bearer {customer2_token}"})
        assert r.status_code == 404, f"E1: Expected 404 for customer2 confirm, got {r.status_code}"
        
        # Customer2 tries to dispute trip A
        r = requests.post(f"{API_BASE}/trips/{trip_id}/dispute", json={"reason": "test"}, headers={"Authorization": f"Bearer {customer2_token}"})
        assert r.status_code == 404, f"E1: Expected 404 for customer2 dispute, got {r.status_code}"
        
        # Customer2 tries to GET trip A
        r = requests.get(f"{API_BASE}/trips/{trip_id}", headers={"Authorization": f"Bearer {customer2_token}"})
        assert r.status_code == 404, f"E1: Expected 404 for customer2 GET trip, got {r.status_code}"
        log("E1: ✅ Customer2 authorization checks passed")
    else:
        log("E1: ⚠️ Customer2 creation skipped (OTP request failed)")
    
    # E2: Driver2 tries to update trip A
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "COMPLETED", "pod_photo": POD_PHOTO}, headers={"Authorization": f"Bearer {driver2_token}"})
    assert r.status_code == 404, f"E2: Expected 404 for driver2 status update, got {r.status_code}"
    log("E2: ✅ Driver2 authorization check passed")
    
    # E3: Driver tries to dispute (customer-only endpoint)
    r = requests.post(f"{API_BASE}/trips/{trip_id}/dispute", json={"reason": "test"}, headers={"Authorization": f"Bearer {driver1_token}"})
    assert r.status_code == 403, f"E3: Expected 403 for driver dispute, got {r.status_code}"
    log("E3: ✅ Driver cannot dispute (customer-only)")
    
    # E4: Customer tries to update status (driver-only endpoint)
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "COMPLETED"}, headers={"Authorization": f"Bearer {customer1_token}"})
    assert r.status_code == 403, f"E4: Expected 403 for customer status update, got {r.status_code}"
    log("E4: ✅ Customer cannot update status (driver-only)")
    
    log("=== SECTION E: ALL TESTS PASSED ===\n")

def run_section_f():
    """F) LEGACY / BACKWARDS COMPAT"""
    log("=== SECTION F: LEGACY / BACKWARDS COMPAT ===")
    admin_token = login_admin()
    customer_token = login_customer()
    driver_token = login_driver()
    
    # F1: Legacy trips with status=DELIVERED (not tested, just note)
    log("F1: ⚠️ Legacy DELIVERED trips not tested (no legacy data in test environment)")
    
    # F2: All existing admin endpoints still 200
    endpoints = [
        "/admin/stats",
        "/admin/shipments",
        "/admin/bids",
        "/admin/trips",
        "/admin/finance/stats",
        "/admin/finance/transactions",
        "/admin/roles",
        "/admin/audit-logs",
        "/admin/documents"
    ]
    for ep in endpoints:
        r = requests.get(f"{API_BASE}{ep}", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200, f"F2: {ep} failed: {r.status_code} {r.text}"
    log("F2: ✅ All admin endpoints return 200")
    
    # F3: Existing OTP + admin login still 200
    r = requests.post(f"{API_BASE}/auth/otp/request", json={"phone": CUSTOMER_PHONE, "role": "customer"})
    assert r.status_code == 200, f"F3: Customer OTP request failed: {r.status_code} {r.text}"
    r = requests.post(f"{API_BASE}/auth/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"F3: Admin login failed: {r.status_code} {r.text}"
    log("F3: ✅ OTP + admin login still working")
    
    # F4: Existing shipment creation, publishing, bidding, acceptance flow still 200
    sid = create_shipment(customer_token)
    bid_id = submit_bid(sid, driver_token)
    trip_id = accept_bid(bid_id, customer_token)
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status", json={"status": "DRIVER_EN_ROUTE"}, headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 200, f"F4: Trip status update failed: {r.status_code} {r.text}"
    log("F4: ✅ Shipment/bid/trip flow still working")
    
    log("=== SECTION F: ALL TESTS PASSED ===\n")

def main():
    log("Starting Phase 5A Backend Testing...")
    log(f"Base URL: {BASE_URL}")
    log(f"API Base: {API_BASE}\n")
    
    try:
        run_section_a()
        run_section_b()
        run_section_c()
        run_section_d()
        run_section_e()
        run_section_f()
        
        log("\n" + "="*60)
        log("✅ ALL PHASE 5A BACKEND TESTS PASSED")
        log("="*60)
        return 0
    except AssertionError as e:
        log(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        log(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
