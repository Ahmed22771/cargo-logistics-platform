from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import random
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Response, Request
from pymongo import ReturnDocument
from starlette.middleware.cors import CORSMiddleware

from database import db, ensure_indexes
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_roles, validate_secrets,
)
from otp_service import (
    request_otp as otp_service_request, verify_otp_code,
    validate_otp_security, is_production as _otp_is_production,
)
from seed import run_seed
from models import (
    OtpRequest, OtpVerify, AdminLogin, ProfileUpdate, DocumentSubmit,
    ShipmentCreate, BidCreate, TripStatusUpdate, DeliveryConfirm, ReviewCreate, VerifyAction, DisputeCreate,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cargo")

app = FastAPI(title="CARGO API")
api = APIRouter(prefix="/api")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return str(uuid.uuid4())


# ---------- helpers ----------
async def create_notification(user_id, type_, title_ar, title_en, body_ar="", body_en="", meta=None):
    await db.notifications.insert_one({
        "id": uid(), "user_id": user_id, "type": type_,
        "title_ar": title_ar, "title_en": title_en,
        "body_ar": body_ar, "body_en": body_en,
        "read": False, "meta": meta or {}, "created_at": now_iso(),
    })


async def audit(admin, action, entity, entity_id, result="success"):
    await db.audit_logs.insert_one({
        "id": uid(), "admin_id": admin["id"], "admin_name": admin.get("name", ""),
        "actor_id": admin["id"], "actor_name": admin.get("name", ""), "actor_role": admin.get("role", ""),
        "action": action, "entity": entity, "entity_id": entity_id,
        "result": result, "timestamp": now_iso(),
    })


def clean(doc):
    if doc:
        doc.pop("_id", None)
        doc.pop("password_hash", None)
    return doc


async def can_access_shipment(shipment: dict, user: dict) -> bool:
    """Apply resource-level access rules independently of frontend routing."""
    if user["role"] == "admin":
        return True
    if user["role"] == "customer":
        return shipment["customer_id"] == user["id"]
    if user["role"] == "driver":
        if shipment.get("assigned_driver_id") == user["id"]:
            return True
        # A driver who has submitted a bid is legitimately participating, but no
        # other driver may fetch an arbitrary customer's shipment by id.
        return bool(await db.bids.find_one({"shipment_id": shipment["id"], "driver_id": user["id"]}))
    if user["role"] == "provider":
        return bool(await db.trips.find_one({"shipment_id": shipment["id"], "provider_id": user["id"]}))
    return False


def can_access_trip(trip: dict, user: dict) -> bool:
    if user["role"] == "admin":
        return True
    if user["role"] == "customer":
        return trip["customer_id"] == user["id"]
    if user["role"] == "driver":
        return trip["driver_id"] == user["id"]
    if user["role"] == "provider":
        return trip.get("provider_id") == user["id"]
    return False


# ================= AUTH =================
@api.get("/")
async def root():
    return {"message": "CARGO API running"}


def _client_ip(request: Request):
    """Best-effort client IP for OTP rate limiting (ingress sets X-Forwarded-For)."""
    fwd = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if fwd:
        return fwd
    return request.client.host if request.client else None


@api.post("/auth/otp/request")
async def otp_request(body: OtpRequest, request: Request):
    # Thin HTTP adapter — all lifecycle/rate-limit/provider logic lives in otp_service.
    return await otp_service_request(body.phone, body.role, ip=_client_ip(request))


@api.post("/auth/otp/verify")
async def otp_verify(body: OtpVerify, response: Response, request: Request):
    # Validates + consumes the OTP (expiry / single-use / attempt budget / rate limits)
    # inside otp_service; user/session creation below is unchanged.
    await verify_otp_code(body.phone, body.role, body.code, ip=_client_ip(request))

    user = await db.users.find_one({"phone": body.phone, "role": body.role})
    if not user:
        new = {
            "id": uid(), "role": body.role, "name": body.name or body.phone,
            "phone": body.phone, "email": "", "created_at": now_iso(),
        }
        if body.role == "driver":
            new.update({"verification_status": "DRAFT", "rating": 0, "rating_count": 0,
                        "completed_trips": 0, "vehicle": {}, "documents": []})
        if body.role == "provider":
            new.update({"company_name": "", "cr_number": "", "service_areas": [],
                        "company_role": "COMPANY_ADMIN", "verification_status": "DRAFT"})
        await db.users.insert_one(new)
        user = new
    else:
        raw_status = (user.get("status") or "active").lower()
        if raw_status == "suspended":
            raise HTTPException(status_code=403, detail="ACCOUNT_SUSPENDED")
        if raw_status in ("disabled", "inactive"):
            raise HTTPException(status_code=403, detail="ACCOUNT_DISABLED")
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": now_iso()}})
    user["last_login"] = now_iso()
    token = create_access_token(user["id"], user["role"])
    return {"token": token, "user": clean(dict(user))}


@api.post("/auth/admin/login")
async def admin_login(body: AdminLogin):
    user = await db.users.find_one({"email": body.email.lower(), "role": "admin"})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    raw_status = (user.get("status") or "active").lower()
    if raw_status == "suspended":
        raise HTTPException(status_code=403, detail="ACCOUNT_SUSPENDED")
    if raw_status in ("disabled", "inactive"):
        raise HTTPException(status_code=403, detail="ACCOUNT_DISABLED")
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": now_iso()}})
    token = create_access_token(user["id"], "admin")
    return {"token": token, "user": clean(dict(user))}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return clean(dict(user))


# ================= PROFILE =================
@api.put("/profile")
async def update_profile(body: ProfileUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = now_iso()
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    updated = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return updated


@api.post("/driver/documents")
async def submit_documents(body: DocumentSubmit, user: dict = Depends(require_roles("driver"))):
    docs = []
    for d in body.documents:
        docs.append({
            "type": d.get("type"), "status": "PENDING", "reference": d.get("reference", ""),
            "expiry": d.get("expiry", ""), "notes": "", "submitted_at": now_iso(), "reviewed_at": None,
        })
    updates = {"documents": docs, "verification_status": "UNDER_REVIEW", "updated_at": now_iso()}
    if body.vehicle:
        updates["vehicle"] = body.vehicle
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    admins = await db.users.find({"role": "admin"}).to_list(10)
    for a in admins:
        await create_notification(a["id"], "verification", "طلب توثيق جديد", "New verification request",
                                  f"السائق {user.get('name')} قدّم مستنداته", f"Driver {user.get('name')} submitted documents",
                                  {"driver_id": user["id"]})
    updated = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return updated


# ================= SHIPMENTS (customer) =================
@api.post("/shipments")
async def create_shipment(body: ShipmentCreate, user: dict = Depends(require_roles("customer"))):
    status = "PUBLISHED" if body.status == "PUBLISHED" else "DRAFT"
    if status == "PUBLISHED":
        if not body.pickup_location and not body.delivery_location:
            raise HTTPException(status_code=400, detail="MISSING_BOTH")
        if not body.pickup_location:
            raise HTTPException(status_code=400, detail="MISSING_PICKUP")
        if not body.delivery_location:
            raise HTTPException(status_code=400, detail="MISSING_DELIVERY")
    data = body.model_dump()
    data.pop("status", None)
    if data.get("pickup_location"):
        data["pickup_location"] = dict(data["pickup_location"])
    if data.get("delivery_location"):
        data["delivery_location"] = dict(data["delivery_location"])
    doc = {
        "id": uid(), "customer_id": user["id"], "customer_name": user.get("name", ""),
        "status": status, "accepted_bid_id": None, "assigned_driver_id": None, "trip_id": None,
        "created_at": now_iso(), "updated_at": now_iso(), **data,
    }
    await db.shipments.insert_one(doc)
    return clean(dict(doc))


@api.get("/shipments/mine")
async def my_shipments(user: dict = Depends(require_roles("customer"))):
    docs = await db.shipments.find({"customer_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@api.get("/shipments/{sid}")
async def get_shipment(sid: str, user: dict = Depends(get_current_user)):
    s = await db.shipments.find_one({"id": sid}, {"_id": 0})
    if not s or not await can_access_shipment(s, user):
        raise HTTPException(status_code=404, detail="Shipment not found")
    return s


@api.put("/shipments/{sid}")
async def update_shipment(sid: str, body: ShipmentCreate, user: dict = Depends(require_roles("customer"))):
    s = await db.shipments.find_one({"id": sid})
    if not s or s["customer_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if s["status"] not in ("DRAFT", "PUBLISHED"):
        raise HTTPException(status_code=400, detail="Cannot edit shipment in current state")
    data = body.model_dump()
    new_status = "PUBLISHED" if data.pop("status", "DRAFT") == "PUBLISHED" else s["status"]
    if new_status == "PUBLISHED":
        if not data.get("pickup_location") and not data.get("delivery_location"):
            raise HTTPException(status_code=400, detail="MISSING_BOTH")
        if not data.get("pickup_location"):
            raise HTTPException(status_code=400, detail="MISSING_PICKUP")
        if not data.get("delivery_location"):
            raise HTTPException(status_code=400, detail="MISSING_DELIVERY")
    if data.get("pickup_location"):
        data["pickup_location"] = dict(data["pickup_location"])
    if data.get("delivery_location"):
        data["delivery_location"] = dict(data["delivery_location"])
    data["status"] = new_status
    data["updated_at"] = now_iso()
    await db.shipments.update_one({"id": sid}, {"$set": data})
    return await db.shipments.find_one({"id": sid}, {"_id": 0})


@api.post("/shipments/{sid}/publish")
async def publish_shipment(sid: str, user: dict = Depends(require_roles("customer"))):
    s = await db.shipments.find_one({"id": sid})
    if not s or s["customer_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if not s.get("pickup_location") and not s.get("delivery_location"):
        raise HTTPException(status_code=400, detail="MISSING_BOTH")
    if not s.get("pickup_location"):
        raise HTTPException(status_code=400, detail="MISSING_PICKUP")
    if not s.get("delivery_location"):
        raise HTTPException(status_code=400, detail="MISSING_DELIVERY")
    await db.shipments.update_one({"id": sid}, {"$set": {"status": "PUBLISHED", "updated_at": now_iso()}})
    return await db.shipments.find_one({"id": sid}, {"_id": 0})


@api.delete("/shipments/{sid}")
async def cancel_shipment(sid: str, user: dict = Depends(require_roles("customer"))):
    s = await db.shipments.find_one({"id": sid})
    if not s or s["customer_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if s["status"] not in ("DRAFT", "PUBLISHED", "BIDDING"):
        raise HTTPException(status_code=400, detail="Cannot cancel shipment in current state")
    result = await db.shipments.update_one(
        {"id": sid, "customer_id": user["id"], "status": {"$in": ["DRAFT", "PUBLISHED", "BIDDING"]}},
        {"$set": {"status": "CANCELLED", "updated_at": now_iso()}},
    )
    if result.modified_count != 1:
        raise HTTPException(status_code=400, detail="Cannot cancel shipment in current state")
    await db.bids.update_many(
        {"shipment_id": sid, "status": "PENDING"},
        {"$set": {"status": "CANCELLED", "updated_at": now_iso()}},
    )
    await audit(user, "shipment_cancelled", "shipment", sid)
    return {"success": True}


# ================= MARKETPLACE (driver) =================
@api.get("/marketplace/shipments")
async def marketplace(user: dict = Depends(require_roles("driver"))):
    if user.get("verification_status") != "APPROVED":
        raise HTTPException(status_code=403, detail="DRIVER_NOT_APPROVED")
    docs = await db.shipments.find(
        {"status": {"$in": ["PUBLISHED", "BIDDING"]}}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    # annotate whether this driver already bid
    my_bids = await db.bids.find({"driver_id": user["id"]}, {"_id": 0}).to_list(1000)
    bid_shipments = {b["shipment_id"] for b in my_bids}
    for d in docs:
        d["already_bid"] = d["id"] in bid_shipments
    return docs


@api.post("/shipments/{sid}/bids")
async def submit_bid(sid: str, body: BidCreate, user: dict = Depends(require_roles("driver"))):
    if user.get("verification_status") != "APPROVED":
        raise HTTPException(status_code=403, detail="DRIVER_NOT_APPROVED")
    if body.price is None or body.price <= 0:
        raise HTTPException(status_code=400, detail="INVALID_PRICE")
    s = await db.shipments.find_one({"id": sid})
    if not s or s["status"] not in ("PUBLISHED", "BIDDING"):
        raise HTTPException(status_code=400, detail="Shipment not open for bids")
    existing = await db.bids.find_one({"shipment_id": sid, "driver_id": user["id"], "status": "PENDING"})
    if existing:
        raise HTTPException(status_code=400, detail="ALREADY_BID")
    # Regulatory eligibility gate (confirmed rules only: app license + driver training).
    from compliance import check_driver_eligibility, log_eligibility_blocked
    elig = await check_driver_eligibility(user)
    if not elig["eligible"]:
        await log_eligibility_blocked(user, "shipment", sid, elig)
        raise HTTPException(status_code=403, detail={"code": "NOT_ELIGIBLE", "reasons": elig["reasons"]})
    bid = {
        "id": uid(), "shipment_id": sid, "driver_id": user["id"], "driver_name": user.get("name", ""),
        "provider_id": None, "price": body.price, "note": body.note or "", "status": "PENDING",
        "driver_rating": user.get("rating", 0), "driver_rating_count": user.get("rating_count", 0),
        "driver_completed_trips": user.get("completed_trips", 0),
        "driver_vehicle": user.get("vehicle", {}), "driver_verification": user.get("verification_status"),
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.bids.insert_one(bid)
    if s["status"] == "PUBLISHED":
        await db.shipments.update_one({"id": sid}, {"$set": {"status": "BIDDING", "updated_at": now_iso()}})
    await create_notification(s["customer_id"], "new_bid", "عرض جديد على شحنتك", "New bid on your shipment",
                              f"عرض بقيمة {body.price} ر.ع على «{s['title']}»", f"A bid of OMR {body.price} on \"{s['title']}\"",
                              {"shipment_id": sid, "bid_id": bid["id"], "entity_type": "shipment", "entity_id": sid})
    return clean(dict(bid))


@api.get("/driver/bids")
async def driver_bids(user: dict = Depends(require_roles("driver"))):
    bids = await db.bids.find({"driver_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for b in bids:
        s = await db.shipments.find_one({"id": b["shipment_id"]}, {"_id": 0})
        b["shipment"] = s
    return bids


# ================= BIDS (customer) =================
@api.get("/shipments/{sid}/bids")
async def shipment_bids(sid: str, user: dict = Depends(get_current_user)):
    s = await db.shipments.find_one({"id": sid})
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    role = user.get("role")
    if role == "admin":
        # Admins may view bids per their existing admin permissions.
        pass
    elif role == "customer":
        # A customer may only view bids on their own shipment.
        if s["customer_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        # Drivers/providers must not enumerate competitors' bids on shipments
        # they don't own. They use /driver/bids and /provider/bids for their own.
        raise HTTPException(status_code=403, detail="Forbidden")
    bids = await db.bids.find({"shipment_id": sid}, {"_id": 0}).sort("price", 1).to_list(500)
    return bids


@api.post("/bids/{bid_id}/accept")
async def accept_bid(bid_id: str, user: dict = Depends(require_roles("customer"))):
    bid = await db.bids.find_one({"id": bid_id})
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    if bid.get("status") != "PENDING":
        raise HTTPException(status_code=400, detail="Bid is not pending")
    driver = await db.users.find_one({"id": bid["driver_id"]}, {"_id": 0, "password_hash": 0})
    if not driver or driver.get("verification_status") != "APPROVED" or (driver.get("status") or "active").lower() in ("inactive", "suspended"):
        raise HTTPException(status_code=400, detail="Driver is not eligible")

    # Regulatory eligibility re-check at assignment (driver + provider if a company bid).
    from compliance import check_driver_eligibility, check_provider_eligibility, log_eligibility_blocked
    elig = await check_driver_eligibility(driver)
    reasons = list(elig["reasons"])
    if bid.get("provider_id"):
        provider = await db.users.find_one({"id": bid["provider_id"]}, {"_id": 0, "password_hash": 0})
        reasons += (await check_provider_eligibility(provider or {}))["reasons"]
    # De-duplicate identical reason codes (application gate can appear twice).
    seen = set()
    reasons = [r for r in reasons if not (r["code"] in seen or seen.add(r["code"]))]
    if reasons:
        await log_eligibility_blocked(user, "shipment", bid["shipment_id"], {"eligible": False, "reasons": reasons})
        raise HTTPException(status_code=403, detail={"code": "NOT_ELIGIBLE", "reasons": reasons})

    trip_id = uid()
    # This conditional update is the acceptance lock: only one request can reserve
    # an open shipment, so competing bids cannot create more than one active trip.
    s = await db.shipments.find_one_and_update(
        {"id": bid["shipment_id"], "customer_id": user["id"], "status": {"$in": ["PUBLISHED", "BIDDING"]}, "accepted_bid_id": None},
        {"$set": {"status": "DRIVER_ASSIGNED", "accepted_bid_id": bid_id, "assigned_driver_id": bid["driver_id"], "trip_id": trip_id, "updated_at": now_iso()}},
        return_document=ReturnDocument.BEFORE,
    )
    if not s:
        raise HTTPException(status_code=400, detail="Shipment is not available for bid acceptance")

    claimed_bid = await db.bids.update_one(
        {"id": bid_id, "status": "PENDING"},
        {"$set": {"status": "ACCEPTED", "updated_at": now_iso()}},
    )
    if claimed_bid.modified_count != 1:
        await db.shipments.update_one(
            {"id": s["id"], "accepted_bid_id": bid_id, "trip_id": trip_id},
            {"$set": {"status": s["status"], "accepted_bid_id": s.get("accepted_bid_id"), "assigned_driver_id": s.get("assigned_driver_id"), "trip_id": s.get("trip_id"), "updated_at": now_iso()}},
        )
        raise HTTPException(status_code=400, detail="Bid is not pending")
    # accept this bid, reject others
    await db.bids.update_many(
        {"shipment_id": s["id"], "id": {"$ne": bid_id}, "status": "PENDING"},
        {"$set": {"status": "REJECTED", "updated_at": now_iso()}},
    )
    # create trip
    trip = {
        "id": trip_id, "shipment_id": s["id"], "customer_id": s["customer_id"], "customer_name": s["customer_name"],
        "driver_id": bid["driver_id"], "driver_name": bid["driver_name"], "provider_id": bid.get("provider_id"),
        "vehicle": bid.get("driver_vehicle", {}),
        "pickup_location": s.get("pickup_location"), "delivery_location": s.get("delivery_location"),
        "price": bid["price"], "shipment_title": s["title"],
        "status": "DRIVER_ASSIGNED", "tracking_events": [
            {"id": uid(), "status": "DRIVER_ASSIGNED", "lat": None, "lng": None, "timestamp": now_iso()}
        ],
        "delivery_confirmation": None, "customer_confirmed": False,
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.trips.insert_one(trip)
    await create_notification(bid["driver_id"], "bid_accepted", "تم قبول عرضك!", "Your bid was accepted!",
                              f"تم قبول عرضك على «{s['title']}»", f"Your bid on \"{s['title']}\" was accepted",
                              {"trip_id": trip["id"], "shipment_id": s["id"], "entity_type": "trip", "entity_id": trip["id"]})
    return clean(dict(trip))


# ================= DEMO PAYMENT =================
@api.post("/trips/{tid}/pay")
async def pay_trip(tid: str, user: dict = Depends(require_roles("customer"))):
    """Demo payment. Idempotent: if the trip is already HELD, returns the current state
    without creating another transaction. Records a single payment_hold row in the
    existing db.transactions collection (NO new ledger). record_trip_completion() is
    untouched and continues to run at delivery-confirmation time to settle the trip."""
    t = await db.trips.find_one({"id": tid}, {"_id": 0})
    if not t or t["customer_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Trip not found")
    if t.get("status") in TERMINAL_STATES:
        raise HTTPException(status_code=400, detail="TRIP_IN_TERMINAL_STATE")
    if (t.get("payment_status") or "NONE") == "HELD":
        # already paid — idempotent no-op
        return {"trip": t, "already_paid": True}

    amount = float(t.get("price", 0) or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="INVALID_TRIP_PRICE")

    # Atomic claim: only one concurrent request wins the transition NONE -> HELD.
    payment_id = uid()
    now = now_iso()
    claimed = await db.trips.find_one_and_update(
        {"id": tid, "$or": [{"payment_status": {"$exists": False}}, {"payment_status": {"$ne": "HELD"}}]},
        {"$set": {"payment_status": "HELD", "payment_id": payment_id, "paid_at": now, "updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not claimed:
        # Lost the race: another request already flipped it to HELD.
        fresh = await db.trips.find_one({"id": tid}, {"_id": 0})
        return {"trip": fresh, "already_paid": True}

    # Fetch platform settings (currency) — do NOT create driver_earning or platform_commission here;
    # those remain the exclusive responsibility of record_trip_completion() at completion time.
    from extra import get_settings
    settings = await get_settings()
    txn = {
        "id": payment_id, "type": "payment_hold",
        "account_id": t["customer_id"], "account_role": "customer",
        "shipment_id": t.get("shipment_id"), "trip_id": tid,
        "amount": amount, "gross": amount, "commission": 0, "net": amount,
        "currency": settings["currency"], "status": "HELD",
        "description": f"Payment held for {t.get('shipment_title','')}",
        "created_by": user.get("name"), "created_by_id": user["id"],
        "created_at": now,
    }
    await db.transactions.insert_one(txn)
    await db.audit_logs.insert_one({
        "id": uid(), "admin_id": user["id"], "admin_name": user.get("name", ""),
        "actor_id": user["id"], "actor_name": user.get("name", ""), "actor_role": "customer",
        "action": "TRIP_PAYMENT_HELD", "entity": "trip", "entity_id": tid,
        "old_value": {"payment_status": t.get("payment_status") or "NONE"},
        "new_value": {"payment_status": "HELD", "amount": amount, "payment_id": payment_id},
        "reason": "", "result": "success", "timestamp": now,
    })
    fresh = await db.trips.find_one({"id": tid}, {"_id": 0})
    return {"trip": fresh, "already_paid": False}


# ================= TRIPS =================
TRIP_FLOW = [
    "DRIVER_ASSIGNED", "DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "LOADING", "LOADED",
    "IN_TRANSIT", "NEAR_DESTINATION", "DRIVER_ARRIVED_DESTINATION",
    "DELIVERED_PENDING_CONFIRMATION",
]
TERMINAL_STATES = {"DELIVERED", "COMPLETED", "CANCELLED", "DISPUTED", "REFUNDED"}
DEFAULT_AUTO_COMPLETE_HOURS = 48


async def _maybe_auto_complete(t: dict) -> dict:
    """Phase 5A lazy auto-completion. If a trip is stuck in DELIVERED_PENDING_CONFIRMATION
    beyond the configured timeout, mark it COMPLETED (system) and fire the ledger. Called
    at every trip read for the affected roles."""
    if not t or t.get("status") != "DELIVERED_PENDING_CONFIRMATION":
        return t
    try:
        from datetime import datetime as _dt
        from extra import get_settings as _get_settings, record_trip_completion as _rec
        s = await _get_settings()
        hours = float(s.get("auto_complete_hours") or DEFAULT_AUTO_COMPLETE_HOURS)
        marker = t.get("delivered_pending_at") or t.get("updated_at") or t.get("created_at")
        if not marker:
            return t
        elapsed = (datetime.now(timezone.utc) - _dt.fromisoformat(marker.replace("Z", "+00:00"))).total_seconds() / 3600.0
        if elapsed < hours:
            return t
        claimed = await db.trips.update_one(
            {"id": t["id"], "status": "DELIVERED_PENDING_CONFIRMATION"},
            {"$set": {
                "status": "COMPLETED", "customer_confirmed": True, "auto_completed": True,
                "delivery_confirmation": {
                    "reference": "", "confirmed_at": now_iso(),
                    "confirmed_by": "system", "auto": True,
                },
                "delivered_at": now_iso(), "completed_at": now_iso(), "updated_at": now_iso(),
            }},
        )
        if claimed.modified_count == 1:
            await db.shipments.update_one({"id": t["shipment_id"]}, {"$set": {"status": "COMPLETED", "updated_at": now_iso()}})
            fresh = await db.trips.find_one({"id": t["id"]}, {"_id": 0})
            await _rec(fresh)
            await db.audit_logs.insert_one({
                "id": uid(), "admin_id": "system", "admin_name": "system",
                "actor_id": "system", "actor_name": "system", "actor_role": "system",
                "action": "TRIP_AUTO_COMPLETED", "entity": "trip", "entity_id": t["id"],
                "old_value": {"status": "DELIVERED_PENDING_CONFIRMATION"},
                "new_value": {"status": "COMPLETED", "auto": True, "elapsed_hours": round(elapsed, 2)},
                "reason": f"Auto-completed after {round(elapsed,1)}h without customer confirmation",
                "result": "success", "timestamp": now_iso(),
            })
            await create_notification(t["customer_id"], "trip_auto_completed",
                                      "تم إكمال الرحلة تلقائيًا", "Trip auto-completed",
                                      "لم يتم تأكيد الاستلام خلال المهلة المحددة.",
                                      "Delivery was not confirmed within the allowed window.",
                                      {"trip_id": t["id"], "entity_type": "trip", "entity_id": t["id"]})
            return fresh
    except Exception as _e:
        logger.warning("auto-complete check failed for trip %s: %s", t.get("id"), _e)
    return t


@api.get("/trips/mine")
async def my_trips(user: dict = Depends(get_current_user)):
    if user["role"] == "customer":
        q = {"customer_id": user["id"]}
    elif user["role"] == "driver":
        q = {"driver_id": user["id"]}
    elif user["role"] == "provider":
        q = {"provider_id": user["id"]}
    else:
        q = {}
    trips = await db.trips.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Lazy auto-complete pass (only touches DELIVERED_PENDING_CONFIRMATION beyond threshold)
    refreshed = []
    for tr in trips:
        refreshed.append(await _maybe_auto_complete(tr))
    return refreshed


@api.get("/trips/{tid}")
async def get_trip(tid: str, user: dict = Depends(get_current_user)):
    t = await db.trips.find_one({"id": tid}, {"_id": 0})
    if not t or not can_access_trip(t, user):
        raise HTTPException(status_code=404, detail="Trip not found")
    t = await _maybe_auto_complete(t)
    return t


@api.post("/trips/{tid}/status")
async def update_trip_status(tid: str, body: TripStatusUpdate, user: dict = Depends(require_roles("driver"))):
    t = await db.trips.find_one({"id": tid})
    if not t or t["driver_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Trip not found")
    if t.get("status") in TERMINAL_STATES:
        raise HTTPException(status_code=400, detail="TRIP_IN_TERMINAL_STATE")
    if body.status not in TRIP_FLOW:
        raise HTTPException(status_code=400, detail="Invalid status")
    try:
        current_index = TRIP_FLOW.index(t["status"])
    except ValueError:
        raise HTTPException(status_code=400, detail="Trip is in a terminal state")
    has_next_state = current_index + 1 < len(TRIP_FLOW)
    if not has_next_state or body.status != TRIP_FLOW[current_index + 1]:
        raise HTTPException(status_code=400, detail="INVALID_TRIP_TRANSITION")

    # Payment gate: driver cannot advance the trip beyond DRIVER_ASSIGNED until the
    # customer has paid (demo payment_status == HELD). This is the only backend
    # change that couples payment to the trip state machine.
    if t.get("status") == "DRIVER_ASSIGNED" and (t.get("payment_status") or "NONE") != "HELD":
        raise HTTPException(status_code=400, detail="PAYMENT_REQUIRED")

    # Regulatory eligibility gate at TRIP START only (leaving DRIVER_ASSIGNED). Per the
    # confirmed policy we do NOT auto-halt an already-running trip if a document later
    # expires — mid-trip statuses are recorded/shown for admin, not auto-blocked here.
    if t.get("status") == "DRIVER_ASSIGNED":
        from compliance import check_trip_eligibility, log_eligibility_blocked
        trip_elig = await check_trip_eligibility(t)
        if not trip_elig["eligible"]:
            await log_eligibility_blocked(user, "trip", tid, trip_elig)
            raise HTTPException(status_code=403, detail={"code": "NOT_ELIGIBLE", "reasons": trip_elig["reasons"]})

    # Phase 5A: Proof of Delivery is REQUIRED to reach DELIVERED_PENDING_CONFIRMATION
    updates = {"status": body.status, "updated_at": now_iso()}
    if body.status == "DELIVERED_PENDING_CONFIRMATION":
        if not (body.pod_photo or "").strip():
            raise HTTPException(status_code=400, detail="POD_REQUIRED")
        updates["delivered_pending_at"] = now_iso()
        updates["delivery_proof"] = {
            "photo": body.pod_photo,
            "notes": body.pod_notes or "",
            "delivered_by_id": user["id"],
            "delivered_by_name": user.get("name", ""),
            "lat": body.lat, "lng": body.lng,
            "at": now_iso(),
        }
        await db.audit_logs.insert_one({
            "id": uid(), "admin_id": user["id"], "admin_name": user.get("name", ""),
            "actor_id": user["id"], "actor_name": user.get("name", ""), "actor_role": "driver",
            "action": "TRIP_POD_SUBMITTED", "entity": "trip", "entity_id": tid,
            "old_value": {"status": t.get("status")},
            "new_value": {"status": body.status, "has_photo": True, "notes_len": len(body.pod_notes or "")},
            "reason": "", "result": "success", "timestamp": now_iso(),
        })

    event = {"id": uid(), "status": body.status, "lat": body.lat, "lng": body.lng, "timestamp": now_iso()}
    await db.trips.update_one({"id": tid}, {"$set": updates, "$push": {"tracking_events": event}})
    await db.shipments.update_one({"id": t["shipment_id"]}, {"$set": {"status": body.status, "updated_at": now_iso()}})
    if body.status == "DELIVERED_PENDING_CONFIRMATION":
        # Distinct, action-required notification — clearer than the generic trip_update.
        await create_notification(
            t["customer_id"], "pod_pending",
            "إثبات تسليم بانتظار تأكيدك", "Proof of delivery awaits your confirmation",
            "تم إرسال إثبات التسليم. يرجى مراجعة الشحنة وتأكيد استلامها.",
            "Proof of delivery has been submitted. Please review and confirm receipt.",
            {"trip_id": tid, "shipment_id": t["shipment_id"], "status": body.status,
             "entity_type": "trip", "entity_id": tid},
        )
    else:
        await create_notification(t["customer_id"], "trip_update", "تحديث حالة الرحلة", "Trip status updated",
                                  "", "", {"trip_id": tid, "shipment_id": t["shipment_id"], "status": body.status,
                                           "entity_type": "trip", "entity_id": tid})
    return await db.trips.find_one({"id": tid}, {"_id": 0})


@api.post("/trips/{tid}/confirm-delivery")
async def confirm_delivery(tid: str, body: DeliveryConfirm, user: dict = Depends(require_roles("customer"))):
    """Customer confirms receipt. Phase 5A: transitions all the way to COMPLETED (no more
    sticky DELIVERED-only state) and triggers the immutable ledger. Rating remains optional."""
    t = await db.trips.find_one({"id": tid})
    if not t or t["customer_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Trip not found")
    if t.get("status") == "DISPUTED":
        raise HTTPException(status_code=400, detail="TRIP_IN_DISPUTE")
    if t.get("status") != "DELIVERED_PENDING_CONFIRMATION":
        raise HTTPException(status_code=400, detail="Trip is not ready for delivery confirmation")
    claimed = await db.trips.update_one(
        {"id": tid, "status": "DELIVERED_PENDING_CONFIRMATION"},
        {"$set": {
            "status": "COMPLETED", "customer_confirmed": True, "auto_completed": False,
            "delivery_confirmation": {
                "reference": body.reference or "", "confirmed_at": now_iso(),
                "confirmed_by": user.get("name", ""), "confirmed_by_id": user["id"],
                "lat": body.lat, "lng": body.lng,
                "delivered_to_name": body.delivered_to_name or "",
                "auto": False,
            },
            "delivered_at": now_iso(), "completed_at": now_iso(), "updated_at": now_iso(),
        }},
    )
    if claimed.modified_count != 1:
        raise HTTPException(status_code=409, detail="Trip already confirmed or state changed")
    await db.shipments.update_one({"id": t["shipment_id"]}, {"$set": {"status": "COMPLETED", "updated_at": now_iso()}})
    fresh = await db.trips.find_one({"id": tid}, {"_id": 0})
    from extra import record_trip_completion
    await record_trip_completion(fresh)
    await db.audit_logs.insert_one({
        "id": uid(), "admin_id": user["id"], "admin_name": user.get("name", ""),
        "actor_id": user["id"], "actor_name": user.get("name", ""), "actor_role": "customer",
        "action": "TRIP_DELIVERY_CONFIRMED", "entity": "trip", "entity_id": tid,
        "old_value": {"status": "DELIVERED_PENDING_CONFIRMATION"},
        "new_value": {"status": "COMPLETED"},
        "reason": "", "result": "success", "timestamp": now_iso(),
    })
    await create_notification(t["driver_id"], "delivery_confirmed", "تم تأكيد التسليم", "Delivery confirmed",
                              "", "", {"trip_id": tid, "entity_type": "trip", "entity_id": tid})
    return fresh


@api.post("/trips/{tid}/dispute")
async def dispute_trip(tid: str, body: DisputeCreate, user: dict = Depends(require_roles("customer"))):
    """Phase 5A: customer disputes the delivery instead of confirming."""
    t = await db.trips.find_one({"id": tid})
    if not t or t["customer_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Trip not found")
    if t.get("status") != "DELIVERED_PENDING_CONFIRMATION":
        raise HTTPException(status_code=400, detail="Trip is not in a disputable state")
    if not (body.reason or "").strip():
        raise HTTPException(status_code=400, detail="DISPUTE_REASON_REQUIRED")
    claimed = await db.trips.update_one(
        {"id": tid, "status": "DELIVERED_PENDING_CONFIRMATION"},
        {"$set": {
            "status": "DISPUTED",
            "dispute": {
                "reason": body.reason, "notes": body.notes or "",
                "opened_by_id": user["id"], "opened_by_name": user.get("name", ""),
                "opened_at": now_iso(),
            },
            "updated_at": now_iso(),
        }},
    )
    if claimed.modified_count != 1:
        raise HTTPException(status_code=409, detail="Trip state changed")
    await db.shipments.update_one({"id": t["shipment_id"]}, {"$set": {"status": "DISPUTED", "updated_at": now_iso()}})
    await db.audit_logs.insert_one({
        "id": uid(), "admin_id": user["id"], "admin_name": user.get("name", ""),
        "actor_id": user["id"], "actor_name": user.get("name", ""), "actor_role": "customer",
        "action": "TRIP_DISPUTED", "entity": "trip", "entity_id": tid,
        "old_value": {"status": "DELIVERED_PENDING_CONFIRMATION"},
        "new_value": {"status": "DISPUTED", "reason": body.reason},
        "reason": body.reason, "result": "success", "timestamp": now_iso(),
    })
    await create_notification(t["driver_id"], "trip_disputed", "تم فتح نزاع على الرحلة", "Trip disputed",
                              body.reason, body.reason,
                              {"trip_id": tid, "entity_type": "trip", "entity_id": tid})
    # Notify admins
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(100)
    for a in admins:
        await create_notification(a["id"], "trip_disputed", "نزاع جديد", "New dispute",
                                  body.reason, body.reason,
                                  {"trip_id": tid, "entity_type": "trip", "entity_id": tid})
    return await db.trips.find_one({"id": tid}, {"_id": 0})


@api.post("/trips/{tid}/review")
async def review_trip(tid: str, body: ReviewCreate, user: dict = Depends(require_roles("customer"))):
    t = await db.trips.find_one({"id": tid})
    if not t or t["customer_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Trip not found")
    if t.get("review_id"):
        raise HTTPException(status_code=409, detail="Trip already reviewed")
    if t.get("status") == "DISPUTED":
        raise HTTPException(status_code=400, detail="TRIP_IN_DISPUTE")
    # Phase 5A: accept both DELIVERED (legacy) and COMPLETED (current flow)
    if t.get("status") not in ("DELIVERED", "COMPLETED") or not t.get("customer_confirmed"):
        raise HTTPException(status_code=400, detail="Delivery not confirmed yet")
    review = {
        "id": uid(), "trip_id": tid, "shipment_id": t["shipment_id"], "customer_id": user["id"],
        "driver_id": t["driver_id"], "overall": body.overall, "service_quality": body.service_quality,
        "communication": body.communication, "on_time": body.on_time, "comment": body.comment or "",
        "created_at": now_iso(),
    }
    claimed = await db.trips.update_one(
        {"id": tid, "customer_id": user["id"], "status": {"$in": ["DELIVERED", "COMPLETED"]},
         "customer_confirmed": True, "review_id": {"$exists": False}},
        {"$set": {"status": "COMPLETED", "review_id": review["id"], "updated_at": now_iso()}},
    )
    if claimed.modified_count != 1:
        raise HTTPException(status_code=409, detail="Trip already reviewed or not ready for review")
    await db.reviews.insert_one(review)
    # update driver aggregate rating
    driver = await db.users.find_one({"id": t["driver_id"]})
    if driver:
        count = driver.get("rating_count", 0)
        avg = driver.get("rating", 0)
        new_count = count + 1
        new_avg = round((avg * count + body.overall) / new_count, 2)
        await db.users.update_one({"id": driver["id"]}, {"$set": {
            "rating": new_avg, "rating_count": new_count,
            "completed_trips": driver.get("completed_trips", 0) + 1,
        }})
    await db.shipments.update_one({"id": t["shipment_id"]}, {"$set": {"status": "COMPLETED", "updated_at": now_iso()}})
    from extra import record_trip_completion
    completed = await db.trips.find_one({"id": tid}, {"_id": 0})
    await record_trip_completion(completed)
    return clean(dict(review))


# ================= NOTIFICATIONS =================
@api.get("/notifications")
async def notifications(user: dict = Depends(get_current_user)):
    return await db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.post("/notifications/{nid}/read")
async def read_notification(nid: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one({"id": nid, "user_id": user["id"]}, {"$set": {"read": True}})
    return {"success": True}


# ================= PROVIDER =================
@api.get("/provider/opportunities")
async def provider_opportunities(user: dict = Depends(require_roles("provider"))):
    return await db.shipments.find(
        {"status": {"$in": ["PUBLISHED", "BIDDING"]}}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)


@api.get("/provider/summary")
async def provider_summary(user: dict = Depends(require_roles("provider"))):
    opportunities = await db.shipments.count_documents({"status": {"$in": ["PUBLISHED", "BIDDING"]}})
    trips = await db.trips.count_documents({"provider_id": user["id"]})
    return {"opportunities": opportunities, "trips": trips,
            "company_name": user.get("company_name", ""), "service_areas": user.get("service_areas", [])}


@api.get("/provider/bids")
async def provider_bids(user: dict = Depends(require_roles("provider"))):
    bids = await db.bids.find({"provider_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for bid in bids:
        bid["shipment"] = await db.shipments.find_one({"id": bid.get("shipment_id")}, {"_id": 0})
    return bids


@api.get("/provider/transactions")
async def provider_transactions(user: dict = Depends(require_roles("provider"))):
    return await db.transactions.find(
        {"account_id": user["id"], "account_role": "provider"}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)



# ================= ADMIN =================
@api.get("/admin/stats")
async def admin_stats(user: dict = Depends(require_roles("admin"))):
    total_shipments = await db.shipments.count_documents({})
    active_shipments = await db.shipments.count_documents({"status": {"$in": ["PUBLISHED", "BIDDING", "DRIVER_ASSIGNED", "IN_TRANSIT"]}})
    completed_shipments = await db.shipments.count_documents({"status": "COMPLETED"})
    active_trips = await db.trips.count_documents({"status": {"$nin": ["COMPLETED", "CANCELLED"]}})
    total_drivers = await db.users.count_documents({"role": "driver"})
    verified_drivers = await db.users.count_documents({"role": "driver", "verification_status": "APPROVED"})
    pending_drivers = await db.users.count_documents({"role": "driver", "verification_status": {"$in": ["PENDING", "UNDER_REVIEW"]}})
    providers = await db.users.count_documents({"role": "provider"})
    customers = await db.users.count_documents({"role": "customer"})
    recent = await db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).to_list(10)
    return {
        "total_shipments": total_shipments, "active_shipments": active_shipments,
        "completed_shipments": completed_shipments, "active_trips": active_trips,
        "total_drivers": total_drivers, "verified_drivers": verified_drivers,
        "pending_drivers": pending_drivers, "providers": providers, "customers": customers,
        "recent_activity": recent,
    }


@api.get("/admin/drivers")
async def admin_drivers(user: dict = Depends(require_roles("admin"))):
    return await db.users.find({"role": "driver"}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(500)


@api.post("/admin/drivers/{driver_id}/verify")
async def admin_verify_driver(driver_id: str, body: VerifyAction, user: dict = Depends(require_roles("admin"))):
    d = await db.users.find_one({"id": driver_id, "role": "driver"})
    if not d:
        raise HTTPException(status_code=404, detail="Driver not found")
    mapping = {"approve": "APPROVED", "reject": "REJECTED", "suspend": "SUSPENDED", "request_changes": "PENDING"}
    if body.action not in mapping:
        raise HTTPException(status_code=400, detail="Invalid action")
    new_status = mapping[body.action]
    doc_status = {"approve": "APPROVED", "reject": "REJECTED"}.get(body.action)
    updates = {"verification_status": new_status, "admin_notes": body.notes or "", "updated_at": now_iso()}
    if doc_status:
        docs = d.get("documents", [])
        for doc in docs:
            doc["status"] = doc_status
            doc["reviewed_at"] = now_iso()
            if body.notes:
                doc["notes"] = body.notes
        updates["documents"] = docs
    await db.users.update_one({"id": driver_id}, {"$set": updates})
    await audit(user, f"driver_{body.action}", "driver", driver_id)
    titles = {
        "APPROVED": ("تم توثيق حسابك", "Your account has been verified"),
        "REJECTED": ("تم رفض التوثيق", "Verification rejected"),
        "SUSPENDED": ("تم تعليق حسابك", "Your account has been suspended"),
        "PENDING": ("مطلوب تحديث المستندات", "Document changes requested"),
    }
    ta, te = titles[new_status]
    await create_notification(driver_id, "verification", ta, te, body.notes or "", body.notes or "",
                              {"status": new_status, "entity_type": "verification", "entity_id": driver_id})
    return await db.users.find_one({"id": driver_id}, {"_id": 0, "password_hash": 0})


@api.get("/admin/providers")
async def admin_providers(user: dict = Depends(require_roles("admin"))):
    return await db.users.find({"role": "provider"}, {"_id": 0, "password_hash": 0}).to_list(500)


@api.get("/admin/customers")
async def admin_customers(user: dict = Depends(require_roles("admin"))):
    return await db.users.find({"role": "customer"}, {"_id": 0, "password_hash": 0}).to_list(500)


@api.get("/admin/users")
async def admin_users(q: str = "", role: str = "", status: str = "", user: dict = Depends(require_roles("admin"))):
    query = {}
    if role:
        query["role"] = role
    docs = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(2000)
    ql = (q or "").lower().strip()
    out = []
    for u in docs:
        raw = (u.get("status") or "active").lower()
        # Phase 4: distinguish suspended (new) from disabled (legacy). Both block login.
        if raw == "suspended":
            st = "suspended"
        elif raw in ("disabled", "inactive"):
            st = "disabled"
        else:
            st = "active"
        u["status"] = st
        if status:
            # Accept 'blocked' as a synonym for either suspended or disabled
            if status == "blocked" and st in ("suspended", "disabled"):
                pass
            elif status != st:
                continue
        if ql and ql not in (u.get("name", "") or "").lower() and ql not in (u.get("phone", "") or "").lower() and ql not in (u.get("email", "") or "").lower():
            continue
        out.append(u)
    return out


@api.get("/admin/shipments")
async def admin_shipments(user: dict = Depends(require_roles("admin"))):
    return await db.shipments.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api.get("/admin/bids")
async def admin_bids(user: dict = Depends(require_roles("admin"))):
    bids = await db.bids.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for b in bids:
        s = await db.shipments.find_one({"id": b["shipment_id"]}, {"_id": 0, "title": 1, "customer_name": 1})
        b["shipment_title"] = s.get("title") if s else ""
        b["customer_name"] = s.get("customer_name") if s else ""
    return bids


@api.get("/admin/trips")
async def admin_trips(user: dict = Depends(require_roles("admin"))):
    return await db.trips.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)


@api.get("/admin/audit-logs")
async def admin_audit(user: dict = Depends(require_roles("admin"))):
    return await db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).to_list(500)


from extra import extra_api
from regulatory_core import reg_router
from privacy import privacy_router
app.include_router(api)
app.include_router(extra_api)
app.include_router(reg_router)
app.include_router(privacy_router)

def _cors_allowed_origins() -> list:
    """Resolve allowed CORS origins.

    Production: explicit origins only — any '*' wildcard is stripped (fail
    closed). Development/preview: falls back to '*' so local work keeps running.
    Prefers CORS_ALLOWED_ORIGINS, with legacy CORS_ORIGINS as a fallback.
    """
    raw = os.environ.get("CORS_ALLOWED_ORIGINS")
    if raw is None:
        raw = os.environ.get("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if _otp_is_production():
        return [o for o in origins if o != "*"]
    return origins or ["*"]


_cors_origins = _cors_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    # Fail-closed security guards: refuse to boot production with an unsafe
    # OTP configuration or default/weak secrets.
    validate_otp_security()
    validate_secrets()
    await ensure_indexes()
    await run_seed()
    logger.info("CARGO backend ready")


@app.on_event("shutdown")
async def shutdown():
    from database import client
    client.close()
