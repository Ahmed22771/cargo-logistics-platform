#!/usr/bin/env python3
"""
CARGO Pricing Engine Backend Test
Tests the new pricing engine + vehicle_type + advisory price + customer max-offer + bid limit
"""
import os
import sys
import requests
import json
from typing import Optional

# Base URL from environment
BACKEND_URL = os.getenv("REACT_APP_BACKEND_URL", "https://hardened-cargo.preview.emergentagent.com")
BASE_URL = f"{BACKEND_URL}/api"

# Test credentials from /app/memory/test_credentials.md
CUSTOMER_PHONE = "+96890000001"
DRIVER_PHONE = "+96890000002"
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"

# Test coordinates (Oman)
PICKUP_COORDS = {"address": "Muscat", "lat": 23.5859, "lng": 58.4059}
DELIVERY_COORDS = {"address": "Sohar", "lat": 24.3419, "lng": 56.7094}

# Global tokens
customer_token = None
driver_token = None
admin_token = None

def log(msg: str, level: str = "INFO"):
    """Simple logger"""
    print(f"[{level}] {msg}")

def otp_login(phone: str, role: str) -> Optional[str]:
    """Login via OTP and return token"""
    try:
        # Request OTP
        resp = requests.post(f"{BASE_URL}/auth/otp/request", json={"phone": phone, "role": role}, timeout=10)
        if resp.status_code != 200:
            log(f"OTP request failed for {phone}: {resp.status_code} {resp.text}", "ERROR")
            return None
        
        data = resp.json()
        demo_code = data.get("demo_code")
        if not demo_code:
            log(f"No demo_code in OTP response for {phone}", "ERROR")
            return None
        
        log(f"OTP request successful for {phone}, demo_code: {demo_code}")
        
        # Verify OTP
        resp = requests.post(f"{BASE_URL}/auth/otp/verify", 
                           json={"phone": phone, "role": role, "code": demo_code}, 
                           timeout=10)
        if resp.status_code != 200:
            log(f"OTP verify failed for {phone}: {resp.status_code} {resp.text}", "ERROR")
            return None
        
        data = resp.json()
        token = data.get("token")
        if not token:
            log(f"No token in OTP verify response for {phone}", "ERROR")
            return None
        
        log(f"OTP login successful for {phone} (role: {role})")
        return token
    except Exception as e:
        log(f"OTP login exception for {phone}: {e}", "ERROR")
        return None

def admin_login() -> Optional[str]:
    """Admin login and return token"""
    try:
        resp = requests.post(f"{BASE_URL}/auth/admin/login", 
                           json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, 
                           timeout=10)
        if resp.status_code != 200:
            log(f"Admin login failed: {resp.status_code} {resp.text}", "ERROR")
            return None
        
        data = resp.json()
        token = data.get("token")
        if not token:
            log(f"No token in admin login response", "ERROR")
            return None
        
        log(f"Admin login successful")
        return token
    except Exception as e:
        log(f"Admin login exception: {e}", "ERROR")
        return None

def test_pricing_quote():
    """Test 1 & 2: Pricing quote endpoint with different vehicle types"""
    log("\n=== TEST 1 & 2: PRICING QUOTE ===")
    
    headers = {"Authorization": f"Bearer {customer_token}"}
    
    # Test 1: flatbed
    log("Test 1: POST /api/pricing/quote with vehicle_type='flatbed'")
    payload = {
        "pickup_location": PICKUP_COORDS,
        "delivery_location": DELIVERY_COORDS,
        "vehicle_type": "flatbed"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/pricing/quote", json=payload, headers=headers, timeout=10)
        log(f"Response: {resp.status_code}")
        
        if resp.status_code != 200:
            log(f"❌ FAIL: Expected 200, got {resp.status_code}", "ERROR")
            log(f"Response body: {resp.text}", "ERROR")
            return False
        
        data = resp.json()
        log(f"Response body: {json.dumps(data, indent=2)}")
        
        # Verify required fields
        required_fields = ["advisory_price", "pricing_min", "pricing_max", "pricing_currency", "pricing_version", "distance_km"]
        for field in required_fields:
            if field not in data:
                log(f"❌ FAIL: Missing field '{field}' in response", "ERROR")
                return False
        
        # Verify values
        if data["pricing_currency"] != "OMR":
            log(f"❌ FAIL: Expected pricing_currency='OMR', got '{data['pricing_currency']}'", "ERROR")
            return False
        
        if data["pricing_version"] != "rule_based_v1":
            log(f"❌ FAIL: Expected pricing_version='rule_based_v1', got '{data['pricing_version']}'", "ERROR")
            return False
        
        if data["distance_km"] <= 0:
            log(f"❌ FAIL: Expected distance_km > 0, got {data['distance_km']}", "ERROR")
            return False
        
        # Verify advisory_price == round((pricing_min + pricing_max) / 2)
        expected_advisory = round((data["pricing_min"] + data["pricing_max"]) / 2)
        if data["advisory_price"] != expected_advisory:
            log(f"❌ FAIL: advisory_price mismatch. Expected {expected_advisory}, got {data['advisory_price']}", "ERROR")
            return False
        
        log(f"✅ PASS: Test 1 - flatbed pricing quote successful")
        log(f"  distance_km: {data['distance_km']}, advisory_price: {data['advisory_price']}, min: {data['pricing_min']}, max: {data['pricing_max']}")
        
        flatbed_price = data["advisory_price"]
        
        # Test 2: Compare car vs heavy_truck
        log("\nTest 2: Compare vehicle_type='car' vs 'heavy_truck'")
        
        # Test car
        payload["vehicle_type"] = "car"
        resp = requests.post(f"{BASE_URL}/pricing/quote", json=payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: car pricing failed with {resp.status_code}", "ERROR")
            return False
        car_data = resp.json()
        car_price = car_data["advisory_price"]
        log(f"  car advisory_price: {car_price}")
        
        # Test heavy_truck
        payload["vehicle_type"] = "heavy_truck"
        resp = requests.post(f"{BASE_URL}/pricing/quote", json=payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: heavy_truck pricing failed with {resp.status_code}", "ERROR")
            return False
        truck_data = resp.json()
        truck_price = truck_data["advisory_price"]
        log(f"  heavy_truck advisory_price: {truck_price}")
        
        # Verify car < heavy_truck
        if car_price >= truck_price:
            log(f"❌ FAIL: Expected car price ({car_price}) < heavy_truck price ({truck_price})", "ERROR")
            return False
        
        log(f"✅ PASS: Test 2 - Vehicle type changes price correctly (car: {car_price} < heavy_truck: {truck_price})")
        return True
        
    except Exception as e:
        log(f"❌ FAIL: Exception in pricing quote test: {e}", "ERROR")
        return False

def test_create_shipment_snapshot():
    """Test 3, 4, 5: Create shipment with pricing snapshot and clamping"""
    log("\n=== TEST 3, 4, 5: CREATE SHIPMENT SNAPSHOT + CLAMP ===")
    
    headers = {"Authorization": f"Bearer {customer_token}"}
    
    # First get a quote to know the pricing_max
    quote_payload = {
        "pickup_location": PICKUP_COORDS,
        "delivery_location": DELIVERY_COORDS,
        "vehicle_type": "flatbed"
    }
    resp = requests.post(f"{BASE_URL}/pricing/quote", json=quote_payload, headers=headers, timeout=10)
    if resp.status_code != 200:
        log(f"❌ FAIL: Could not get quote for test setup", "ERROR")
        return False, None, None, None
    
    quote = resp.json()
    pricing_max = quote["pricing_max"]
    pricing_min = quote["pricing_min"]
    advisory_price = quote["advisory_price"]
    log(f"Quote: advisory={advisory_price}, min={pricing_min}, max={pricing_max}")
    
    # Test 3: Create shipment with customer_max_offer > pricing_max (should clamp to pricing_max)
    log("\nTest 3: Create shipment with customer_max_offer > pricing_max (should clamp)")
    shipment_payload = {
        "title": "Test Shipment - Clamp High",
        "description": "Testing max offer clamping",
        "pickup_location": PICKUP_COORDS,
        "delivery_location": DELIVERY_COORDS,
        "vehicle_type": "flatbed",
        "customer_max_offer": pricing_max + 500,  # Way above max
        "status": "PUBLISHED"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/shipments", json=shipment_payload, headers=headers, timeout=10)
        log(f"Response: {resp.status_code}")
        
        if resp.status_code != 200:
            log(f"❌ FAIL: Expected 200, got {resp.status_code}", "ERROR")
            log(f"Response body: {resp.text}", "ERROR")
            return False, None, None, None
        
        shipment = resp.json()
        shipment_id = shipment.get("id")
        log(f"Shipment created: {shipment_id}")
        
        # Verify pricing fields exist
        required_fields = ["advisory_price", "pricing_min", "pricing_max", "pricing_currency", "pricing_version", "vehicle_type", "customer_max_offer"]
        for field in required_fields:
            if field not in shipment:
                log(f"❌ FAIL: Missing field '{field}' in shipment", "ERROR")
                return False, None, None, None
        
        # Verify customer_max_offer was clamped to pricing_max
        if shipment["customer_max_offer"] != pricing_max:
            log(f"❌ FAIL: customer_max_offer not clamped. Expected {pricing_max}, got {shipment['customer_max_offer']}", "ERROR")
            return False, None, None, None
        
        # Verify advisory_price is separate and unchanged
        if shipment["advisory_price"] != advisory_price:
            log(f"❌ FAIL: advisory_price changed. Expected {advisory_price}, got {shipment['advisory_price']}", "ERROR")
            return False, None, None, None
        
        log(f"✅ PASS: Test 3 - customer_max_offer clamped to pricing_max ({pricing_max})")
        log(f"  advisory_price: {shipment['advisory_price']}, customer_max_offer: {shipment['customer_max_offer']}")
        
        # Test 4: Create shipment with customer_max_offer < pricing_min (should clamp to pricing_min)
        log("\nTest 4: Create shipment with customer_max_offer < pricing_min (should clamp)")
        shipment_payload["title"] = "Test Shipment - Clamp Low"
        shipment_payload["customer_max_offer"] = pricing_min - 10  # Below min
        
        resp = requests.post(f"{BASE_URL}/shipments", json=shipment_payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: Expected 200, got {resp.status_code}", "ERROR")
            return False, None, None, None
        
        shipment2 = resp.json()
        shipment2_id = shipment2.get("id")
        
        if shipment2["customer_max_offer"] != pricing_min:
            log(f"❌ FAIL: customer_max_offer not clamped up. Expected {pricing_min}, got {shipment2['customer_max_offer']}", "ERROR")
            return False, None, None, None
        
        log(f"✅ PASS: Test 4 - customer_max_offer clamped to pricing_min ({pricing_min})")
        
        # Test 5: Create shipment with NO customer_max_offer (should default to advisory_price)
        log("\nTest 5: Create shipment with NO customer_max_offer (should default to advisory)")
        shipment_payload["title"] = "Test Shipment - Default"
        shipment_payload.pop("customer_max_offer", None)  # Remove the field
        
        resp = requests.post(f"{BASE_URL}/shipments", json=shipment_payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: Expected 200, got {resp.status_code}", "ERROR")
            return False, None, None, None
        
        shipment3 = resp.json()
        shipment3_id = shipment3.get("id")
        
        if shipment3["customer_max_offer"] != advisory_price:
            log(f"❌ FAIL: customer_max_offer not defaulted. Expected {advisory_price}, got {shipment3['customer_max_offer']}", "ERROR")
            return False, None, None, None
        
        log(f"✅ PASS: Test 5 - customer_max_offer defaulted to advisory_price ({advisory_price})")
        
        return True, shipment_id, shipment["customer_max_offer"], shipment3_id
        
    except Exception as e:
        log(f"❌ FAIL: Exception in create shipment test: {e}", "ERROR")
        return False, None, None, None

def test_bid_limit(shipment_id: str, customer_max_offer: float, shipment_default_id: str):
    """Test 6, 7, 8: Bid limit enforcement"""
    log("\n=== TEST 6, 7, 8: BID LIMIT ===")
    
    headers = {"Authorization": f"Bearer {driver_token}"}
    
    # Test 6: Bid OVER limit (should fail with BID_EXCEEDS_MAX_OFFER)
    log(f"\nTest 6: Bid over limit (customer_max_offer + 10)")
    bid_payload = {
        "price": customer_max_offer + 10,
        "note": "Test bid over limit"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/shipments/{shipment_id}/bids", json=bid_payload, headers=headers, timeout=10)
        log(f"Response: {resp.status_code}")
        
        if resp.status_code != 400:
            log(f"❌ FAIL: Expected 400, got {resp.status_code}", "ERROR")
            log(f"Response body: {resp.text}", "ERROR")
            return False
        
        data = resp.json()
        log(f"Response body: {json.dumps(data, indent=2)}")
        
        # Check for BID_EXCEEDS_MAX_OFFER error code
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            error_code = detail.get("code")
            if error_code != "BID_EXCEEDS_MAX_OFFER":
                log(f"❌ FAIL: Expected error code 'BID_EXCEEDS_MAX_OFFER', got '{error_code}'", "ERROR")
                return False
        else:
            log(f"❌ FAIL: Expected detail to be dict with code, got: {detail}", "ERROR")
            return False
        
        log(f"✅ PASS: Test 6 - Bid over limit correctly rejected with BID_EXCEEDS_MAX_OFFER")
        
        # Test 7: Bid AT limit (should succeed) - create fresh shipment for this test
        log(f"\nTest 7: Bid at limit (customer_max_offer exactly)")
        
        # Create new shipment for test 7
        customer_headers = {"Authorization": f"Bearer {customer_token}"}
        shipment_payload = {
            "title": "Test Shipment - Bid At Limit",
            "description": "Testing bid at exact limit",
            "pickup_location": PICKUP_COORDS,
            "delivery_location": DELIVERY_COORDS,
            "vehicle_type": "flatbed",
            "status": "PUBLISHED"
        }
        
        resp = requests.post(f"{BASE_URL}/shipments", json=shipment_payload, headers=customer_headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: Could not create shipment for test 7", "ERROR")
            return False
        
        test7_shipment = resp.json()
        test7_shipment_id = test7_shipment["id"]
        test7_max_offer = test7_shipment["customer_max_offer"]
        
        bid_payload["price"] = test7_max_offer  # Exactly at limit
        bid_payload["note"] = "Test bid at limit"
        
        resp = requests.post(f"{BASE_URL}/shipments/{test7_shipment_id}/bids", json=bid_payload, headers=headers, timeout=10)
        log(f"Response: {resp.status_code}")
        
        if resp.status_code != 200:
            log(f"❌ FAIL: Expected 200, got {resp.status_code}", "ERROR")
            log(f"Response body: {resp.text}", "ERROR")
            return False
        
        log(f"✅ PASS: Test 7 - Bid at limit accepted (max_offer: {test7_max_offer})")
        
        # Test 8: Bid BELOW limit (should succeed)
        # Create a fresh shipment first
        log(f"\nTest 8: Bid below limit")
        
        # Create new shipment for this test
        customer_headers = {"Authorization": f"Bearer {customer_token}"}
        shipment_payload = {
            "title": "Test Shipment - Bid Below",
            "description": "Testing bid below limit",
            "pickup_location": PICKUP_COORDS,
            "delivery_location": DELIVERY_COORDS,
            "vehicle_type": "flatbed",
            "status": "PUBLISHED"
        }
        
        resp = requests.post(f"{BASE_URL}/shipments", json=shipment_payload, headers=customer_headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: Could not create shipment for test 8", "ERROR")
            return False
        
        fresh_shipment = resp.json()
        fresh_shipment_id = fresh_shipment["id"]
        fresh_max_offer = fresh_shipment["customer_max_offer"]
        
        bid_payload["price"] = fresh_max_offer - 5  # Below limit
        bid_payload["note"] = "Test bid below limit"
        
        resp = requests.post(f"{BASE_URL}/shipments/{fresh_shipment_id}/bids", json=bid_payload, headers=headers, timeout=10)
        log(f"Response: {resp.status_code}")
        
        if resp.status_code != 200:
            log(f"❌ FAIL: Expected 200, got {resp.status_code}", "ERROR")
            log(f"Response body: {resp.text}", "ERROR")
            return False
        
        log(f"✅ PASS: Test 8 - Bid below limit accepted")
        return True
        
    except Exception as e:
        log(f"❌ FAIL: Exception in bid limit test: {e}", "ERROR")
        return False

def test_backward_compat():
    """Test 9: Backward compatibility - old shipments without pricing fields"""
    log("\n=== TEST 9: BACKWARD COMPATIBILITY ===")
    
    headers = {"Authorization": f"Bearer {driver_token}"}
    
    try:
        log("Test 9: GET /api/marketplace/shipments (should not error on old shipments)")
        resp = requests.get(f"{BASE_URL}/marketplace/shipments", headers=headers, timeout=10)
        log(f"Response: {resp.status_code}")
        
        if resp.status_code != 200:
            log(f"❌ FAIL: Expected 200, got {resp.status_code}", "ERROR")
            log(f"Response body: {resp.text}", "ERROR")
            return False
        
        shipments = resp.json()
        log(f"Retrieved {len(shipments)} shipments")
        
        # Check if any shipments lack pricing fields (backward compat)
        old_style_count = 0
        for s in shipments:
            if "advisory_price" not in s or "customer_max_offer" not in s:
                old_style_count += 1
        
        log(f"Found {old_style_count} shipments without pricing fields (old-style)")
        
        # Try to bid on an old-style shipment if one exists
        # For now, just verify the endpoint doesn't crash
        log(f"✅ PASS: Test 9 - Marketplace endpoint works with mixed old/new shipments")
        return True
        
    except Exception as e:
        log(f"❌ FAIL: Exception in backward compat test: {e}", "ERROR")
        return False

def test_regression():
    """Test 10: Light regression - full flow"""
    log("\n=== TEST 10: REGRESSION (LIGHT) ===")
    
    try:
        # Customer creates shipment
        log("Step 1: Customer creates shipment")
        customer_headers = {"Authorization": f"Bearer {customer_token}"}
        shipment_payload = {
            "title": "Regression Test Shipment",
            "description": "Full flow test",
            "pickup_location": PICKUP_COORDS,
            "delivery_location": DELIVERY_COORDS,
            "vehicle_type": "flatbed",
            "customer_max_offer": 100,  # Explicit max offer
            "status": "PUBLISHED"
        }
        
        resp = requests.post(f"{BASE_URL}/shipments", json=shipment_payload, headers=customer_headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: Shipment creation failed: {resp.status_code}", "ERROR")
            return False
        
        shipment = resp.json()
        shipment_id = shipment["id"]
        customer_max_offer = shipment["customer_max_offer"]
        log(f"✅ Shipment created: {shipment_id}, max_offer: {customer_max_offer}")
        
        # Driver sees it in marketplace
        log("Step 2: Driver sees shipment in marketplace")
        driver_headers = {"Authorization": f"Bearer {driver_token}"}
        resp = requests.get(f"{BASE_URL}/marketplace/shipments", headers=driver_headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: Marketplace access failed: {resp.status_code}", "ERROR")
            return False
        
        marketplace = resp.json()
        found = any(s["id"] == shipment_id for s in marketplace)
        if not found:
            log(f"❌ FAIL: Shipment not found in marketplace", "ERROR")
            return False
        log(f"✅ Shipment visible in marketplace")
        
        # Driver bids within limit
        log("Step 3: Driver bids within limit")
        bid_payload = {
            "price": customer_max_offer - 5,  # Within limit
            "note": "Regression test bid"
        }
        resp = requests.post(f"{BASE_URL}/shipments/{shipment_id}/bids", json=bid_payload, headers=driver_headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: Bid submission failed: {resp.status_code}", "ERROR")
            log(f"Response: {resp.text}", "ERROR")
            return False
        
        bid = resp.json()
        bid_id = bid["id"]
        log(f"✅ Bid submitted: {bid_id}")
        
        # Customer gets bids
        log("Step 4: Customer gets bids")
        resp = requests.get(f"{BASE_URL}/shipments/{shipment_id}/bids", headers=customer_headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: Get bids failed: {resp.status_code}", "ERROR")
            return False
        
        bids = resp.json()
        found_bid = any(b["id"] == bid_id for b in bids)
        if not found_bid:
            log(f"❌ FAIL: Bid not found in customer's bid list", "ERROR")
            return False
        log(f"✅ Customer sees bid")
        
        # Customer accepts bid
        log("Step 5: Customer accepts bid")
        resp = requests.post(f"{BASE_URL}/bids/{bid_id}/accept", headers=customer_headers, timeout=10)
        if resp.status_code != 200:
            log(f"❌ FAIL: Bid acceptance failed: {resp.status_code}", "ERROR")
            log(f"Response: {resp.text}", "ERROR")
            return False
        
        result = resp.json()
        trip_id = result.get("trip_id") or result.get("id")
        if not trip_id:
            log(f"❌ FAIL: No trip_id in acceptance response", "ERROR")
            log(f"Response keys: {list(result.keys())}", "ERROR")
            return False
        log(f"✅ Bid accepted, trip created: {trip_id}")
        
        log(f"✅ PASS: Test 10 - Full regression flow successful")
        return True
        
    except Exception as e:
        log(f"❌ FAIL: Exception in regression test: {e}", "ERROR")
        return False

def main():
    """Main test runner"""
    global customer_token, driver_token, admin_token
    
    log("=" * 80)
    log("CARGO PRICING ENGINE BACKEND TEST")
    log("=" * 80)
    log(f"Backend URL: {BASE_URL}")
    
    # Setup: Login all users
    log("\n=== SETUP: LOGIN ===")
    customer_token = otp_login(CUSTOMER_PHONE, "customer")
    if not customer_token:
        log("❌ FATAL: Customer login failed", "ERROR")
        sys.exit(1)
    
    driver_token = otp_login(DRIVER_PHONE, "driver")
    if not driver_token:
        log("❌ FATAL: Driver login failed", "ERROR")
        sys.exit(1)
    
    admin_token = admin_login()
    if not admin_token:
        log("❌ FATAL: Admin login failed", "ERROR")
        sys.exit(1)
    
    log("✅ All logins successful\n")
    
    # Run tests
    results = {}
    
    # Test 1 & 2: Pricing quote
    results["pricing_quote"] = test_pricing_quote()
    
    # Test 3, 4, 5: Create shipment snapshot
    success, shipment_id, customer_max_offer, shipment_default_id = test_create_shipment_snapshot()
    results["create_shipment_snapshot"] = success
    
    if success and shipment_id:
        # Test 6, 7, 8: Bid limit
        results["bid_limit"] = test_bid_limit(shipment_id, customer_max_offer, shipment_default_id)
    else:
        log("⚠️ Skipping bid limit tests due to shipment creation failure", "WARN")
        results["bid_limit"] = False
    
    # Test 9: Backward compatibility
    results["backward_compat"] = test_backward_compat()
    
    # Test 10: Regression
    results["regression"] = test_regression()
    
    # Summary
    log("\n" + "=" * 80)
    log("TEST SUMMARY")
    log("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        log(f"{status}: {test_name}")
    
    log(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        log("\n🎉 ALL TESTS PASSED", "SUCCESS")
        sys.exit(0)
    else:
        log(f"\n❌ {total - passed} TEST(S) FAILED", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
