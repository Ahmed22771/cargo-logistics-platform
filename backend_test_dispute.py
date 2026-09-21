#!/usr/bin/env python3
"""
Dispute Resolution Phase 1 — Financial Resolution Core Backend Tests
Tests the POST /api/admin/disputes/{trip_id}/resolve endpoint with all scenarios.
"""
import requests
import sys
import time
from typing import Dict, Optional

BASE_URL = "https://6d1774a7-93f3-4112-a01b-a68cdfddb960.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"
CUSTOMER_PHONE = "+96890000001"
DRIVER_PHONE = "+96890000002"

# POD photo (small base64 data-url)
POD_PHOTO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

class TestRunner:
    def __init__(self):
        self.admin_token = None
        self.customer_token = None
        self.driver_token = None
        self.passed = 0
        self.failed = 0
        self.test_trips = []  # Store created trip IDs for cleanup
        
    def log(self, msg: str):
        print(f"[TEST] {msg}")
        
    def assert_eq(self, actual, expected, msg: str):
        if actual == expected:
            self.passed += 1
            self.log(f"✅ PASS: {msg}")
            return True
        else:
            self.failed += 1
            self.log(f"❌ FAIL: {msg} (expected {expected}, got {actual})")
            return False
            
    def assert_true(self, condition: bool, msg: str):
        if condition:
            self.passed += 1
            self.log(f"✅ PASS: {msg}")
            return True
        else:
            self.failed += 1
            self.log(f"❌ FAIL: {msg}")
            return False
            
    def assert_in(self, item, container, msg: str):
        if item in container:
            self.passed += 1
            self.log(f"✅ PASS: {msg}")
            return True
        else:
            self.failed += 1
            self.log(f"❌ FAIL: {msg} ({item} not in {container})")
            return False
    
    def login_admin(self):
        """Login as super_admin"""
        self.log("Logging in as admin...")
        r = requests.post(f"{BASE_URL}/auth/admin/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        self.assert_eq(r.status_code, 200, "Admin login returns 200")
        if r.status_code == 200:
            data = r.json()
            self.admin_token = data.get("token")
            self.assert_true(self.admin_token is not None, "Admin token received")
            return True
        return False
    
    def login_otp(self, phone: str, role: str) -> Optional[str]:
        """Login via OTP demo flow"""
        self.log(f"Logging in as {role} {phone}...")
        # Request OTP
        r1 = requests.post(f"{BASE_URL}/auth/otp/request", json={
            "phone": phone,
            "role": role
        })
        self.assert_eq(r1.status_code, 200, f"{role} OTP request returns 200")
        if r1.status_code != 200:
            return None
        
        data1 = r1.json()
        demo_code = data1.get("demo_code")
        self.assert_true(demo_code is not None, f"{role} demo_code received")
        
        # Verify OTP
        r2 = requests.post(f"{BASE_URL}/auth/otp/verify", json={
            "phone": phone,
            "role": role,
            "code": demo_code
        })
        self.assert_eq(r2.status_code, 200, f"{role} OTP verify returns 200")
        if r2.status_code == 200:
            data2 = r2.json()
            token = data2.get("token")
            self.assert_true(token is not None, f"{role} token received")
            return token
        return None
    
    def create_disputed_trip(self, trip_name: str) -> Optional[str]:
        """Create a full trip through the flow and dispute it"""
        self.log(f"\n=== Creating disputed trip: {trip_name} ===")
        
        # 1. Customer creates and publishes shipment
        shipment_data = {
            "title": f"Test Shipment {trip_name}",
            "description": "Test cargo",
            "category": "general",
            "weight": "100",
            "pickup_location": {
                "address": "مسقط",
                "lat": 23.58,
                "lng": 58.40
            },
            "delivery_location": {
                "address": "صلالة",
                "lat": 17.01,
                "lng": 54.09
            },
            "pickup_date": "2025-02-01",
            "delivery_date": "2025-02-05",
            "vehicle_type": "flatbed"
        }
        
        r1 = requests.post(f"{BASE_URL}/shipments", 
                          json=shipment_data,
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        if r1.status_code != 200:
            self.log(f"❌ Failed to create shipment: {r1.status_code} {r1.text}")
            return None
        
        shipment = r1.json()
        shipment_id = shipment["id"]
        self.log(f"Created shipment {shipment_id}")
        
        # Publish
        r2 = requests.post(f"{BASE_URL}/shipments/{shipment_id}/publish",
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        if r2.status_code != 200:
            self.log(f"❌ Failed to publish shipment: {r2.status_code}")
            return None
        self.log(f"Published shipment {shipment_id}")
        
        # 2. Driver submits bid
        r3 = requests.post(f"{BASE_URL}/shipments/{shipment_id}/bids",
                          json={"price": 40, "note": "test bid"},
                          headers={"Authorization": f"Bearer {self.driver_token}"})
        if r3.status_code != 200:
            self.log(f"❌ Failed to submit bid: {r3.status_code}")
            return None
        
        bid = r3.json()
        bid_id = bid["id"]
        self.log(f"Driver submitted bid {bid_id}")
        
        # 3. Customer accepts bid
        r4 = requests.post(f"{BASE_URL}/bids/{bid_id}/accept",
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        if r4.status_code != 200:
            self.log(f"❌ Failed to accept bid: {r4.status_code}")
            return None
        
        trip = r4.json()
        trip_id = trip["id"]
        self.log(f"Created trip {trip_id}")
        self.test_trips.append(trip_id)
        
        # 4. Customer pays
        r5 = requests.post(f"{BASE_URL}/trips/{trip_id}/pay",
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        if r5.status_code != 200:
            self.log(f"❌ Failed to pay: {r5.status_code}")
            return None
        self.log(f"Payment held for trip {trip_id}")
        
        # 5. Driver advances through all states to DELIVERED_PENDING_CONFIRMATION
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
            r = requests.post(f"{BASE_URL}/trips/{trip_id}/status",
                            json={"status": state},
                            headers={"Authorization": f"Bearer {self.driver_token}"})
            if r.status_code != 200:
                self.log(f"❌ Failed to advance to {state}: {r.status_code}")
                return None
        
        # Final state with POD
        r6 = requests.post(f"{BASE_URL}/trips/{trip_id}/status",
                          json={
                              "status": "DELIVERED_PENDING_CONFIRMATION",
                              "pod_photo": POD_PHOTO,
                              "pod_notes": "Delivered successfully"
                          },
                          headers={"Authorization": f"Bearer {self.driver_token}"})
        if r6.status_code != 200:
            self.log(f"❌ Failed to submit POD: {r6.status_code}")
            return None
        self.log(f"POD submitted for trip {trip_id}")
        
        # 6. Customer disputes
        r7 = requests.post(f"{BASE_URL}/trips/{trip_id}/dispute",
                          json={
                              "reason": "cargo damaged",
                              "notes": "test dispute"
                          },
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        if r7.status_code != 200:
            self.log(f"❌ Failed to dispute: {r7.status_code}")
            return None
        
        self.log(f"✅ Trip {trip_id} disputed successfully")
        return trip_id
    
    def get_dispute_detail(self, trip_id: str) -> Optional[Dict]:
        """Get dispute detail via admin endpoint"""
        r = requests.get(f"{BASE_URL}/admin/disputes/{trip_id}",
                        headers={"Authorization": f"Bearer {self.admin_token}"})
        if r.status_code == 200:
            return r.json()
        return None
    
    def count_transactions_by_type(self, trip_id: str) -> Dict[str, int]:
        """Count transactions for a trip by type"""
        r = requests.get(f"{BASE_URL}/admin/finance/transactions",
                        headers={"Authorization": f"Bearer {self.admin_token}"})
        if r.status_code != 200:
            return {}
        
        txns = r.json()
        trip_txns = [t for t in txns if t.get("trip_id") == trip_id]
        
        counts = {}
        for t in trip_txns:
            typ = t.get("type")
            counts[typ] = counts.get(typ, 0) + 1
        
        return counts
    
    def test_release_to_driver(self):
        """Test 1: RELEASE_TO_DRIVER resolution"""
        self.log("\n" + "="*60)
        self.log("TEST 1: RELEASE_TO_DRIVER")
        self.log("="*60)
        
        trip_id = self.create_disputed_trip("RELEASE")
        if not trip_id:
            self.log("❌ Failed to create disputed trip")
            return
        
        # Resolve as RELEASE_TO_DRIVER
        r = requests.post(f"{BASE_URL}/admin/disputes/{trip_id}/resolve",
                         json={
                             "outcome": "RELEASE_TO_DRIVER",
                             "reason": "delivered ok"
                         },
                         headers={"Authorization": f"Bearer {self.admin_token}"})
        
        self.assert_eq(r.status_code, 200, "Resolve RELEASE_TO_DRIVER returns 200")
        
        # Verify dispute detail
        detail = self.get_dispute_detail(trip_id)
        if detail:
            trip = detail.get("trip", {})
            dispute = trip.get("dispute", {})
            hold = detail.get("payment_hold", {})
            
            self.assert_eq(dispute.get("status"), "RESOLVED", "Dispute status = RESOLVED")
            self.assert_eq(dispute.get("outcome"), "RELEASE_TO_DRIVER", "Dispute outcome = RELEASE_TO_DRIVER")
            self.assert_true(dispute.get("resolved_by_name") is not None, "resolved_by_name present")
            self.assert_true(dispute.get("resolved_at") is not None, "resolved_at present")
            
            self.assert_eq(trip.get("status"), "COMPLETED", "Trip status = COMPLETED")
            self.assert_eq(trip.get("payment_status"), "RELEASED", "Trip payment_status = RELEASED")
            
            self.assert_true(hold is not None, "Payment hold exists (not deleted)")
            self.assert_eq(hold.get("status"), "RELEASED", "Hold status = RELEASED")
            
            # Check shipment status
            r2 = requests.get(f"{BASE_URL}/shipments/{trip.get('shipment_id')}",
                            headers={"Authorization": f"Bearer {self.customer_token}"})
            if r2.status_code == 200:
                shipment = r2.json()
                self.assert_eq(shipment.get("status"), "COMPLETED", "Shipment status = COMPLETED")
        
        # Verify transactions
        counts = self.count_transactions_by_type(trip_id)
        self.assert_eq(counts.get("payment_hold", 0), 1, "Exactly 1 payment_hold transaction")
        self.assert_eq(counts.get("customer_payment", 0), 1, "Exactly 1 customer_payment transaction")
        self.assert_eq(counts.get("platform_commission", 0), 1, "Exactly 1 platform_commission transaction")
        self.assert_eq(counts.get("driver_earning", 0), 1, "Exactly 1 driver_earning transaction")
        self.assert_eq(counts.get("refund", 0), 0, "NO refund transaction")
        
        # Verify audit log
        r3 = requests.get(f"{BASE_URL}/admin/audit-logs",
                         headers={"Authorization": f"Bearer {self.admin_token}"})
        if r3.status_code == 200:
            logs = r3.json()
            release_logs = [l for l in logs if l.get("action") == "DISPUTE_RESOLVED_RELEASE" and l.get("entity_id") == trip_id]
            self.assert_true(len(release_logs) > 0, "Audit log contains DISPUTE_RESOLVED_RELEASE")
            if release_logs:
                log = release_logs[0]
                old_val = log.get("old_value", {})
                new_val = log.get("new_value", {})
                self.assert_eq(old_val.get("payment_status"), "HELD", "Audit old payment_status = HELD")
                self.assert_eq(new_val.get("payment_status"), "RELEASED", "Audit new payment_status = RELEASED")
        
        # Test customer can rate after release
        r4 = requests.post(f"{BASE_URL}/trips/{trip_id}/review",
                          json={
                              "overall": 5,
                              "service_quality": 5,
                              "communication": 5,
                              "on_time": 5,
                              "comment": "ok"
                          },
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        self.assert_eq(r4.status_code, 200, "Customer can rate after RELEASE")
    
    def test_full_refund(self):
        """Test 2: FULL_REFUND resolution"""
        self.log("\n" + "="*60)
        self.log("TEST 2: FULL_REFUND")
        self.log("="*60)
        
        trip_id = self.create_disputed_trip("REFUND")
        if not trip_id:
            self.log("❌ Failed to create disputed trip")
            return
        
        # Resolve as FULL_REFUND
        r = requests.post(f"{BASE_URL}/admin/disputes/{trip_id}/resolve",
                         json={
                             "outcome": "FULL_REFUND",
                             "reason": "not delivered"
                         },
                         headers={"Authorization": f"Bearer {self.admin_token}"})
        
        self.assert_eq(r.status_code, 200, "Resolve FULL_REFUND returns 200")
        
        # Verify dispute detail
        detail = self.get_dispute_detail(trip_id)
        if detail:
            trip = detail.get("trip", {})
            dispute = trip.get("dispute", {})
            hold = detail.get("payment_hold", {})
            
            self.assert_eq(dispute.get("status"), "RESOLVED", "Dispute status = RESOLVED")
            self.assert_eq(dispute.get("outcome"), "FULL_REFUND", "Dispute outcome = FULL_REFUND")
            
            self.assert_eq(trip.get("status"), "REFUNDED", "Trip status = REFUNDED")
            self.assert_eq(trip.get("payment_status"), "REFUNDED", "Trip payment_status = REFUNDED")
            
            self.assert_true(hold is not None, "Payment hold exists (not deleted)")
            self.assert_eq(hold.get("status"), "REFUNDED", "Hold status = REFUNDED")
            self.assert_true(hold.get("refund_txn_id") is not None, "Hold has refund_txn_id")
            
            # Check shipment status
            r2 = requests.get(f"{BASE_URL}/shipments/{trip.get('shipment_id')}",
                            headers={"Authorization": f"Bearer {self.customer_token}"})
            if r2.status_code == 200:
                shipment = r2.json()
                self.assert_eq(shipment.get("status"), "REFUNDED", "Shipment status = REFUNDED")
        
        # Verify transactions
        counts = self.count_transactions_by_type(trip_id)
        self.assert_eq(counts.get("payment_hold", 0), 1, "Exactly 1 payment_hold transaction")
        self.assert_eq(counts.get("refund", 0), 1, "Exactly 1 refund transaction")
        self.assert_eq(counts.get("customer_payment", 0), 0, "NO customer_payment transaction")
        self.assert_eq(counts.get("platform_commission", 0), 0, "NO platform_commission transaction")
        self.assert_eq(counts.get("driver_earning", 0), 0, "NO driver_earning transaction")
        
        # Verify audit log
        r3 = requests.get(f"{BASE_URL}/admin/audit-logs",
                         headers={"Authorization": f"Bearer {self.admin_token}"})
        if r3.status_code == 200:
            logs = r3.json()
            refund_logs = [l for l in logs if l.get("action") == "DISPUTE_RESOLVED_REFUND" and l.get("entity_id") == trip_id]
            self.assert_true(len(refund_logs) > 0, "Audit log contains DISPUTE_RESOLVED_REFUND")
    
    def test_duplicate_resolution(self):
        """Test 3: Duplicate resolution attempts"""
        self.log("\n" + "="*60)
        self.log("TEST 3: DUPLICATE RESOLUTION")
        self.log("="*60)
        
        # Use the first released trip
        if len(self.test_trips) < 1:
            self.log("❌ No test trips available")
            return
        
        trip_id = self.test_trips[0]
        
        # Get transaction counts before
        counts_before = self.count_transactions_by_type(trip_id)
        
        # Try to resolve again with same outcome
        r = requests.post(f"{BASE_URL}/admin/disputes/{trip_id}/resolve",
                         json={
                             "outcome": "RELEASE_TO_DRIVER",
                             "reason": "duplicate attempt"
                         },
                         headers={"Authorization": f"Bearer {self.admin_token}"})
        
        self.assert_eq(r.status_code, 409, "Duplicate resolution returns 409")
        if r.status_code == 409:
            self.assert_in("ALREADY_RESOLVED", r.text, "Error detail contains ALREADY_RESOLVED")
        
        # Verify transaction counts unchanged
        counts_after = self.count_transactions_by_type(trip_id)
        self.assert_eq(counts_after, counts_before, "Transaction counts unchanged after duplicate")
    
    def test_conflicting_resolution(self):
        """Test 4: Conflicting resolution attempts"""
        self.log("\n" + "="*60)
        self.log("TEST 4: CONFLICTING RESOLUTION")
        self.log("="*60)
        
        if len(self.test_trips) < 2:
            self.log("❌ Not enough test trips available")
            return
        
        released_trip = self.test_trips[0]
        refunded_trip = self.test_trips[1]
        
        # Try FULL_REFUND on released trip
        r1 = requests.post(f"{BASE_URL}/admin/disputes/{released_trip}/resolve",
                          json={
                              "outcome": "FULL_REFUND",
                              "reason": "conflicting"
                          },
                          headers={"Authorization": f"Bearer {self.admin_token}"})
        
        self.assert_eq(r1.status_code, 409, "Conflicting FULL_REFUND on released trip returns 409")
        
        # Verify trip still COMPLETED
        detail1 = self.get_dispute_detail(released_trip)
        if detail1:
            trip1 = detail1.get("trip", {})
            self.assert_eq(trip1.get("status"), "COMPLETED", "Released trip still COMPLETED")
            counts1 = self.count_transactions_by_type(released_trip)
            self.assert_eq(counts1.get("refund", 0), 0, "No refund transaction added")
        
        # Try RELEASE_TO_DRIVER on refunded trip
        r2 = requests.post(f"{BASE_URL}/admin/disputes/{refunded_trip}/resolve",
                          json={
                              "outcome": "RELEASE_TO_DRIVER",
                              "reason": "conflicting"
                          },
                          headers={"Authorization": f"Bearer {self.admin_token}"})
        
        self.assert_eq(r2.status_code, 409, "Conflicting RELEASE on refunded trip returns 409")
        
        # Verify trip still REFUNDED
        detail2 = self.get_dispute_detail(refunded_trip)
        if detail2:
            trip2 = detail2.get("trip", {})
            self.assert_eq(trip2.get("status"), "REFUNDED", "Refunded trip still REFUNDED")
            counts2 = self.count_transactions_by_type(refunded_trip)
            self.assert_eq(counts2.get("customer_payment", 0), 0, "No settlement transactions added")
    
    def test_disputed_protections(self):
        """Test 5: Protection - disputed trip blocks certain actions"""
        self.log("\n" + "="*60)
        self.log("TEST 5: DISPUTED PROTECTIONS")
        self.log("="*60)
        
        trip_id = self.create_disputed_trip("PROTECTION")
        if not trip_id:
            self.log("❌ Failed to create disputed trip")
            return
        
        # Customer cannot confirm delivery
        r1 = requests.post(f"{BASE_URL}/trips/{trip_id}/confirm-delivery",
                          json={},
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        self.assert_eq(r1.status_code, 400, "Customer confirm-delivery blocked (400)")
        if r1.status_code == 400:
            self.assert_in("TRIP_IN_DISPUTE", r1.text, "Error contains TRIP_IN_DISPUTE")
        
        # Customer cannot review
        r2 = requests.post(f"{BASE_URL}/trips/{trip_id}/review",
                          json={
                              "overall": 5,
                              "service_quality": 5,
                              "communication": 5,
                              "on_time": 5
                          },
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        self.assert_eq(r2.status_code, 400, "Customer review blocked (400)")
        if r2.status_code == 400:
            self.assert_in("TRIP_IN_DISPUTE", r2.text, "Error contains TRIP_IN_DISPUTE")
        
        # Driver cannot update status
        r3 = requests.post(f"{BASE_URL}/trips/{trip_id}/status",
                          json={"status": "COMPLETED"},
                          headers={"Authorization": f"Bearer {self.driver_token}"})
        self.assert_eq(r3.status_code, 400, "Driver status update blocked (400)")
        if r3.status_code == 400:
            self.assert_in("TRIP_IN_TERMINAL_STATE", r3.text, "Error contains TRIP_IN_TERMINAL_STATE")
        
        # Customer GET /trips/mine - status remains DISPUTED (no auto-complete)
        r4 = requests.get(f"{BASE_URL}/trips/mine",
                         headers={"Authorization": f"Bearer {self.customer_token}"})
        if r4.status_code == 200:
            trips = r4.json()
            disputed_trip = next((t for t in trips if t["id"] == trip_id), None)
            if disputed_trip:
                self.assert_eq(disputed_trip.get("status"), "DISPUTED", "Trip status remains DISPUTED (no auto-complete)")
        
        # Customer GET /trips/{id} - status remains DISPUTED
        r5 = requests.get(f"{BASE_URL}/trips/{trip_id}",
                         headers={"Authorization": f"Bearer {self.customer_token}"})
        if r5.status_code == 200:
            trip = r5.json()
            self.assert_eq(trip.get("status"), "DISPUTED", "Trip status remains DISPUTED on GET")
        
        # Customer cannot pay again
        r6 = requests.post(f"{BASE_URL}/trips/{trip_id}/pay",
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        self.assert_eq(r6.status_code, 400, "Customer pay blocked (400)")
        if r6.status_code == 400:
            self.assert_in("TRIP_IN_TERMINAL_STATE", r6.text, "Error contains TRIP_IN_TERMINAL_STATE")
        
        # Verify zero settlement transactions
        counts = self.count_transactions_by_type(trip_id)
        self.assert_eq(counts.get("customer_payment", 0), 0, "NO customer_payment for disputed trip")
        self.assert_eq(counts.get("platform_commission", 0), 0, "NO platform_commission for disputed trip")
        self.assert_eq(counts.get("driver_earning", 0), 0, "NO driver_earning for disputed trip")
    
    def test_normal_completion_regression(self):
        """Test 6: Normal completion flow (regression)"""
        self.log("\n" + "="*60)
        self.log("TEST 6: NORMAL COMPLETION REGRESSION")
        self.log("="*60)
        
        # Create shipment
        shipment_data = {
            "title": "Normal Completion Test",
            "description": "Test cargo",
            "category": "general",
            "weight": "100",
            "pickup_location": {
                "address": "مسقط",
                "lat": 23.58,
                "lng": 58.40
            },
            "delivery_location": {
                "address": "صلالة",
                "lat": 17.01,
                "lng": 54.09
            },
            "pickup_date": "2025-02-01",
            "delivery_date": "2025-02-05",
            "vehicle_type": "flatbed"
        }
        
        r1 = requests.post(f"{BASE_URL}/shipments", 
                          json=shipment_data,
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        if r1.status_code != 200:
            self.log(f"❌ Failed to create shipment: {r1.status_code}")
            return
        
        shipment = r1.json()
        shipment_id = shipment["id"]
        
        # Publish
        requests.post(f"{BASE_URL}/shipments/{shipment_id}/publish",
                     headers={"Authorization": f"Bearer {self.customer_token}"})
        
        # Driver bids
        r2 = requests.post(f"{BASE_URL}/shipments/{shipment_id}/bids",
                          json={"price": 40, "note": "test"},
                          headers={"Authorization": f"Bearer {self.driver_token}"})
        bid = r2.json()
        bid_id = bid["id"]
        
        # Customer accepts
        r3 = requests.post(f"{BASE_URL}/bids/{bid_id}/accept",
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        trip = r3.json()
        trip_id = trip["id"]
        
        # Customer pays
        requests.post(f"{BASE_URL}/trips/{trip_id}/pay",
                     headers={"Authorization": f"Bearer {self.customer_token}"})
        
        # Driver advances to POD
        states = [
            "DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "LOADING", "LOADED",
            "IN_TRANSIT", "NEAR_DESTINATION", "DRIVER_ARRIVED_DESTINATION"
        ]
        for state in states:
            requests.post(f"{BASE_URL}/trips/{trip_id}/status",
                         json={"status": state},
                         headers={"Authorization": f"Bearer {self.driver_token}"})
        
        # Submit POD
        requests.post(f"{BASE_URL}/trips/{trip_id}/status",
                     json={
                         "status": "DELIVERED_PENDING_CONFIRMATION",
                         "pod_photo": POD_PHOTO,
                         "pod_notes": "Delivered"
                     },
                     headers={"Authorization": f"Bearer {self.driver_token}"})
        
        # Customer confirms delivery
        r4 = requests.post(f"{BASE_URL}/trips/{trip_id}/confirm-delivery",
                          json={},
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        self.assert_eq(r4.status_code, 200, "Normal confirm-delivery returns 200")
        
        if r4.status_code == 200:
            trip_data = r4.json()
            self.assert_eq(trip_data.get("status"), "COMPLETED", "Trip status = COMPLETED")
        
        # Verify settlement transactions
        counts = self.count_transactions_by_type(trip_id)
        self.assert_eq(counts.get("customer_payment", 0), 1, "Exactly 1 customer_payment")
        self.assert_eq(counts.get("platform_commission", 0), 1, "Exactly 1 platform_commission")
        self.assert_eq(counts.get("driver_earning", 0), 1, "Exactly 1 driver_earning")
        
        # Try duplicate confirm
        r5 = requests.post(f"{BASE_URL}/trips/{trip_id}/confirm-delivery",
                          json={},
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        self.assert_true(r5.status_code in [400, 409], "Duplicate confirm rejected (400 or 409)")
        
        # Verify counts unchanged
        counts_after = self.count_transactions_by_type(trip_id)
        self.assert_eq(counts_after, counts, "Transaction counts unchanged after duplicate confirm")
    
    def test_authorization_and_validation(self):
        """Test authorization and validation"""
        self.log("\n" + "="*60)
        self.log("TEST 7: AUTHORIZATION & VALIDATION")
        self.log("="*60)
        
        if len(self.test_trips) < 1:
            self.log("❌ No test trips available")
            return
        
        trip_id = self.test_trips[0]
        
        # Non-admin (customer) cannot resolve
        r1 = requests.post(f"{BASE_URL}/admin/disputes/{trip_id}/resolve",
                          json={
                              "outcome": "RELEASE_TO_DRIVER",
                              "reason": "test"
                          },
                          headers={"Authorization": f"Bearer {self.customer_token}"})
        self.assert_eq(r1.status_code, 403, "Customer resolve returns 403")
        
        # Invalid outcome
        r2 = requests.post(f"{BASE_URL}/admin/disputes/{trip_id}/resolve",
                          json={
                              "outcome": "PARTIAL",
                              "reason": "test"
                          },
                          headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assert_eq(r2.status_code, 400, "Invalid outcome returns 400")
        if r2.status_code == 400:
            self.assert_in("INVALID_DISPUTE_OUTCOME", r2.text, "Error contains INVALID_DISPUTE_OUTCOME")
        
        # Empty reason
        r3 = requests.post(f"{BASE_URL}/admin/disputes/{trip_id}/resolve",
                          json={
                              "outcome": "RELEASE_TO_DRIVER",
                              "reason": ""
                          },
                          headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assert_eq(r3.status_code, 400, "Empty reason returns 400")
        if r3.status_code == 400:
            self.assert_in("DISPUTE_REASON_REQUIRED", r3.text, "Error contains DISPUTE_REASON_REQUIRED")
        
        # Non-existent trip
        r4 = requests.post(f"{BASE_URL}/admin/disputes/nonexistent-trip-id/resolve",
                          json={
                              "outcome": "RELEASE_TO_DRIVER",
                              "reason": "test"
                          },
                          headers={"Authorization": f"Bearer {self.admin_token}"})
        self.assert_eq(r4.status_code, 404, "Non-existent trip returns 404")
    
    def run_all_tests(self):
        """Run all test scenarios"""
        self.log("\n" + "="*80)
        self.log("DISPUTE RESOLUTION PHASE 1 - BACKEND TESTS")
        self.log("="*80)
        
        # Login
        if not self.login_admin():
            self.log("❌ Admin login failed, aborting tests")
            return
        
        self.customer_token = self.login_otp(CUSTOMER_PHONE, "customer")
        if not self.customer_token:
            self.log("❌ Customer login failed, aborting tests")
            return
        
        self.driver_token = self.login_otp(DRIVER_PHONE, "driver")
        if not self.driver_token:
            self.log("❌ Driver login failed, aborting tests")
            return
        
        # Run tests
        self.test_release_to_driver()
        self.test_full_refund()
        self.test_duplicate_resolution()
        self.test_conflicting_resolution()
        self.test_disputed_protections()
        self.test_normal_completion_regression()
        self.test_authorization_and_validation()
        
        # Summary
        self.log("\n" + "="*80)
        self.log("TEST SUMMARY")
        self.log("="*80)
        self.log(f"✅ PASSED: {self.passed}")
        self.log(f"❌ FAILED: {self.failed}")
        self.log(f"TOTAL: {self.passed + self.failed}")
        
        if self.failed == 0:
            self.log("\n🎉 ALL TESTS PASSED!")
            return 0
        else:
            self.log(f"\n⚠️  {self.failed} TEST(S) FAILED")
            return 1

if __name__ == "__main__":
    runner = TestRunner()
    exit_code = runner.run_all_tests()
    sys.exit(exit_code)
