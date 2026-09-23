#!/usr/bin/env python3
"""
Phase 2B Backend Testing — Critical dispute/payment safety + super_admin authorization protection

Test Scope:
A) Real dispute flow: shipment→bid→accept→pay HELD→trip advance→POD→dispute
   - Verify trip.status=DISPUTED, shipment.status=DISPUTED
   - Verify payment_status=HELD (not settled)
   - Verify payment_hold remains HELD
   - Verify ZERO settlement transactions (customer_payment/platform_commission/driver_earning)
   - Verify trip never becomes COMPLETED
   - Verify rating/review blocked
   - Verify driver + all admins receive trip_disputed notifications

B) Disputed blocking/idempotency:
   - Duplicate dispute → reject
   - Customer confirm-delivery → reject
   - Customer review → reject
   - Driver status update → reject
   - GET trip/mine (lazy auto-completion) → no change
   - Verify status stays DISPUTED, shipment stays DISPUTED, payment stays HELD
   - Verify ledger stays with no final settlement
   - Verify duplicate payment/dispute/confirm attempts don't create duplicates

C) Separate normal flow: shipment→bid→accept→pay→trip→POD→confirm
   - Verify COMPLETED, shipment COMPLETED
   - Verify exactly one customer_payment, one platform_commission, one driver_earning
   - Verify payment hold is not duplicated
   - Verify repeat confirm/review/completion attempts don't duplicate transactions
   - Verify rating behavior for completed trips
   - Verify settlement is idempotent

D) Super_admin protection:
   - Identify seeded super_admin id
   - Create disposable platform manager, supervisor (if model supports)
   - Test authorization boundaries:
     * PUT /api/admin/users/{super_admin_id} → 403
     * POST /api/admin/users/{super_admin_id}/reset-password → 403
     * POST /api/admin/users/{super_admin_id}/status disable → 403
     * POST /api/admin/users/{super_admin_id}/suspend → 403
     * POST /api/admin/users/{super_admin_id}/activate → 403
     * PUT /api/admin/admins/{super_admin_id}/role → 403
     * POST /api/admin/admins with admin_role_key=super_admin → 403
     * PUT /api/admin/users/{id} with admin_role_key=super_admin → 403
   - Verify super_admin remains unchanged
   - Verify last super_admin protection
   - Verify legitimate super_admin access still works
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
PROVIDER_PHONE = "+96890000005"

# POD photo (1x1 transparent PNG)
POD_PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "failures": []
}

def log(msg):
    print(f"[TEST] {msg}")

def assert_test(condition, message):
    test_results["total"] += 1
    if condition:
        test_results["passed"] += 1
        log(f"✅ PASS: {message}")
    else:
        test_results["failed"] += 1
        test_results["failures"].append(message)
        log(f"❌ FAIL: {message}")

def login_customer():
    r = requests.post(f"{API_BASE}/auth/otp/request", json={"phone": CUSTOMER_PHONE, "role": "customer"})
    assert r.status_code == 200, f"Customer OTP request failed: {r.status_code} {r.text}"
    code = r.json()["demo_code"]
    r = requests.post(f"{API_BASE}/auth/otp/verify", json={"phone": CUSTOMER_PHONE, "code": code, "role": "customer"})
    assert r.status_code == 200, f"Customer OTP verify failed: {r.status_code} {r.text}"
    return r.json()["token"]

def login_driver():
    r = requests.post(f"{API_BASE}/auth/otp/request", json={"phone": DRIVER_PHONE, "role": "driver"})
    assert r.status_code == 200, f"Driver OTP request failed: {r.status_code} {r.text}"
    code = r.json()["demo_code"]
    r = requests.post(f"{API_BASE}/auth/otp/verify", json={"phone": DRIVER_PHONE, "code": code, "role": "driver"})
    assert r.status_code == 200, f"Driver OTP verify failed: {r.status_code} {r.text}"
    return r.json()["token"]

def login_admin():
    r = requests.post(f"{API_BASE}/auth/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]

def create_and_publish_shipment(customer_token):
    """Create and publish a shipment."""
    payload = {
        "title": f"Test Shipment {datetime.now().isoformat()}",
        "description": "Test shipment for Phase 2B testing",
        "category": "general",
        "weight": "10",
        "dimensions": "10x10x10",
        "pickup_location": {
            "address": "Muscat, Oman",
            "lat": 23.5880,
            "lng": 58.3829,
            "city": "Muscat",
            "area": "Muscat",
            "country": "Oman"
        },
        "delivery_location": {
            "address": "Salalah, Oman",
            "lat": 17.0150,
            "lng": 54.0924,
            "city": "Salalah",
            "area": "Dhofar",
            "country": "Oman"
        },
        "pickup_date": (datetime.now() + timedelta(days=1)).isoformat(),
        "status": "PUBLISHED"
    }
    r = requests.post(f"{API_BASE}/shipments", json=payload, headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"Shipment creation failed: {r.status_code} {r.text}"
    return r.json()["id"]

def submit_bid(driver_token, shipment_id, price=30.0):
    """Driver submits a bid."""
    r = requests.post(f"{API_BASE}/shipments/{shipment_id}/bids", 
                     json={"price": price, "note": "Test bid"},
                     headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 200, f"Bid submission failed: {r.status_code} {r.text}"
    return r.json()["id"]

def accept_bid(customer_token, bid_id):
    """Customer accepts a bid."""
    r = requests.post(f"{API_BASE}/bids/{bid_id}/accept",
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"Bid acceptance failed: {r.status_code} {r.text}"
    return r.json()["id"]

def pay_trip(customer_token, trip_id):
    """Customer pays for the trip (demo payment)."""
    r = requests.post(f"{API_BASE}/trips/{trip_id}/pay",
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert r.status_code == 200, f"Trip payment failed: {r.status_code} {r.text}"
    return r.json()

def advance_trip_to_pod(driver_token, trip_id):
    """Advance trip through all states to DRIVER_ARRIVED_DESTINATION."""
    states = [
        "DRIVER_EN_ROUTE",
        "DRIVER_ARRIVED",
        "LOADING",
        "LOADED",
        "IN_TRANSIT",
        "NEAR_DESTINATION",
        "DRIVER_ARRIVED_DESTINATION"
    ]
    for state in states:
        r = requests.post(f"{API_BASE}/trips/{trip_id}/status",
                         json={"status": state, "lat": 23.5880, "lng": 58.3829},
                         headers={"Authorization": f"Bearer {driver_token}"})
        assert r.status_code == 200, f"Trip status update to {state} failed: {r.status_code} {r.text}"

def submit_pod(driver_token, trip_id):
    """Submit POD to reach DELIVERED_PENDING_CONFIRMATION."""
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status",
                     json={
                         "status": "DELIVERED_PENDING_CONFIRMATION",
                         "pod_photo": POD_PHOTO,
                         "pod_notes": "Test POD submission",
                         "lat": 17.0150,
                         "lng": 54.0924
                     },
                     headers={"Authorization": f"Bearer {driver_token}"})
    assert r.status_code == 200, f"POD submission failed: {r.status_code} {r.text}"
    return r.json()

def get_trip(token, trip_id):
    """Get trip details."""
    r = requests.get(f"{API_BASE}/trips/{trip_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Get trip failed: {r.status_code} {r.text}"
    return r.json()

def get_shipment(token, shipment_id):
    """Get shipment details."""
    r = requests.get(f"{API_BASE}/shipments/{shipment_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Get shipment failed: {r.status_code} {r.text}"
    return r.json()

def get_transactions(admin_token, trip_id=None):
    """Get transactions, optionally filtered by trip_id."""
    url = f"{API_BASE}/admin/finance/transactions"
    r = requests.get(url, headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"Get transactions failed: {r.status_code} {r.text}"
    txns = r.json()
    if trip_id:
        return [t for t in txns if t.get("trip_id") == trip_id]
    return txns

def get_notifications(token):
    """Get notifications for current user."""
    r = requests.get(f"{API_BASE}/notifications", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Get notifications failed: {r.status_code} {r.text}"
    return r.json()

# ==================== SECTION A: REAL DISPUTE FLOW ====================
def test_section_a_dispute_flow():
    log("\n" + "="*80)
    log("SECTION A: REAL DISPUTE FLOW")
    log("="*80)
    
    customer_token = login_customer()
    driver_token = login_driver()
    admin_token = login_admin()
    
    # A1: Create shipment
    log("A1: Creating and publishing shipment...")
    shipment_id = create_and_publish_shipment(customer_token)
    assert_test(shipment_id is not None, "A1: Shipment created successfully")
    
    # A2: Driver bids
    log("A2: Driver submitting bid...")
    bid_id = submit_bid(driver_token, shipment_id, price=50.0)
    assert_test(bid_id is not None, "A2: Bid submitted successfully")
    
    # A3: Customer accepts bid
    log("A3: Customer accepting bid...")
    trip_id = accept_bid(customer_token, bid_id)
    assert_test(trip_id is not None, "A3: Bid accepted, trip created")
    
    # A4: Customer pays (demo payment → HELD)
    log("A4: Customer paying for trip...")
    pay_result = pay_trip(customer_token, trip_id)
    trip = pay_result["trip"]
    assert_test(trip["payment_status"] == "HELD", "A4: Payment status is HELD")
    assert_test("payment_id" in trip, "A4: Payment ID recorded")
    
    # A4.1: Verify exactly one payment_hold transaction
    log("A4.1: Verifying payment_hold transaction...")
    txns = get_transactions(admin_token, trip_id)
    payment_holds = [t for t in txns if t["type"] == "payment_hold"]
    assert_test(len(payment_holds) == 1, f"A4.1: Exactly one payment_hold transaction (found {len(payment_holds)})")
    if payment_holds:
        assert_test(payment_holds[0]["status"] == "HELD", "A4.1: Payment hold status is HELD")
        assert_test(payment_holds[0]["amount"] == 50.0, "A4.1: Payment hold amount is correct")
    
    # A5: Driver advances trip through state machine
    log("A5: Driver advancing trip to DRIVER_ARRIVED_DESTINATION...")
    advance_trip_to_pod(driver_token, trip_id)
    
    # A6: Driver submits POD
    log("A6: Driver submitting POD...")
    trip = submit_pod(driver_token, trip_id)
    assert_test(trip["status"] == "DELIVERED_PENDING_CONFIRMATION", "A6: Trip status is DELIVERED_PENDING_CONFIRMATION")
    assert_test("delivery_proof" in trip, "A6: Delivery proof recorded")
    
    # A7: Customer disputes the trip
    log("A7: Customer disputing the trip...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/dispute",
                     json={"reason": "Damaged goods", "notes": "Package was damaged on arrival"},
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert_test(r.status_code == 200, f"A7: Dispute created successfully (status={r.status_code})")
    
    # A8: Verify trip status = DISPUTED
    log("A8: Verifying trip status...")
    trip = get_trip(customer_token, trip_id)
    assert_test(trip["status"] == "DISPUTED", f"A8: Trip status is DISPUTED (actual={trip.get('status')})")
    assert_test("dispute" in trip, "A8: Dispute details recorded")
    if "dispute" in trip:
        assert_test(trip["dispute"]["reason"] == "Damaged goods", "A8: Dispute reason preserved")
    
    # A9: Verify shipment status = DISPUTED
    log("A9: Verifying shipment status...")
    shipment = get_shipment(customer_token, shipment_id)
    assert_test(shipment["status"] == "DISPUTED", f"A9: Shipment status is DISPUTED (actual={shipment.get('status')})")
    
    # A10: Verify payment_status remains HELD
    log("A10: Verifying payment status remains HELD...")
    trip = get_trip(customer_token, trip_id)
    assert_test(trip.get("payment_status") == "HELD", f"A10: Payment status remains HELD (actual={trip.get('payment_status')})")
    
    # A11: Verify payment_hold remains HELD (not settled)
    log("A11: Verifying payment_hold transaction remains HELD...")
    txns = get_transactions(admin_token, trip_id)
    payment_holds = [t for t in txns if t["type"] == "payment_hold"]
    assert_test(len(payment_holds) == 1, f"A11: Still exactly one payment_hold (found {len(payment_holds)})")
    if payment_holds:
        assert_test(payment_holds[0]["status"] == "HELD", f"A11: Payment hold status remains HELD (actual={payment_holds[0].get('status')})")
    
    # A12: Verify ZERO settlement transactions
    log("A12: Verifying NO settlement transactions...")
    customer_payments = [t for t in txns if t["type"] == "customer_payment"]
    platform_commissions = [t for t in txns if t["type"] == "platform_commission"]
    driver_earnings = [t for t in txns if t["type"] == "driver_earning"]
    provider_earnings = [t for t in txns if t["type"] == "provider_earning"]
    
    assert_test(len(customer_payments) == 0, f"A12: Zero customer_payment transactions (found {len(customer_payments)})")
    assert_test(len(platform_commissions) == 0, f"A12: Zero platform_commission transactions (found {len(platform_commissions)})")
    assert_test(len(driver_earnings) == 0, f"A12: Zero driver_earning transactions (found {len(driver_earnings)})")
    assert_test(len(provider_earnings) == 0, f"A12: Zero provider_earning transactions (found {len(provider_earnings)})")
    
    # A13: Verify trip never becomes COMPLETED
    log("A13: Verifying trip is not COMPLETED...")
    trip = get_trip(customer_token, trip_id)
    assert_test(trip["status"] != "COMPLETED", f"A13: Trip is not COMPLETED (actual={trip.get('status')})")
    assert_test(trip.get("customer_confirmed") != True, "A13: Customer has not confirmed")
    
    # A14: Verify rating/review is blocked
    log("A14: Attempting to review disputed trip (should fail)...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/review",
                     json={
                         "overall": 5,
                         "service_quality": 5,
                         "communication": 5,
                         "on_time": 5,
                         "comment": "Test review"
                     },
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert_test(r.status_code == 400, f"A14: Review blocked for disputed trip (status={r.status_code})")
    if r.status_code == 400:
        assert_test("TRIP_IN_DISPUTE" in r.text or "dispute" in r.text.lower(), "A14: Error message mentions dispute")
    
    # A15: Verify driver receives trip_disputed notification
    log("A15: Verifying driver notification...")
    driver_notifications = get_notifications(driver_token)
    dispute_notifs = [n for n in driver_notifications if n.get("type") == "trip_disputed" and n.get("meta", {}).get("trip_id") == trip_id]
    assert_test(len(dispute_notifs) > 0, f"A15: Driver received trip_disputed notification (found {len(dispute_notifs)})")
    
    # A16: Verify all admins receive trip_disputed notification
    log("A16: Verifying admin notification...")
    admin_notifications = get_notifications(admin_token)
    admin_dispute_notifs = [n for n in admin_notifications if n.get("type") == "trip_disputed" and n.get("meta", {}).get("trip_id") == trip_id]
    assert_test(len(admin_dispute_notifs) > 0, f"A16: Admin received trip_disputed notification (found {len(admin_dispute_notifs)})")
    
    return trip_id, shipment_id

# ==================== SECTION B: DISPUTED BLOCKING/IDEMPOTENCY ====================
def test_section_b_disputed_blocking(trip_id, shipment_id):
    log("\n" + "="*80)
    log("SECTION B: DISPUTED BLOCKING/IDEMPOTENCY")
    log("="*80)
    
    customer_token = login_customer()
    driver_token = login_driver()
    admin_token = login_admin()
    
    # B1: Attempt duplicate dispute
    log("B1: Attempting duplicate dispute (should fail)...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/dispute",
                     json={"reason": "Another reason", "notes": "Duplicate dispute"},
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert_test(r.status_code in [400, 409], f"B1: Duplicate dispute rejected (status={r.status_code})")
    
    # B2: Attempt customer confirm-delivery
    log("B2: Attempting confirm-delivery on disputed trip (should fail)...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/confirm-delivery",
                     json={"reference": "test", "lat": 17.0150, "lng": 54.0924},
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert_test(r.status_code == 400, f"B2: Confirm-delivery blocked (status={r.status_code})")
    if r.status_code == 400:
        assert_test("TRIP_IN_DISPUTE" in r.text or "dispute" in r.text.lower(), "B2: Error message mentions dispute")
    
    # B3: Attempt customer review
    log("B3: Attempting review on disputed trip (should fail)...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/review",
                     json={
                         "overall": 5,
                         "service_quality": 5,
                         "communication": 5,
                         "on_time": 5,
                         "comment": "Test review"
                     },
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert_test(r.status_code == 400, f"B3: Review blocked (status={r.status_code})")
    
    # B4: Attempt driver status update
    log("B4: Attempting driver status update on disputed trip (should fail)...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/status",
                     json={"status": "COMPLETED", "lat": 17.0150, "lng": 54.0924},
                     headers={"Authorization": f"Bearer {driver_token}"})
    assert_test(r.status_code == 400, f"B4: Driver status update blocked (status={r.status_code})")
    if r.status_code == 400:
        assert_test("TRIP_IN_TERMINAL_STATE" in r.text or "terminal" in r.text.lower(), "B4: Error message mentions terminal state")
    
    # B5: GET trip/mine (lazy auto-completion check)
    log("B5: Verifying lazy auto-completion doesn't change disputed trip...")
    r = requests.get(f"{API_BASE}/trips/mine", headers={"Authorization": f"Bearer {customer_token}"})
    assert_test(r.status_code == 200, f"B5: GET trips/mine successful (status={r.status_code})")
    trips = r.json()
    disputed_trip = next((t for t in trips if t["id"] == trip_id), None)
    assert_test(disputed_trip is not None, "B5: Disputed trip found in trips/mine")
    if disputed_trip:
        assert_test(disputed_trip["status"] == "DISPUTED", f"B5: Trip status remains DISPUTED (actual={disputed_trip.get('status')})")
    
    # B6: Verify trip status still DISPUTED
    log("B6: Verifying trip status remains DISPUTED...")
    trip = get_trip(customer_token, trip_id)
    assert_test(trip["status"] == "DISPUTED", f"B6: Trip status remains DISPUTED (actual={trip.get('status')})")
    
    # B7: Verify shipment status still DISPUTED
    log("B7: Verifying shipment status remains DISPUTED...")
    shipment = get_shipment(customer_token, shipment_id)
    assert_test(shipment["status"] == "DISPUTED", f"B7: Shipment status remains DISPUTED (actual={shipment.get('status')})")
    
    # B8: Verify payment status still HELD
    log("B8: Verifying payment status remains HELD...")
    trip = get_trip(customer_token, trip_id)
    assert_test(trip.get("payment_status") == "HELD", f"B8: Payment status remains HELD (actual={trip.get('payment_status')})")
    
    # B9: Verify ledger still has no settlement
    log("B9: Verifying ledger still has no settlement transactions...")
    txns = get_transactions(admin_token, trip_id)
    customer_payments = [t for t in txns if t["type"] == "customer_payment"]
    platform_commissions = [t for t in txns if t["type"] == "platform_commission"]
    driver_earnings = [t for t in txns if t["type"] == "driver_earning"]
    
    assert_test(len(customer_payments) == 0, f"B9: Still zero customer_payment transactions (found {len(customer_payments)})")
    assert_test(len(platform_commissions) == 0, f"B9: Still zero platform_commission transactions (found {len(platform_commissions)})")
    assert_test(len(driver_earnings) == 0, f"B9: Still zero driver_earning transactions (found {len(driver_earnings)})")
    
    # B10: Verify duplicate payment attempt is idempotent
    log("B10: Attempting duplicate payment (should be idempotent)...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/pay",
                     headers={"Authorization": f"Bearer {customer_token}"})
    # Should either return 200 with already_paid=true or 400 TRIP_IN_TERMINAL_STATE
    assert_test(r.status_code in [200, 400], f"B10: Duplicate payment handled (status={r.status_code})")
    if r.status_code == 200:
        result = r.json()
        assert_test(result.get("already_paid") == True, "B10: Payment marked as already_paid")
    
    # B11: Verify payment_hold count hasn't changed
    log("B11: Verifying payment_hold count unchanged...")
    txns = get_transactions(admin_token, trip_id)
    payment_holds = [t for t in txns if t["type"] == "payment_hold"]
    assert_test(len(payment_holds) == 1, f"B11: Still exactly one payment_hold (found {len(payment_holds)})")

# ==================== SECTION C: SEPARATE NORMAL FLOW ====================
def test_section_c_normal_flow():
    log("\n" + "="*80)
    log("SECTION C: SEPARATE NORMAL FLOW (COMPLETED)")
    log("="*80)
    
    customer_token = login_customer()
    driver_token = login_driver()
    admin_token = login_admin()
    
    # C1: Create new shipment
    log("C1: Creating new shipment for normal flow...")
    shipment_id = create_and_publish_shipment(customer_token)
    assert_test(shipment_id is not None, "C1: Shipment created successfully")
    
    # C2: Driver bids
    log("C2: Driver submitting bid...")
    bid_id = submit_bid(driver_token, shipment_id, price=40.0)
    assert_test(bid_id is not None, "C2: Bid submitted successfully")
    
    # C3: Customer accepts bid
    log("C3: Customer accepting bid...")
    trip_id = accept_bid(customer_token, bid_id)
    assert_test(trip_id is not None, "C3: Bid accepted, trip created")
    
    # C4: Customer pays
    log("C4: Customer paying for trip...")
    pay_result = pay_trip(customer_token, trip_id)
    trip = pay_result["trip"]
    assert_test(trip["payment_status"] == "HELD", "C4: Payment status is HELD")
    
    # C5: Driver advances trip
    log("C5: Driver advancing trip to DRIVER_ARRIVED_DESTINATION...")
    advance_trip_to_pod(driver_token, trip_id)
    
    # C6: Driver submits POD
    log("C6: Driver submitting POD...")
    trip = submit_pod(driver_token, trip_id)
    assert_test(trip["status"] == "DELIVERED_PENDING_CONFIRMATION", "C6: Trip status is DELIVERED_PENDING_CONFIRMATION")
    
    # C7: Customer confirms delivery
    log("C7: Customer confirming delivery...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/confirm-delivery",
                     json={"reference": "test-confirm", "lat": 17.0150, "lng": 54.0924, "delivered_to_name": "Test Recipient"},
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert_test(r.status_code == 200, f"C7: Delivery confirmed successfully (status={r.status_code})")
    
    # C8: Verify trip status = COMPLETED
    log("C8: Verifying trip status is COMPLETED...")
    trip = get_trip(customer_token, trip_id)
    assert_test(trip["status"] == "COMPLETED", f"C8: Trip status is COMPLETED (actual={trip.get('status')})")
    assert_test(trip.get("customer_confirmed") == True, "C8: Customer confirmed flag is true")
    
    # C9: Verify shipment status = COMPLETED
    log("C9: Verifying shipment status is COMPLETED...")
    shipment = get_shipment(customer_token, shipment_id)
    assert_test(shipment["status"] == "COMPLETED", f"C9: Shipment status is COMPLETED (actual={shipment.get('status')})")
    
    # C10: Verify exactly one customer_payment transaction
    log("C10: Verifying exactly one customer_payment transaction...")
    txns = get_transactions(admin_token, trip_id)
    customer_payments = [t for t in txns if t["type"] == "customer_payment"]
    assert_test(len(customer_payments) == 1, f"C10: Exactly one customer_payment (found {len(customer_payments)})")
    if customer_payments:
        assert_test(customer_payments[0]["amount"] == 40.0, "C10: Customer payment amount is correct")
        assert_test(customer_payments[0]["status"] == "COMPLETED", "C10: Customer payment status is COMPLETED")
    
    # C11: Verify exactly one platform_commission transaction
    log("C11: Verifying exactly one platform_commission transaction...")
    platform_commissions = [t for t in txns if t["type"] == "platform_commission"]
    assert_test(len(platform_commissions) == 1, f"C11: Exactly one platform_commission (found {len(platform_commissions)})")
    if platform_commissions:
        assert_test(platform_commissions[0]["status"] == "COMPLETED", "C11: Platform commission status is COMPLETED")
    
    # C12: Verify exactly one driver_earning transaction
    log("C12: Verifying exactly one driver_earning transaction...")
    driver_earnings = [t for t in txns if t["type"] == "driver_earning"]
    assert_test(len(driver_earnings) == 1, f"C12: Exactly one driver_earning (found {len(driver_earnings)})")
    if driver_earnings:
        assert_test(driver_earnings[0]["status"] == "COMPLETED", "C12: Driver earning status is COMPLETED")
    
    # C13: Verify payment_hold is not duplicated
    log("C13: Verifying payment_hold is not duplicated...")
    payment_holds = [t for t in txns if t["type"] == "payment_hold"]
    assert_test(len(payment_holds) == 1, f"C13: Exactly one payment_hold (found {len(payment_holds)})")
    
    # C14: Attempt duplicate confirm (should fail)
    log("C14: Attempting duplicate confirm-delivery (should fail)...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/confirm-delivery",
                     json={"reference": "duplicate", "lat": 17.0150, "lng": 54.0924},
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert_test(r.status_code in [400, 409], f"C14: Duplicate confirm rejected (status={r.status_code})")
    
    # C15: Verify transaction counts haven't changed
    log("C15: Verifying transaction counts unchanged after duplicate confirm...")
    txns_after = get_transactions(admin_token, trip_id)
    customer_payments_after = [t for t in txns_after if t["type"] == "customer_payment"]
    platform_commissions_after = [t for t in txns_after if t["type"] == "platform_commission"]
    driver_earnings_after = [t for t in txns_after if t["type"] == "driver_earning"]
    
    assert_test(len(customer_payments_after) == 1, f"C15: Still exactly one customer_payment (found {len(customer_payments_after)})")
    assert_test(len(platform_commissions_after) == 1, f"C15: Still exactly one platform_commission (found {len(platform_commissions_after)})")
    assert_test(len(driver_earnings_after) == 1, f"C15: Still exactly one driver_earning (found {len(driver_earnings_after)})")
    
    # C16: Verify rating is available for completed trip
    log("C16: Submitting rating for completed trip...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/review",
                     json={
                         "overall": 5,
                         "service_quality": 5,
                         "communication": 5,
                         "on_time": 5,
                         "comment": "Excellent service"
                     },
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert_test(r.status_code == 200, f"C16: Rating submitted successfully (status={r.status_code})")
    
    # C17: Attempt duplicate rating (should fail)
    log("C17: Attempting duplicate rating (should fail)...")
    r = requests.post(f"{API_BASE}/trips/{trip_id}/review",
                     json={
                         "overall": 4,
                         "service_quality": 4,
                         "communication": 4,
                         "on_time": 4,
                         "comment": "Duplicate review"
                     },
                     headers={"Authorization": f"Bearer {customer_token}"})
    assert_test(r.status_code == 409, f"C17: Duplicate rating rejected (status={r.status_code})")
    
    # C18: Verify settlement is idempotent (transaction counts still the same)
    log("C18: Verifying settlement idempotency...")
    txns_final = get_transactions(admin_token, trip_id)
    customer_payments_final = [t for t in txns_final if t["type"] == "customer_payment"]
    platform_commissions_final = [t for t in txns_final if t["type"] == "platform_commission"]
    driver_earnings_final = [t for t in txns_final if t["type"] == "driver_earning"]
    
    assert_test(len(customer_payments_final) == 1, f"C18: Still exactly one customer_payment (found {len(customer_payments_final)})")
    assert_test(len(platform_commissions_final) == 1, f"C18: Still exactly one platform_commission (found {len(platform_commissions_final)})")
    assert_test(len(driver_earnings_final) == 1, f"C18: Still exactly one driver_earning (found {len(driver_earnings_final)})")

# ==================== SECTION D: SUPER_ADMIN PROTECTION ====================
def test_section_d_super_admin_protection():
    log("\n" + "="*80)
    log("SECTION D: SUPER_ADMIN PROTECTION")
    log("="*80)
    
    admin_token = login_admin()
    
    # D1: Identify super_admin
    log("D1: Identifying super_admin...")
    r = requests.get(f"{API_BASE}/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"Get current user failed: {r.status_code}"
    super_admin = r.json()
    super_admin_id = super_admin["id"]
    assert_test(super_admin.get("admin_role_key") == "super_admin", f"D1: Current user is super_admin (actual={super_admin.get('admin_role_key')})")
    log(f"   Super admin ID: {super_admin_id}")
    
    # D2: Create a manager admin (lower-level admin)
    log("D2: Creating manager admin...")
    r = requests.post(f"{API_BASE}/admin/admins",
                     json={
                         "name": "Test Manager",
                         "email": f"manager_test_{datetime.now().timestamp()}@cargo.test",
                         "password": "test123456",
                         "admin_role_key": "manager"
                     },
                     headers={"Authorization": f"Bearer {admin_token}"})
    assert_test(r.status_code == 200, f"D2: Manager admin created (status={r.status_code})")
    if r.status_code == 200:
        manager_id = r.json()["id"]
        manager_email = r.json()["email"]
        log(f"   Manager ID: {manager_id}, Email: {manager_email}")
        
        # D2.1: Login as manager
        log("D2.1: Logging in as manager...")
        r = requests.post(f"{API_BASE}/auth/admin/login",
                         json={"email": manager_email, "password": "test123456"})
        assert_test(r.status_code == 200, f"D2.1: Manager login successful (status={r.status_code})")
        if r.status_code == 200:
            manager_token = r.json()["token"]
            
            # D3: Manager attempts to modify super_admin (PUT /api/admin/users/{super_admin_id})
            log("D3: Manager attempting to modify super_admin user (should fail)...")
            r = requests.put(f"{API_BASE}/admin/users/{super_admin_id}",
                           json={"name": "Modified Super Admin", "notes": "Unauthorized modification"},
                           headers={"Authorization": f"Bearer {manager_token}"})
            assert_test(r.status_code == 403, f"D3: Manager blocked from modifying super_admin (status={r.status_code})")
            if r.status_code == 403:
                assert_test("SUPER_ADMIN_PROTECTED" in r.text or "protected" in r.text.lower(), "D3: Error message mentions protection")
            
            # D4: Manager attempts to reset super_admin password
            log("D4: Manager attempting to reset super_admin password (should fail)...")
            r = requests.post(f"{API_BASE}/admin/users/{super_admin_id}/reset-password",
                            json={"password": "hacked123"},
                            headers={"Authorization": f"Bearer {manager_token}"})
            assert_test(r.status_code == 403, f"D4: Manager blocked from resetting super_admin password (status={r.status_code})")
            
            # D5: Manager attempts to disable super_admin
            log("D5: Manager attempting to disable super_admin (should fail)...")
            r = requests.post(f"{API_BASE}/admin/users/{super_admin_id}/status",
                            json={"status": "disabled"},
                            headers={"Authorization": f"Bearer {manager_token}"})
            assert_test(r.status_code == 403, f"D5: Manager blocked from disabling super_admin (status={r.status_code})")
            
            # D6: Manager attempts to suspend super_admin
            log("D6: Manager attempting to suspend super_admin (should fail)...")
            r = requests.post(f"{API_BASE}/admin/users/{super_admin_id}/suspend",
                            json={"reason": "Unauthorized suspension"},
                            headers={"Authorization": f"Bearer {manager_token}"})
            assert_test(r.status_code == 403, f"D6: Manager blocked from suspending super_admin (status={r.status_code})")
            
            # D7: Manager attempts to change super_admin role
            log("D7: Manager attempting to change super_admin role (should fail)...")
            r = requests.put(f"{API_BASE}/admin/admins/{super_admin_id}/role",
                           json={"admin_role_key": "manager"},
                           headers={"Authorization": f"Bearer {manager_token}"})
            assert_test(r.status_code == 403, f"D7: Manager blocked from changing super_admin role (status={r.status_code})")
            
            # D8: Manager attempts to grant super_admin role to self
            log("D8: Manager attempting to grant super_admin role to self (should fail)...")
            r = requests.put(f"{API_BASE}/admin/users/{manager_id}",
                           json={"admin_role_key": "super_admin"},
                           headers={"Authorization": f"Bearer {manager_token}"})
            assert_test(r.status_code == 403, f"D8: Manager blocked from granting super_admin role (status={r.status_code})")
            if r.status_code == 403:
                assert_test("PLATFORM_ADMIN_ROLE_REQUIRED" in r.text or "platform" in r.text.lower(), "D8: Error message mentions platform admin requirement")
            
            # D9: Manager attempts to create new super_admin
            log("D9: Manager attempting to create new super_admin (should fail)...")
            r = requests.post(f"{API_BASE}/admin/admins",
                            json={
                                "name": "Fake Super Admin",
                                "email": f"fake_super_{datetime.now().timestamp()}@cargo.test",
                                "password": "test123456",
                                "admin_role_key": "super_admin"
                            },
                            headers={"Authorization": f"Bearer {manager_token}"})
            assert_test(r.status_code == 403, f"D9: Manager blocked from creating super_admin (status={r.status_code})")
    
    # D10: Verify super_admin unchanged
    log("D10: Verifying super_admin account unchanged...")
    r = requests.get(f"{API_BASE}/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200, f"Get super_admin failed: {r.status_code}"
    current_super_admin = r.json()
    assert_test(current_super_admin["id"] == super_admin_id, "D10: Super admin ID unchanged")
    assert_test(current_super_admin.get("admin_role_key") == "super_admin", "D10: Super admin role unchanged")
    assert_test(current_super_admin.get("status", "active").lower() == "active", "D10: Super admin status is active")
    
    # D11: Verify last super_admin protection
    log("D11: Attempting to suspend last super_admin (should fail)...")
    r = requests.post(f"{API_BASE}/admin/users/{super_admin_id}/suspend",
                     json={"reason": "Test last super_admin protection"},
                     headers={"Authorization": f"Bearer {admin_token}"})
    # Should fail because this is the last active super_admin
    assert_test(r.status_code == 400, f"D11: Last super_admin protection active (status={r.status_code})")
    if r.status_code == 400:
        assert_test("CANNOT_SUSPEND_LAST_SUPER_ADMIN" in r.text or "last" in r.text.lower(), "D11: Error message mentions last super_admin")
    
    # D12: Create second super_admin to test protection bypass
    log("D12: Creating second super_admin...")
    r = requests.post(f"{API_BASE}/admin/admins",
                     json={
                         "name": "Second Super Admin",
                         "email": f"super2_{datetime.now().timestamp()}@cargo.test",
                         "password": "test123456",
                         "admin_role_key": "super_admin"
                     },
                     headers={"Authorization": f"Bearer {admin_token}"})
    assert_test(r.status_code == 200, f"D12: Second super_admin created (status={r.status_code})")
    if r.status_code == 200:
        second_super_id = r.json()["id"]
        
        # D13: Now first super_admin can be suspended (but we won't actually do it to avoid breaking tests)
        log("D13: Verifying first super_admin CAN now be suspended (with 2 active super_admins)...")
        # We'll just verify the protection is lifted by checking the count
        r = requests.get(f"{API_BASE}/admin/users?role=admin", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200, f"Get admin users failed: {r.status_code}"
        admins = r.json()
        super_admins = [a for a in admins if a.get("admin_role_key") == "super_admin" and a.get("status", "active").lower() == "active"]
        assert_test(len(super_admins) >= 2, f"D13: At least 2 active super_admins exist (found {len(super_admins)})")
    
    # D14: Verify legitimate super_admin access still works
    log("D14: Verifying legitimate super_admin operations still work...")
    r = requests.get(f"{API_BASE}/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert_test(r.status_code == 200, f"D14: Super admin can access admin stats (status={r.status_code})")
    
    r = requests.get(f"{API_BASE}/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert_test(r.status_code == 200, f"D14: Super admin can list users (status={r.status_code})")
    
    r = requests.get(f"{API_BASE}/admin/finance/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert_test(r.status_code == 200, f"D14: Super admin can access finance stats (status={r.status_code})")

# ==================== MAIN ====================
def main():
    log("="*80)
    log("PHASE 2B BACKEND TESTING")
    log("Critical dispute/payment safety + super_admin authorization protection")
    log(f"Backend URL: {BASE_URL}")
    log("="*80)
    
    try:
        # Section A: Real dispute flow
        trip_id, shipment_id = test_section_a_dispute_flow()
        
        # Section B: Disputed blocking/idempotency
        test_section_b_disputed_blocking(trip_id, shipment_id)
        
        # Section C: Separate normal flow
        test_section_c_normal_flow()
        
        # Section D: Super_admin protection
        test_section_d_super_admin_protection()
        
    except Exception as e:
        log(f"\n❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        test_results["failed"] += 1
        test_results["failures"].append(f"Critical error: {str(e)}")
    
    # Print summary
    log("\n" + "="*80)
    log("TEST SUMMARY")
    log("="*80)
    log(f"Total tests: {test_results['total']}")
    log(f"Passed: {test_results['passed']}")
    log(f"Failed: {test_results['failed']}")
    
    if test_results["failed"] > 0:
        log("\n❌ FAILED TESTS:")
        for failure in test_results["failures"]:
            log(f"  - {failure}")
        sys.exit(1)
    else:
        log("\n✅ ALL TESTS PASSED!")
        sys.exit(0)

if __name__ == "__main__":
    main()
