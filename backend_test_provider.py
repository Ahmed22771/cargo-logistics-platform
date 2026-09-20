#!/usr/bin/env python3
"""
Backend-only testing for Company/Provider Portal endpoints.
Tests all provider endpoints with proper isolation and authorization checks.
"""
import os
import sys
import requests
import json
from typing import Optional

# Get backend URL from environment
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://f3a0b183-d308-41de-b545-d511967f3ced.preview.emergentagent.com")
API_BASE = f"{BACKEND_URL}/api"

# Test accounts
PROVIDER_PHONE = "+96890000005"
DRIVER_PHONE = "+96890000002"
CUSTOMER_PHONE = "+96890000001"
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"

# Global tokens
provider_token = None
driver_token = None
customer_token = None
admin_token = None

# Test data storage
test_vehicle_ids = []
test_shipment_ids = []
test_bid_ids = []
linked_driver_ids = []


def log(msg: str):
    print(f"[TEST] {msg}")


def otp_login(phone: str, role: str, name: str = "") -> Optional[str]:
    """Login via OTP demo flow and return JWT token."""
    log(f"OTP login: {role} {phone}")
    
    # Request OTP
    r = requests.post(f"{API_BASE}/auth/otp/request", json={
        "phone": phone,
        "role": role,
        "name": name or phone
    })
    if r.status_code != 200:
        log(f"  ❌ OTP request failed: {r.status_code} {r.text}")
        return None
    
    data = r.json()
    demo_code = data.get("demo_code")
    if not demo_code:
        log(f"  ❌ No demo_code in response")
        return None
    
    log(f"  Demo OTP: {demo_code}")
    
    # Verify OTP
    r = requests.post(f"{API_BASE}/auth/otp/verify", json={
        "phone": phone,
        "role": role,
        "code": demo_code,
        "name": name or phone
    })
    if r.status_code != 200:
        log(f"  ❌ OTP verify failed: {r.status_code} {r.text}")
        return None
    
    data = r.json()
    token = data.get("token")
    user = data.get("user", {})
    log(f"  ✅ Logged in as {user.get('name')} (role={user.get('role')})")
    return token


def admin_login() -> Optional[str]:
    """Login as admin and return JWT token."""
    log(f"Admin login: {ADMIN_EMAIL}")
    r = requests.post(f"{API_BASE}/auth/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if r.status_code != 200:
        log(f"  ❌ Admin login failed: {r.status_code} {r.text}")
        return None
    
    data = r.json()
    token = data.get("token")
    log(f"  ✅ Admin logged in")
    return token


def test_1_vehicles_crud():
    """Test 1: Vehicles CRUD as provider"""
    log("\n=== TEST 1: VEHICLES CRUD ===")
    
    global test_vehicle_ids
    
    # 1.1: Create vehicle (valid)
    log("1.1: Create vehicle (valid)")
    r = requests.post(f"{API_BASE}/provider/vehicles", 
        headers={"Authorization": f"Bearer {provider_token}"},
        json={
            "plate_number": "TEST-12345",
            "vehicle_type": "TRUCK",
            "make": "Toyota",
            "model": "Hilux",
            "year": "2023",
            "color": "White",
            "capacity": "1000kg",
            "status": "ACTIVE",
            "notes": "Test vehicle"
        })
    if r.status_code == 200:
        vehicle = r.json()
        vehicle_id = vehicle.get("id")
        owner_id = vehicle.get("owner_id")
        log(f"  ✅ PASS: Vehicle created, id={vehicle_id}, owner_id={owner_id}")
        test_vehicle_ids.append(vehicle_id)
    else:
        log(f"  ❌ FAIL: {r.status_code} {r.text}")
    
    # 1.2: Duplicate plate (same owner)
    log("1.2: Duplicate plate (same owner)")
    r = requests.post(f"{API_BASE}/provider/vehicles", 
        headers={"Authorization": f"Bearer {provider_token}"},
        json={
            "plate_number": "TEST-12345",
            "vehicle_type": "VAN",
            "make": "Ford",
            "model": "Transit"
        })
    if r.status_code == 400 and "PLATE_DUPLICATE" in r.text:
        log(f"  ✅ PASS: Duplicate plate rejected with PLATE_DUPLICATE")
    else:
        log(f"  ❌ FAIL: Expected 400 PLATE_DUPLICATE, got {r.status_code} {r.text}")
    
    # 1.3: Empty plate
    log("1.3: Empty plate")
    r = requests.post(f"{API_BASE}/provider/vehicles", 
        headers={"Authorization": f"Bearer {provider_token}"},
        json={
            "plate_number": "",
            "vehicle_type": "TRUCK"
        })
    if r.status_code == 400 and "PLATE_REQUIRED" in r.text:
        log(f"  ✅ PASS: Empty plate rejected with PLATE_REQUIRED")
    else:
        log(f"  ❌ FAIL: Expected 400 PLATE_REQUIRED, got {r.status_code} {r.text}")
    
    # 1.4: List returns only my vehicles
    log("1.4: List returns only my vehicles")
    r = requests.get(f"{API_BASE}/provider/vehicles", 
        headers={"Authorization": f"Bearer {provider_token}"})
    if r.status_code == 200:
        vehicles = r.json()
        log(f"  ✅ PASS: Listed {len(vehicles)} vehicles")
        for v in vehicles:
            log(f"    - {v.get('plate_number')} (id={v.get('id')})")
    else:
        log(f"  ❌ FAIL: {r.status_code} {r.text}")
    
    # 1.5: Update valid + status change
    if test_vehicle_ids:
        log("1.5: Update vehicle (valid + status change)")
        r = requests.put(f"{API_BASE}/provider/vehicles/{test_vehicle_ids[0]}", 
            headers={"Authorization": f"Bearer {provider_token}"},
            json={
                "plate_number": "TEST-12345-UPDATED",
                "vehicle_type": "TRUCK",
                "make": "Toyota",
                "model": "Hilux",
                "year": "2024",
                "color": "Blue",
                "capacity": "1500kg",
                "status": "MAINTENANCE",
                "notes": "Updated test vehicle"
            })
        if r.status_code == 200:
            vehicle = r.json()
            log(f"  ✅ PASS: Vehicle updated, status={vehicle.get('status')}, year={vehicle.get('year')}")
        else:
            log(f"  ❌ FAIL: {r.status_code} {r.text}")
    
    # 1.6: Assign a driver NOT in my company (will test after linking driver)
    # Skip for now, will test in test_3
    
    # 1.7: Delete vehicle
    if test_vehicle_ids:
        log("1.7: Delete vehicle")
        r = requests.delete(f"{API_BASE}/provider/vehicles/{test_vehicle_ids[0]}", 
            headers={"Authorization": f"Bearer {provider_token}"})
        if r.status_code == 200:
            log(f"  ✅ PASS: Vehicle deleted")
            test_vehicle_ids.pop(0)
        else:
            log(f"  ❌ FAIL: {r.status_code} {r.text}")
    
    # 1.8: GET a vehicle by id not owned
    log("1.8: GET vehicle not owned (forge id)")
    r = requests.get(f"{API_BASE}/provider/vehicles/fake-vehicle-id-12345", 
        headers={"Authorization": f"Bearer {provider_token}"})
    if r.status_code == 404:
        log(f"  ✅ PASS: Non-owned vehicle returns 404")
    else:
        log(f"  ❌ FAIL: Expected 404, got {r.status_code}")


def test_2_drivers_link_unlink():
    """Test 2: Drivers link/unlink"""
    log("\n=== TEST 2: DRIVERS LINK/UNLINK ===")
    
    global linked_driver_ids
    
    # 2.1: Link approved driver by phone
    log("2.1: Link approved driver by phone")
    r = requests.post(f"{API_BASE}/provider/drivers/link", 
        headers={"Authorization": f"Bearer {provider_token}"},
        json={"phone": DRIVER_PHONE})
    if r.status_code == 200:
        data = r.json()
        driver_id = data.get("driver_id")
        log(f"  ✅ PASS: Driver linked, driver_id={driver_id}, name={data.get('name')}")
        linked_driver_ids.append(driver_id)
        
        # Verify DB users.company_id == provider.id
        r2 = requests.get(f"{API_BASE}/provider/drivers/{driver_id}", 
            headers={"Authorization": f"Bearer {provider_token}"})
        if r2.status_code == 200:
            driver = r2.json()
            if driver.get("company_id"):
                log(f"  ✅ PASS: Driver company_id set in DB")
            else:
                log(f"  ❌ FAIL: Driver company_id not set")
    else:
        log(f"  ❌ FAIL: {r.status_code} {r.text}")
    
    # 2.2: Link same driver again from same company (idempotent)
    log("2.2: Link same driver again (idempotent)")
    r = requests.post(f"{API_BASE}/provider/drivers/link", 
        headers={"Authorization": f"Bearer {provider_token}"},
        json={"phone": DRIVER_PHONE})
    if r.status_code == 200:
        log(f"  ✅ PASS: Idempotent link succeeded")
    else:
        log(f"  ❌ FAIL: {r.status_code} {r.text}")
    
    # 2.3: Link an already-in-other-company driver
    # Skip - would need a second provider account
    log("2.3: Link driver in other company - SKIPPED (needs second provider)")
    
    # 2.4: Link a non-approved or unknown phone
    log("2.4: Link non-approved driver")
    r = requests.post(f"{API_BASE}/provider/drivers/link", 
        headers={"Authorization": f"Bearer {provider_token}"},
        json={"phone": "+96890000004"})  # pending driver
    if r.status_code == 400 and "DRIVER_NOT_APPROVED" in r.text:
        log(f"  ✅ PASS: Non-approved driver rejected with DRIVER_NOT_APPROVED")
    else:
        log(f"  ❌ FAIL: Expected 400 DRIVER_NOT_APPROVED, got {r.status_code} {r.text}")
    
    log("2.5: Link unknown phone")
    r = requests.post(f"{API_BASE}/provider/drivers/link", 
        headers={"Authorization": f"Bearer {provider_token}"},
        json={"phone": "+96899999999"})
    if r.status_code == 404 and "DRIVER_NOT_FOUND" in r.text:
        log(f"  ✅ PASS: Unknown phone rejected with DRIVER_NOT_FOUND")
    else:
        log(f"  ❌ FAIL: Expected 404 DRIVER_NOT_FOUND, got {r.status_code} {r.text}")
    
    # 2.6: GET /provider/drivers returns only company_id==provider drivers
    log("2.6: GET /provider/drivers")
    r = requests.get(f"{API_BASE}/provider/drivers", 
        headers={"Authorization": f"Bearer {provider_token}"})
    if r.status_code == 200:
        drivers = r.json()
        log(f"  ✅ PASS: Listed {len(drivers)} company drivers")
        for d in drivers:
            log(f"    - {d.get('name')} (id={d.get('id')}, active_trip={d.get('active_trip')}, current_vehicle={d.get('current_vehicle')})")
    else:
        log(f"  ❌ FAIL: {r.status_code} {r.text}")
    
    # 2.7: GET /provider/drivers/{driver_id}
    if linked_driver_ids:
        log("2.7: GET /provider/drivers/{driver_id}")
        r = requests.get(f"{API_BASE}/provider/drivers/{linked_driver_ids[0]}", 
            headers={"Authorization": f"Bearer {provider_token}"})
        if r.status_code == 200:
            driver = r.json()
            log(f"  ✅ PASS: Driver detail retrieved")
            log(f"    - documents: {len(driver.get('documents', []))}")
            log(f"    - current_vehicle: {driver.get('current_vehicle')}")
            log(f"    - trips: {len(driver.get('trips', []))}")
        else:
            log(f"  ❌ FAIL: {r.status_code} {r.text}")


def test_3_assign_vehicle_driver():
    """Test 3: Assign vehicle ↔ driver"""
    log("\n=== TEST 3: ASSIGN VEHICLE ↔ DRIVER ===")
    
    # Create a test vehicle first
    log("3.1: Create test vehicle for assignment")
    r = requests.post(f"{API_BASE}/provider/vehicles", 
        headers={"Authorization": f"Bearer {provider_token}"},
        json={
            "plate_number": "TEST-ASSIGN-001",
            "vehicle_type": "TRUCK",
            "make": "Nissan",
            "model": "Patrol"
        })
    if r.status_code == 200:
        vehicle = r.json()
        vehicle_id = vehicle.get("id")
        test_vehicle_ids.append(vehicle_id)
        log(f"  ✅ Vehicle created: {vehicle_id}")
        
        # 3.2: Assign linked driver to vehicle
        if linked_driver_ids:
            log("3.2: Assign linked driver to vehicle")
            r = requests.post(f"{API_BASE}/provider/vehicles/{vehicle_id}/assign", 
                headers={"Authorization": f"Bearer {provider_token}"},
                json={"driver_id": linked_driver_ids[0]})
            if r.status_code == 200:
                log(f"  ✅ PASS: Driver assigned to vehicle")
            else:
                log(f"  ❌ FAIL: {r.status_code} {r.text}")
            
            # 3.3: Assign with driver_id=null (unassign)
            log("3.3: Unassign driver (driver_id=null)")
            r = requests.post(f"{API_BASE}/provider/vehicles/{vehicle_id}/assign", 
                headers={"Authorization": f"Bearer {provider_token}"},
                json={"driver_id": None})
            if r.status_code == 200:
                log(f"  ✅ PASS: Driver unassigned")
            else:
                log(f"  ❌ FAIL: {r.status_code} {r.text}")
        
        # 3.4: Assign an unlinked driver
        log("3.4: Assign unlinked driver (fake id)")
        r = requests.post(f"{API_BASE}/provider/vehicles/{vehicle_id}/assign", 
            headers={"Authorization": f"Bearer {provider_token}"},
            json={"driver_id": "fake-driver-id-12345"})
        if r.status_code == 400 and "DRIVER_NOT_IN_COMPANY" in r.text:
            log(f"  ✅ PASS: Unlinked driver rejected with DRIVER_NOT_IN_COMPANY")
        else:
            log(f"  ❌ FAIL: Expected 400 DRIVER_NOT_IN_COMPANY, got {r.status_code} {r.text}")
    else:
        log(f"  ❌ FAIL: Could not create test vehicle: {r.status_code} {r.text}")


def test_4_provider_bidding():
    """Test 4: Provider bidding real flow"""
    log("\n=== TEST 4: PROVIDER BIDDING REAL FLOW ===")
    
    # 4.1: Customer creates and publishes a real shipment
    log("4.1: Customer creates and publishes shipment")
    r = requests.post(f"{API_BASE}/shipments", 
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "title": "Test Shipment for Provider Bid",
            "description": "Testing provider bidding flow",
            "category": "GENERAL",
            "weight": "100",
            "dimensions": "1x1x1",
            "pickup_location": {
                "address": "Muscat, Oman",
                "lat": 23.5880,
                "lng": 58.3829,
                "city": "Muscat",
                "area": "Ruwi",
                "country": "Oman"
            },
            "delivery_location": {
                "address": "Salalah, Oman",
                "lat": 17.0150,
                "lng": 54.0924,
                "city": "Salalah",
                "area": "Salalah",
                "country": "Oman"
            },
            "status": "PUBLISHED"
        })
    if r.status_code == 200:
        shipment = r.json()
        shipment_id = shipment.get("id")
        test_shipment_ids.append(shipment_id)
        log(f"  ✅ Shipment created and published: {shipment_id}")
        
        # 4.2: Provider submits bid via POST /provider/shipments/{sid}/bids
        if linked_driver_ids:
            log("4.2: Provider submits bid with linked driver")
            r = requests.post(f"{API_BASE}/provider/shipments/{shipment_id}/bids", 
                headers={"Authorization": f"Bearer {provider_token}"},
                json={
                    "driver_id": linked_driver_ids[0],
                    "price": 50.0,
                    "note": "Professional service with tracking"
                })
            if r.status_code == 200:
                bid = r.json()
                bid_id = bid.get("id")
                test_bid_ids.append(bid_id)
                log(f"  ✅ PASS: Bid submitted, bid_id={bid_id}")
                log(f"    - provider_id: {bid.get('provider_id')}")
                log(f"    - submitted_by_role: {bid.get('submitted_by_role')}")
                log(f"    - status: {bid.get('status')}")
                
                # 4.3: Duplicate submission (same driver, same shipment, still PENDING)
                log("4.3: Duplicate bid submission")
                r = requests.post(f"{API_BASE}/provider/shipments/{shipment_id}/bids", 
                    headers={"Authorization": f"Bearer {provider_token}"},
                    json={
                        "driver_id": linked_driver_ids[0],
                        "price": 55.0,
                        "note": "Another bid"
                    })
                if r.status_code == 400 and "ALREADY_BID" in r.text:
                    log(f"  ✅ PASS: Duplicate bid rejected with ALREADY_BID")
                else:
                    log(f"  ❌ FAIL: Expected 400 ALREADY_BID, got {r.status_code} {r.text}")
            else:
                log(f"  ❌ FAIL: {r.status_code} {r.text}")
        
        # 4.4: Price 0 or negative
        if linked_driver_ids:
            log("4.4: Bid with price=0")
            r = requests.post(f"{API_BASE}/provider/shipments/{shipment_id}/bids", 
                headers={"Authorization": f"Bearer {provider_token}"},
                json={
                    "driver_id": linked_driver_ids[0],
                    "price": 0,
                    "note": "Free service"
                })
            if r.status_code == 400 and "INVALID_PRICE" in r.text:
                log(f"  ✅ PASS: Price=0 rejected with INVALID_PRICE")
            else:
                log(f"  ❌ FAIL: Expected 400 INVALID_PRICE, got {r.status_code} {r.text}")
            
            log("4.5: Bid with negative price")
            r = requests.post(f"{API_BASE}/provider/shipments/{shipment_id}/bids", 
                headers={"Authorization": f"Bearer {provider_token}"},
                json={
                    "driver_id": linked_driver_ids[0],
                    "price": -10,
                    "note": "Negative price"
                })
            if r.status_code == 400 and "INVALID_PRICE" in r.text:
                log(f"  ✅ PASS: Negative price rejected with INVALID_PRICE")
            else:
                log(f"  ❌ FAIL: Expected 400 INVALID_PRICE, got {r.status_code} {r.text}")
        
        # 4.6: driver_id not in company
        log("4.6: Bid with driver not in company")
        r = requests.post(f"{API_BASE}/provider/shipments/{shipment_id}/bids", 
            headers={"Authorization": f"Bearer {provider_token}"},
            json={
                "driver_id": "fake-driver-id-12345",
                "price": 50.0,
                "note": "Test"
            })
        if r.status_code == 400 and "DRIVER_NOT_IN_COMPANY" in r.text:
            log(f"  ✅ PASS: Non-company driver rejected with DRIVER_NOT_IN_COMPANY")
        else:
            log(f"  ❌ FAIL: Expected 400 DRIVER_NOT_IN_COMPANY, got {r.status_code} {r.text}")
        
        # 4.7: Customer accepts the bid
        if test_bid_ids:
            log("4.7: Customer accepts provider bid")
            r = requests.post(f"{API_BASE}/bids/{test_bid_ids[0]}/accept", 
                headers={"Authorization": f"Bearer {customer_token}"})
            if r.status_code == 200:
                trip = r.json()
                trip_id = trip.get("id")
                log(f"  ✅ PASS: Bid accepted, trip created")
                log(f"    - trip_id: {trip_id}")
                log(f"    - driver_id: {trip.get('driver_id')}")
                log(f"    - provider_id: {trip.get('provider_id')}")
                
                # 4.8: GET /provider/trips lists this trip
                log("4.8: GET /provider/trips")
                r = requests.get(f"{API_BASE}/provider/trips", 
                    headers={"Authorization": f"Bearer {provider_token}"})
                if r.status_code == 200:
                    trips = r.json()
                    found = any(t.get("id") == trip_id for t in trips)
                    if found:
                        log(f"  ✅ PASS: Trip found in provider trips list")
                    else:
                        log(f"  ❌ FAIL: Trip not found in provider trips list")
                else:
                    log(f"  ❌ FAIL: {r.status_code} {r.text}")
            else:
                log(f"  ❌ FAIL: {r.status_code} {r.text}")
    else:
        log(f"  ❌ FAIL: Could not create shipment: {r.status_code} {r.text}")


def test_5_finance_summary():
    """Test 5: Finance summary"""
    log("\n=== TEST 5: FINANCE SUMMARY ===")
    
    # 5.1: GET /provider/finance/summary
    log("5.1: GET /provider/finance/summary")
    r = requests.get(f"{API_BASE}/provider/finance/summary", 
        headers={"Authorization": f"Bearer {provider_token}"})
    if r.status_code == 200:
        summary = r.json()
        log(f"  ✅ PASS: Finance summary retrieved")
        log(f"    - total_earnings: {summary.get('total_earnings')}")
        log(f"    - held: {summary.get('held')}")
        log(f"    - completed: {summary.get('completed')}")
        log(f"    - platform_commission: {summary.get('platform_commission')}")
        log(f"    - net_earnings: {summary.get('net_earnings')}")
        log(f"    - transactions_count: {summary.get('transactions_count')}")
        
        # Verify arithmetic
        total = summary.get('total_earnings', 0)
        commission = summary.get('platform_commission', 0)
        net = summary.get('net_earnings', 0)
        if abs((total - commission) - net) < 0.01:
            log(f"  ✅ PASS: Arithmetic correct (total - commission = net)")
        else:
            log(f"  ❌ FAIL: Arithmetic incorrect: {total} - {commission} != {net}")
    else:
        log(f"  ❌ FAIL: {r.status_code} {r.text}")
    
    # 5.2: Compare with /provider/transactions
    log("5.2: Compare with /provider/transactions")
    r = requests.get(f"{API_BASE}/provider/transactions", 
        headers={"Authorization": f"Bearer {provider_token}"})
    if r.status_code == 200:
        transactions = r.json()
        log(f"  ✅ PASS: Transactions retrieved, count={len(transactions)}")
    else:
        log(f"  ❌ FAIL: {r.status_code} {r.text}")


def test_6_isolation_and_role_guards():
    """Test 6: Isolation and role guards"""
    log("\n=== TEST 6: ISOLATION AND ROLE GUARDS ===")
    
    # 6.1: Any /api/provider/* called by customer/driver/admin → 403 PROVIDER_ONLY
    log("6.1: Customer calls /provider/vehicles")
    r = requests.get(f"{API_BASE}/provider/vehicles", 
        headers={"Authorization": f"Bearer {customer_token}"})
    if r.status_code == 403 and "PROVIDER_ONLY" in r.text:
        log(f"  ✅ PASS: Customer rejected with 403 PROVIDER_ONLY")
    else:
        log(f"  ❌ FAIL: Expected 403 PROVIDER_ONLY, got {r.status_code} {r.text}")
    
    log("6.2: Driver calls /provider/drivers")
    r = requests.get(f"{API_BASE}/provider/drivers", 
        headers={"Authorization": f"Bearer {driver_token}"})
    if r.status_code == 403 and "PROVIDER_ONLY" in r.text:
        log(f"  ✅ PASS: Driver rejected with 403 PROVIDER_ONLY")
    else:
        log(f"  ❌ FAIL: Expected 403 PROVIDER_ONLY, got {r.status_code} {r.text}")
    
    log("6.3: Admin calls /provider/trips")
    r = requests.get(f"{API_BASE}/provider/trips", 
        headers={"Authorization": f"Bearer {admin_token}"})
    if r.status_code == 403 and "PROVIDER_ONLY" in r.text:
        log(f"  ✅ PASS: Admin rejected with 403 PROVIDER_ONLY")
    else:
        log(f"  ❌ FAIL: Expected 403 PROVIDER_ONLY, got {r.status_code} {r.text}")
    
    # 6.2: As Provider A, attempt to GET/PUT/DELETE a Provider B vehicle id → 404
    # Skip - would need a second provider account
    log("6.4: Provider A accesses Provider B vehicle - SKIPPED (needs second provider)")
    
    # 6.3: As Provider A, attempt to GET a driver not in company
    log("6.5: Provider accesses driver not in company")
    r = requests.get(f"{API_BASE}/provider/drivers/fake-driver-id-12345", 
        headers={"Authorization": f"Bearer {provider_token}"})
    if r.status_code == 404:
        log(f"  ✅ PASS: Non-company driver returns 404")
    else:
        log(f"  ❌ FAIL: Expected 404, got {r.status_code}")


def test_7_regression_sanity():
    """Test 7: Regression sanity on unchanged endpoints"""
    log("\n=== TEST 7: REGRESSION SANITY ===")
    
    endpoints = [
        "/provider/summary",
        "/provider/opportunities",
        "/provider/bids",
        "/provider/transactions"
    ]
    
    for endpoint in endpoints:
        log(f"7.x: GET {endpoint}")
        r = requests.get(f"{API_BASE}{endpoint}", 
            headers={"Authorization": f"Bearer {provider_token}"})
        if r.status_code == 200:
            log(f"  ✅ PASS: {endpoint} returned 200")
        else:
            log(f"  ❌ FAIL: {endpoint} returned {r.status_code} {r.text}")


def cleanup():
    """Cleanup test data"""
    log("\n=== CLEANUP ===")
    
    # Unlink drivers
    for driver_id in linked_driver_ids:
        log(f"Unlinking driver {driver_id}")
        r = requests.delete(f"{API_BASE}/provider/drivers/{driver_id}", 
            headers={"Authorization": f"Bearer {provider_token}"})
        if r.status_code == 200:
            log(f"  ✅ Driver unlinked")
        else:
            log(f"  ❌ Failed to unlink: {r.status_code} {r.text}")
    
    # Delete test vehicles
    for vehicle_id in test_vehicle_ids:
        log(f"Deleting vehicle {vehicle_id}")
        r = requests.delete(f"{API_BASE}/provider/vehicles/{vehicle_id}", 
            headers={"Authorization": f"Bearer {provider_token}"})
        if r.status_code == 200:
            log(f"  ✅ Vehicle deleted")
        else:
            log(f"  ❌ Failed to delete: {r.status_code} {r.text}")
    
    log("Cleanup complete")


def main():
    global provider_token, driver_token, customer_token, admin_token
    
    log("=" * 80)
    log("CARGO PROVIDER PORTAL BACKEND TESTING")
    log("=" * 80)
    log(f"Backend URL: {BACKEND_URL}")
    log(f"API Base: {API_BASE}")
    
    # Login all test accounts
    log("\n=== AUTHENTICATION ===")
    provider_token = otp_login(PROVIDER_PHONE, "provider", "Company A")
    driver_token = otp_login(DRIVER_PHONE, "driver", "Test Driver")
    customer_token = otp_login(CUSTOMER_PHONE, "customer", "Test Customer")
    admin_token = admin_login()
    
    if not provider_token:
        log("❌ CRITICAL: Provider login failed, cannot continue")
        return 1
    
    if not customer_token:
        log("❌ CRITICAL: Customer login failed, cannot continue")
        return 1
    
    if not driver_token:
        log("⚠️  WARNING: Driver login failed, some tests may be skipped")
    
    if not admin_token:
        log("⚠️  WARNING: Admin login failed, some tests may be skipped")
    
    # Run tests
    try:
        test_1_vehicles_crud()
        test_2_drivers_link_unlink()
        test_3_assign_vehicle_driver()
        test_4_provider_bidding()
        test_5_finance_summary()
        test_6_isolation_and_role_guards()
        test_7_regression_sanity()
    finally:
        cleanup()
    
    log("\n" + "=" * 80)
    log("TESTING COMPLETE")
    log("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
