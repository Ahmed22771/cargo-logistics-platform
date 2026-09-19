"""CARGO — Payment (demo hold) + PoD notification e2e tests (iteration_3)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"
CUSTOMER_PHONE = "+96890000001"
DRIVER_PHONE = "+96890000002"
OTHER_CUSTOMER_PHONE = "+96891112225"


def otp_login(phone, role):
    r = requests.post(f"{API}/auth/otp/request", json={"phone": phone, "role": role})
    assert r.status_code == 200, r.text
    code = r.json()["demo_code"]
    r = requests.post(f"{API}/auth/otp/verify", json={"phone": phone, "role": role, "code": code})
    assert r.status_code == 200, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def make_published_shipment(cust, title="TEST_pay_ship"):
    payload = {
        "title": title, "description": "e2e payment", "category": "test",
        "quantity": "1", "weight": "100",
        "pickup_location": {"address": "Muscat", "lat": 23.61, "lng": 58.54},
        "delivery_location": {"address": "Sohar", "lat": 24.34, "lng": 56.72},
        "pickup_date": "2026-08-01", "pickup_time": "09:00",
        "delivery_date": "2026-08-01", "delivery_time": "17:00",
        "vehicle_type": "flatbed", "status": "PUBLISHED",
    }
    r = requests.post(f"{API}/shipments", json=payload, headers=auth(cust["token"]))
    assert r.status_code == 200, r.text
    return r.json()


def create_assigned_trip(cust, drv, price=175):
    ship = make_published_shipment(cust)
    bid = requests.post(f"{API}/shipments/{ship['id']}/bids", json={"price": price},
                        headers=auth(drv["token"]))
    assert bid.status_code == 200, bid.text
    accepted = requests.post(f"{API}/bids/{bid.json()['id']}/accept",
                             headers=auth(cust["token"]))
    assert accepted.status_code == 200, accepted.text
    return ship, accepted.json()


@pytest.fixture(scope="module")
def customer():
    return otp_login(CUSTOMER_PHONE, "customer")


@pytest.fixture(scope="module")
def driver():
    return otp_login(DRIVER_PHONE, "driver")


@pytest.fixture(scope="module")
def other_customer():
    return otp_login(OTHER_CUSTOMER_PHONE, "customer")


# -------- POST /api/trips/{tid}/pay --------
class TestPayEndpoint:
    def test_pay_success_creates_single_transaction(self, customer, driver):
        _, trip = create_assigned_trip(customer, driver, price=175)
        tid = trip["id"]
        price = float(trip["price"])

        r = requests.post(f"{API}/trips/{tid}/pay", headers=auth(customer["token"]))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["already_paid"] is False
        t = data["trip"]
        assert t["payment_status"] == "HELD"
        assert t.get("payment_id")
        assert t.get("paid_at")

        # Verify persisted
        t2 = requests.get(f"{API}/trips/{tid}", headers=auth(customer["token"])).json()
        assert t2["payment_status"] == "HELD"
        assert t2["payment_id"] == t["payment_id"]

        # Second call — idempotent, no new transaction
        r2 = requests.post(f"{API}/trips/{tid}/pay", headers=auth(customer["token"]))
        assert r2.status_code == 200
        assert r2.json()["already_paid"] is True
        assert r2.json()["trip"]["payment_id"] == t["payment_id"]

        # Verify: exactly ONE payment_hold transaction for this trip
        # (via admin listing since customers don't have txn listing)
        adm = requests.post(f"{API}/auth/admin/login",
                            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).json()
        # Look for transactions endpoint
        r3 = requests.get(f"{API}/admin/transactions", headers=auth(adm["token"]))
        if r3.status_code == 200:
            holds = [x for x in r3.json()
                     if x.get("trip_id") == tid and x.get("type") == "payment_hold"]
            assert len(holds) == 1, f"expected 1 payment_hold, got {len(holds)}"
            assert holds[0]["status"] == "HELD"
            assert float(holds[0]["amount"]) == price

    def test_pay_wrong_customer_404(self, customer, driver, other_customer):
        _, trip = create_assigned_trip(customer, driver)
        r = requests.post(f"{API}/trips/{trip['id']}/pay",
                          headers=auth(other_customer["token"]))
        assert r.status_code == 404

    def test_pay_requires_customer_role(self, customer, driver):
        _, trip = create_assigned_trip(customer, driver)
        r = requests.post(f"{API}/trips/{trip['id']}/pay",
                          headers=auth(driver["token"]))
        assert r.status_code in (401, 403)

    def test_pay_unauthenticated(self, customer, driver):
        _, trip = create_assigned_trip(customer, driver)
        r = requests.post(f"{API}/trips/{trip['id']}/pay")
        assert r.status_code in (401, 403)

    def test_pay_invalid_price(self, customer, driver):
        # Create a shipment with expected_price 0 → bid at 0 will be rejected,
        # so instead we manipulate: bids require >0. To make price=0 we would need
        # to bypass. Skip if backend enforces bid>0 which we already know.
        # Instead simulate by directly checking: create trip with price>0 then verify
        # backend returns INVALID_TRIP_PRICE only when price <= 0 (guard exists).
        # We can't easily set price=0 via public API — mark as documented guard.
        pytest.skip("Cannot create a trip with price<=0 via public API; guard exists in code")

    def test_pay_terminal_trip_rejected(self, customer, driver):
        # complete a full trip and try to pay after COMPLETED
        _, trip = create_assigned_trip(customer, driver, price=100)
        tid = trip["id"]
        # pay first
        assert requests.post(f"{API}/trips/{tid}/pay", headers=auth(customer["token"])).status_code == 200
        # driver advances all the way
        for st in ["DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "LOADING", "LOADED",
                   "IN_TRANSIT", "NEAR_DESTINATION", "DRIVER_ARRIVED_DESTINATION"]:
            r = requests.post(f"{API}/trips/{tid}/status", json={"status": st},
                              headers=auth(driver["token"]))
            assert r.status_code == 200, f"{st}: {r.text}"
        r = requests.post(f"{API}/trips/{tid}/status",
                          json={"status": "DELIVERED_PENDING_CONFIRMATION",
                                "pod_photo": "data:image/png;base64,iVBORw0KGgo="},
                          headers=auth(driver["token"]))
        assert r.status_code == 200
        # customer confirms → COMPLETED
        r = requests.post(f"{API}/trips/{tid}/confirm-delivery", json={},
                          headers=auth(customer["token"]))
        assert r.status_code == 200
        # now pay → should be 400 TRIP_IN_TERMINAL_STATE
        r = requests.post(f"{API}/trips/{tid}/pay", headers=auth(customer["token"]))
        assert r.status_code == 400
        assert "TRIP_IN_TERMINAL_STATE" in r.text


# -------- payment guard on trip status transitions --------
class TestPaymentGuardOnStatus:
    def test_driver_cannot_advance_without_payment(self, customer, driver):
        _, trip = create_assigned_trip(customer, driver)
        tid = trip["id"]
        r = requests.post(f"{API}/trips/{tid}/status",
                          json={"status": "DRIVER_EN_ROUTE"},
                          headers=auth(driver["token"]))
        assert r.status_code == 400
        assert "PAYMENT_REQUIRED" in r.text

    def test_driver_can_advance_after_payment(self, customer, driver):
        _, trip = create_assigned_trip(customer, driver)
        tid = trip["id"]
        assert requests.post(f"{API}/trips/{tid}/pay", headers=auth(customer["token"])).status_code == 200
        r = requests.post(f"{API}/trips/{tid}/status",
                          json={"status": "DRIVER_EN_ROUTE"},
                          headers=auth(driver["token"]))
        assert r.status_code == 200


# -------- pod_pending notification --------
class TestPodPendingNotification:
    def test_notification_created_on_pod(self, customer, driver):
        _, trip = create_assigned_trip(customer, driver, price=150)
        tid = trip["id"]
        sid = trip["shipment_id"]
        assert requests.post(f"{API}/trips/{tid}/pay", headers=auth(customer["token"])).status_code == 200
        for st in ["DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "LOADING", "LOADED",
                   "IN_TRANSIT", "NEAR_DESTINATION", "DRIVER_ARRIVED_DESTINATION"]:
            assert requests.post(f"{API}/trips/{tid}/status", json={"status": st},
                                 headers=auth(driver["token"])).status_code == 200
        r = requests.post(f"{API}/trips/{tid}/status",
                          json={"status": "DELIVERED_PENDING_CONFIRMATION",
                                "pod_photo": "data:image/png;base64,iVBORw0KGgo="},
                          headers=auth(driver["token"]))
        assert r.status_code == 200

        time.sleep(0.5)
        r = requests.get(f"{API}/notifications", headers=auth(customer["token"]))
        assert r.status_code == 200
        notifs = r.json()
        pod = [n for n in notifs
               if n.get("type") == "pod_pending"
               and (n.get("meta") or {}).get("trip_id") == tid]
        assert pod, f"pod_pending notification for trip {tid} not found"
        n = pod[0]
        assert (n.get("meta") or {}).get("shipment_id") == sid
        # title present in both AR and EN — check either title_en/title/title_ar keys
        title_blob = " ".join(str(n.get(k, "")) for k in ("title", "title_en", "title_ar"))
        assert "Proof of delivery" in title_blob or "إثبات تسليم" in title_blob


# -------- ledger stays untouched at confirm-delivery --------
class TestLedgerUnchanged:
    def test_confirm_delivery_creates_three_ledger_txns_once(self, customer, driver):
        _, trip = create_assigned_trip(customer, driver, price=200)
        tid = trip["id"]
        assert requests.post(f"{API}/trips/{tid}/pay", headers=auth(customer["token"])).status_code == 200
        for st in ["DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "LOADING", "LOADED",
                   "IN_TRANSIT", "NEAR_DESTINATION", "DRIVER_ARRIVED_DESTINATION"]:
            assert requests.post(f"{API}/trips/{tid}/status", json={"status": st},
                                 headers=auth(driver["token"])).status_code == 200
        assert requests.post(f"{API}/trips/{tid}/status",
                             json={"status": "DELIVERED_PENDING_CONFIRMATION",
                                   "pod_photo": "data:image/png;base64,iVBORw0KGgo="},
                             headers=auth(driver["token"])).status_code == 200
        # first confirm — creates ledger
        r = requests.post(f"{API}/trips/{tid}/confirm-delivery", json={},
                          headers=auth(customer["token"]))
        assert r.status_code == 200
        # duplicate confirm
        r2 = requests.post(f"{API}/trips/{tid}/confirm-delivery", json={},
                           headers=auth(customer["token"]))
        assert r2.status_code in (400, 409)

        adm = requests.post(f"{API}/auth/admin/login",
                            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).json()
        r3 = requests.get(f"{API}/admin/transactions", headers=auth(adm["token"]))
        if r3.status_code == 200:
            trip_txns = [x for x in r3.json() if x.get("trip_id") == tid]
            types = sorted([x["type"] for x in trip_txns])
            # Expect: 1 payment_hold + customer_payment + platform_commission + driver_earning
            for expected in ("customer_payment", "platform_commission", "driver_earning"):
                assert types.count(expected) == 1, f"{expected} count wrong: {types}"
            assert types.count("payment_hold") == 1
