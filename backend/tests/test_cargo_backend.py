"""CARGO backend end-to-end pytest suite."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://shipment-hub-519.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "shmsantec@gmail.com"
ADMIN_PASSWORD = "Admin@12345"

CUSTOMER_PHONE = "+96890000001"
APPROVED_DRIVER_PHONE = "+96890000002"
PENDING_DRIVER_PHONE = "+96890000004"
PROVIDER_PHONE = "+96890000005"


# ---------- helpers ----------
def otp_login(phone, role):
    r = requests.post(f"{API}/auth/otp/request", json={"phone": phone, "role": role})
    assert r.status_code == 200, r.text
    code = r.json()["demo_code"]
    r = requests.post(f"{API}/auth/otp/verify", json={"phone": phone, "role": role, "code": code})
    assert r.status_code == 200, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["role"] == "admin"
    return data["token"]


@pytest.fixture(scope="session")
def customer():
    return otp_login(CUSTOMER_PHONE, "customer")


@pytest.fixture(scope="session")
def approved_driver():
    return otp_login(APPROVED_DRIVER_PHONE, "driver")


@pytest.fixture(scope="session")
def pending_driver():
    return otp_login(PENDING_DRIVER_PHONE, "driver")


# ---------- auth tests ----------
class TestAuth:
    def test_admin_login_success(self, admin_token):
        assert admin_token

    def test_admin_login_bad_password(self):
        r = requests.post(f"{API}/auth/admin/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_otp_request_invalid_role(self):
        r = requests.post(f"{API}/auth/otp/request", json={"phone": "+9689999", "role": "admin"})
        assert r.status_code == 400

    def test_otp_flow_customer(self, customer):
        assert customer["user"]["role"] == "customer"
        assert customer["user"]["phone"] == CUSTOMER_PHONE

    def test_otp_flow_provider(self):
        p = otp_login(PROVIDER_PHONE, "provider")
        assert p["user"]["role"] == "provider"

    def test_me_endpoint(self, customer):
        r = requests.get(f"{API}/auth/me", headers=auth(customer["token"]))
        assert r.status_code == 200
        assert r.json()["id"] == customer["user"]["id"]

    def test_unauthenticated_401(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code in (401, 403)


# ---------- driver verification gating ----------
class TestDriverGating:
    def test_approved_driver_marketplace(self, approved_driver):
        r = requests.get(f"{API}/marketplace/shipments", headers=auth(approved_driver["token"]))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_pending_driver_marketplace_blocked(self, pending_driver):
        r = requests.get(f"{API}/marketplace/shipments", headers=auth(pending_driver["token"]))
        assert r.status_code == 403
        assert "DRIVER_NOT_APPROVED" in r.text

    def test_pending_driver_bid_blocked(self, pending_driver, customer):
        # find any published shipment via customer
        r = requests.get(f"{API}/shipments/mine", headers=auth(customer["token"]))
        assert r.status_code == 200
        pubs = [s for s in r.json() if s["status"] == "PUBLISHED"]
        assert pubs, "need a published shipment"
        sid = pubs[0]["id"]
        r = requests.post(f"{API}/shipments/{sid}/bids", json={"price": 100, "note": ""}, headers=auth(pending_driver["token"]))
        assert r.status_code == 403


# ---------- shipment publish validation ----------
class TestShipmentValidation:
    def test_missing_both(self, customer):
        payload = {"title": "TEST_no_locs", "status": "PUBLISHED"}
        r = requests.post(f"{API}/shipments", json=payload, headers=auth(customer["token"]))
        assert r.status_code == 400
        assert "MISSING_BOTH" in r.text

    def test_missing_pickup(self, customer):
        payload = {"title": "TEST_no_pickup", "status": "PUBLISHED",
                   "delivery_location": {"address": "X", "lat": 23.5, "lng": 58.5}}
        r = requests.post(f"{API}/shipments", json=payload, headers=auth(customer["token"]))
        assert r.status_code == 400
        assert "MISSING_PICKUP" in r.text

    def test_missing_delivery(self, customer):
        payload = {"title": "TEST_no_delivery", "status": "PUBLISHED",
                   "pickup_location": {"address": "X", "lat": 23.5, "lng": 58.5}}
        r = requests.post(f"{API}/shipments", json=payload, headers=auth(customer["token"]))
        assert r.status_code == 400
        assert "MISSING_DELIVERY" in r.text


# ---------- full connected flow ----------
class TestFullFlow:
    state = {}

    def test_01_create_shipment(self, customer):
        payload = {
            "title": "TEST_flow_shipment", "description": "e2e",
            "category": "test", "quantity": "1", "weight": "100",
            "pickup_location": {"address": "Muscat", "lat": 23.61, "lng": 58.54},
            "delivery_location": {"address": "Sohar", "lat": 24.34, "lng": 56.72},
            "pickup_date": "2026-08-01", "pickup_time": "09:00",
            "delivery_date": "2026-08-01", "delivery_time": "17:00",
            "vehicle_type": "flatbed", "required_capacity": "10",
            "expected_price": "200", "status": "PUBLISHED",
        }
        r = requests.post(f"{API}/shipments", json=payload, headers=auth(customer["token"]))
        assert r.status_code == 200, r.text
        s = r.json()
        assert s["status"] == "PUBLISHED"
        assert s["pickup_location"]["lat"] == 23.61
        TestFullFlow.state["shipment_id"] = s["id"]

        # persistence via GET
        r2 = requests.get(f"{API}/shipments/{s['id']}", headers=auth(customer["token"]))
        assert r2.status_code == 200 and r2.json()["title"] == "TEST_flow_shipment"

    def test_02_invalid_price_rejected(self, approved_driver):
        sid = TestFullFlow.state["shipment_id"]
        r = requests.post(f"{API}/shipments/{sid}/bids", json={"price": 0, "note": ""},
                          headers=auth(approved_driver["token"]))
        assert r.status_code == 400
        assert "INVALID_PRICE" in r.text

    def test_03_driver_bids(self, approved_driver):
        sid = TestFullFlow.state["shipment_id"]
        r = requests.post(f"{API}/shipments/{sid}/bids", json={"price": 175, "note": "TEST_bid"},
                          headers=auth(approved_driver["token"]))
        assert r.status_code == 200, r.text
        bid = r.json()
        assert bid["price"] == 175 and bid["status"] == "PENDING"
        TestFullFlow.state["bid_id"] = bid["id"]

    def test_04_customer_sees_bid(self, customer):
        sid = TestFullFlow.state["shipment_id"]
        r = requests.get(f"{API}/shipments/{sid}/bids", headers=auth(customer["token"]))
        assert r.status_code == 200
        bids = r.json()
        assert any(b["id"] == TestFullFlow.state["bid_id"] for b in bids)

    def test_05_customer_accepts_bid(self, customer):
        bid_id = TestFullFlow.state["bid_id"]
        r = requests.post(f"{API}/bids/{bid_id}/accept", headers=auth(customer["token"]))
        assert r.status_code == 200, r.text
        trip = r.json()
        assert trip["status"] == "DRIVER_ASSIGNED"
        TestFullFlow.state["trip_id"] = trip["id"]

        # shipment status updated
        r2 = requests.get(f"{API}/shipments/{TestFullFlow.state['shipment_id']}", headers=auth(customer["token"]))
        assert r2.json()["status"] == "DRIVER_ASSIGNED"

    def test_06_driver_sees_trip(self, approved_driver):
        r = requests.get(f"{API}/trips/mine", headers=auth(approved_driver["token"]))
        assert r.status_code == 200
        trips = r.json()
        assert any(t["id"] == TestFullFlow.state["trip_id"] for t in trips)

    def test_07_driver_advances_status(self, approved_driver):
        tid = TestFullFlow.state["trip_id"]
        flow = ["DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "LOADING", "LOADED",
                "IN_TRANSIT", "NEAR_DESTINATION", "DRIVER_ARRIVED_DESTINATION",
                "DELIVERED_PENDING_CONFIRMATION"]
        for st in flow:
            r = requests.post(f"{API}/trips/{tid}/status", json={"status": st},
                              headers=auth(approved_driver["token"]))
            assert r.status_code == 200, f"{st}: {r.text}"
        assert r.json()["status"] == "DELIVERED_PENDING_CONFIRMATION"

    def test_08_customer_confirms(self, customer):
        tid = TestFullFlow.state["trip_id"]
        r = requests.post(f"{API}/trips/{tid}/confirm-delivery", json={"reference": "TEST_REF"},
                          headers=auth(customer["token"]))
        assert r.status_code == 200
        assert r.json()["status"] == "DELIVERED"

    def test_09_customer_rates(self, customer, approved_driver):
        tid = TestFullFlow.state["trip_id"]
        # get driver rating before
        r_before = requests.get(f"{API}/auth/me", headers=auth(approved_driver["token"]))
        before_count = r_before.json().get("rating_count", 0)

        r = requests.post(f"{API}/trips/{tid}/review",
                          json={"overall": 5, "service_quality": 5, "communication": 5, "on_time": 5, "comment": "great"},
                          headers=auth(customer["token"]))
        assert r.status_code == 200, r.text

        # verify trip completed
        r2 = requests.get(f"{API}/trips/{tid}", headers=auth(customer["token"]))
        assert r2.json()["status"] == "COMPLETED"

        # driver rating incremented
        r_after = requests.get(f"{API}/auth/me", headers=auth(approved_driver["token"]))
        assert r_after.json()["rating_count"] == before_count + 1


# ---------- admin endpoints ----------
class TestAdmin:
    def test_stats(self, admin_token):
        r = requests.get(f"{API}/admin/stats", headers=auth(admin_token))
        assert r.status_code == 200
        d = r.json()
        for k in ("total_shipments", "active_trips", "total_drivers", "customers"):
            assert k in d

    @pytest.mark.parametrize("ep", ["drivers", "shipments", "bids", "trips", "users", "audit-logs"])
    def test_list_endpoints(self, admin_token, ep):
        r = requests.get(f"{API}/admin/{ep}", headers=auth(admin_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_verify_driver_flow(self, admin_token):
        # find pending driver
        r = requests.get(f"{API}/admin/drivers", headers=auth(admin_token))
        drivers = r.json()
        pending = next((d for d in drivers if d["phone"] == PENDING_DRIVER_PHONE), None)
        assert pending
        did = pending["id"]

        # approve
        r = requests.post(f"{API}/admin/drivers/{did}/verify",
                          json={"action": "approve", "notes": "TEST_approve"},
                          headers=auth(admin_token))
        assert r.status_code == 200
        assert r.json()["verification_status"] == "APPROVED"

        # now driver can access marketplace
        drv = otp_login(PENDING_DRIVER_PHONE, "driver")
        r2 = requests.get(f"{API}/marketplace/shipments", headers=auth(drv["token"]))
        assert r2.status_code == 200

        # audit log written
        r3 = requests.get(f"{API}/admin/audit-logs", headers=auth(admin_token))
        assert any(a.get("entity_id") == did and a.get("action") == "driver_approve" for a in r3.json())

        # suspend
        r = requests.post(f"{API}/admin/drivers/{did}/verify",
                          json={"action": "suspend", "notes": "TEST_suspend"},
                          headers=auth(admin_token))
        assert r.status_code == 200
        assert r.json()["verification_status"] == "SUSPENDED"

        # marketplace now blocked
        drv2 = otp_login(PENDING_DRIVER_PHONE, "driver")
        r4 = requests.get(f"{API}/marketplace/shipments", headers=auth(drv2["token"]))
        assert r4.status_code == 403

        # restore to PENDING for repeatability
        requests.post(f"{API}/admin/drivers/{did}/verify",
                      json={"action": "request_changes", "notes": "TEST_reset"},
                      headers=auth(admin_token))


# ---------- authorization ----------
class TestAuthorization:
    def test_customer_cannot_admin(self, customer):
        r = requests.get(f"{API}/admin/stats", headers=auth(customer["token"]))
        assert r.status_code == 403

    def test_unauth_admin_401(self):
        r = requests.get(f"{API}/admin/stats")
        assert r.status_code in (401, 403)

    def test_unauth_shipments_mine_401(self):
        r = requests.get(f"{API}/shipments/mine")
        assert r.status_code in (401, 403)
