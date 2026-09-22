"""CARGO Regulatory Core — Transport Document + Compliance HTTP adapters.

Design principles (kept aligned with the rest of CARGO):
  * Business logic is in small service functions; HTTP endpoints are thin adapters.
  * No direct coupling to any Naql/government provider — `naql_*` and `integration_*`
    fields are placeholders on an INTERNAL flexible structure. A future NaqlProvider
    can populate them without rewriting the core.
  * The Transport Document is bound to a REAL trip (trip_id unique), and links
    Shipment -> Trip -> Provider/Carrier -> Driver -> Vehicle.
  * A document tied to a COMPLETED trip cannot be deleted or cancelled; the lifecycle
    status + history are used instead.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import db
from auth import get_current_user
from extra import require_permission
import compliance as comp

reg_router = APIRouter(prefix="/api")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid() -> str:
    return str(uuid.uuid4())


# ==================================================================================
# TRANSPORT DOCUMENT
# ==================================================================================
TD_STATUSES = ["DRAFT", "READY", "ISSUED", "IN_TRANSIT", "DELIVERED", "CANCELLED"]
TD_TERMINAL = {"DELIVERED", "CANCELLED"}
TD_TRANSITIONS = {
    "DRAFT": {"READY", "CANCELLED"},
    "READY": {"ISSUED", "DRAFT", "CANCELLED"},
    "ISSUED": {"IN_TRANSIT", "CANCELLED"},
    "IN_TRANSIT": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}

# Stable key sets per group — unknown keys in the request are ignored so the data
# contract stays stable for future extraction / Naql mapping.
TD_GROUPS = {
    "document": ["document_id", "issue_location", "issue_date", "issue_time", "original_copies_count"],
    "shipper": ["shipper_name", "shipper_address"],
    "consignee": ["consignee_name", "consignee_address"],
    "carrier": ["carrier_name", "carrier_license_number", "carrier_license_status", "carrier_license_expiry_date"],
    "delivery": ["delivery_location", "delivery_date", "delivery_time"],
    "cargo": ["cargo_type", "cargo_description", "cargo_weight", "cargo_nature", "cargo_marks",
              "cargo_characteristics", "dangerous_goods", "dangerous_goods_description",
              "quantity", "declared_value"],
    "freight": ["total_transport_price", "payment_payer", "additional_expenses", "currency"],
    "reservations": ["carrier_reservations", "reservation_reason"],
    "integration": ["naql_document_number", "naql_status", "naql_reference", "integration_source",
                    "external_sync_status", "last_sync_at", "integration_notes"],
}


class TransportDocumentBody(BaseModel):
    document: Optional[dict] = None
    shipper: Optional[dict] = None
    consignee: Optional[dict] = None
    carrier: Optional[dict] = None
    delivery: Optional[dict] = None
    cargo: Optional[dict] = None
    freight: Optional[dict] = None
    reservations: Optional[dict] = None
    integration: Optional[dict] = None


class TDStatusBody(BaseModel):
    status: str
    note: Optional[str] = ""


def _empty_group(name: str) -> dict:
    return {k: "" for k in TD_GROUPS[name]}


def _merge_group(name: str, existing: Optional[dict], incoming: Optional[dict]) -> dict:
    out = _empty_group(name)
    if isinstance(existing, dict):
        for k in TD_GROUPS[name]:
            if existing.get(k) is not None:
                out[k] = existing.get(k)
    if isinstance(incoming, dict):
        for k in TD_GROUPS[name]:
            if k in incoming and incoming.get(k) is not None:
                out[k] = incoming.get(k)
    return out


def _actor_role(user: dict) -> str:
    return user.get("role", "")


async def _load_trip(tid: str) -> dict:
    trip = await db.trips.find_one({"id": tid}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="TRIP_NOT_FOUND")
    return trip


def _can_write_td(user: dict, trip: dict) -> bool:
    if user.get("role") == "admin":
        return True
    return user["id"] in (trip.get("driver_id"), trip.get("provider_id"))


def _can_read_td(user: dict, trip: dict) -> bool:
    if user.get("role") == "admin":
        return True
    return user["id"] in (trip.get("customer_id"), trip.get("driver_id"), trip.get("provider_id"))


async def _prefill_from_trip(trip: dict) -> dict:
    """Convenience prefill from real trip/shipment/customer/provider so the carrier
    doesn't retype known data. Everything remains editable via PUT."""
    shipment = await db.shipments.find_one({"id": trip.get("shipment_id")}, {"_id": 0}) or {}
    customer = await db.users.find_one({"id": trip.get("customer_id")}, {"_id": 0}) or {}
    provider = await db.users.find_one({"id": trip.get("provider_id")}, {"_id": 0}) if trip.get("provider_id") else {}
    driver = await db.users.find_one({"id": trip.get("driver_id")}, {"_id": 0}) if trip.get("driver_id") else {}
    from extra import get_settings
    settings = await get_settings()

    carrier_name = (provider or {}).get("company_name") or (provider or {}).get("name") \
        or (driver or {}).get("name") or ""
    carrier_license = ((provider or {}).get("carrier_license") or {}) if provider else {}
    dloc = shipment.get("delivery_location") or {}

    groups = {name: _empty_group(name) for name in TD_GROUPS}
    groups["shipper"]["shipper_name"] = customer.get("name", "")
    groups["shipper"]["shipper_address"] = (shipment.get("pickup_location") or {}).get("address", "")
    groups["consignee"]["consignee_address"] = dloc.get("address", "")
    groups["carrier"]["carrier_name"] = carrier_name
    groups["carrier"]["carrier_license_number"] = carrier_license.get("number", "")
    groups["carrier"]["carrier_license_status"] = carrier_license.get("status", "")
    groups["carrier"]["carrier_license_expiry_date"] = carrier_license.get("expiry_date", "")
    groups["delivery"]["delivery_location"] = dloc.get("address", "")
    groups["delivery"]["delivery_date"] = shipment.get("delivery_date", "")
    groups["delivery"]["delivery_time"] = shipment.get("delivery_time", "")
    groups["cargo"]["cargo_description"] = shipment.get("description", "") or shipment.get("title", "")
    groups["cargo"]["cargo_weight"] = shipment.get("weight", "")
    groups["cargo"]["quantity"] = shipment.get("quantity", "")
    groups["freight"]["total_transport_price"] = trip.get("price", "")
    groups["freight"]["payment_payer"] = "SHIPPER"
    groups["freight"]["currency"] = settings.get("currency", "OMR")
    groups["integration"]["integration_source"] = "INTERNAL"
    groups["integration"]["naql_status"] = ""
    groups["integration"]["external_sync_status"] = "NOT_SYNCED"
    return groups


def _history_entry(user: dict, action: str, note: str = "", source: str = "INTERNAL") -> dict:
    return {"action": action, "by_id": (user or {}).get("id", "system"),
            "by_name": (user or {}).get("name", "system"), "by_role": _actor_role(user or {}),
            "at": now_iso(), "source": source, "note": note}


async def _td_audit(user: dict, action: str, doc_id: str, old=None, new=None, reason=""):
    a = user or {}
    await db.audit_logs.insert_one({
        "id": uid(), "admin_id": a.get("id", "system"), "admin_name": a.get("name", "system"),
        "actor_id": a.get("id", "system"), "actor_name": a.get("name", "system"),
        "actor_role": a.get("role", "system"),
        "action": action, "entity": "transport_document", "entity_id": doc_id,
        "old_value": old, "new_value": new, "reason": reason,
        "result": "success", "timestamp": now_iso(),
    })


# ---- endpoints ----
@reg_router.post("/trips/{tid}/transport-document")
async def create_transport_document(tid: str, body: TransportDocumentBody,
                                    user: dict = Depends(get_current_user)):
    trip = await _load_trip(tid)
    if not _can_write_td(user, trip):
        raise HTTPException(status_code=403, detail="FORBIDDEN")
    existing = await db.transport_documents.find_one({"trip_id": tid}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="TRANSPORT_DOCUMENT_EXISTS")

    groups = await _prefill_from_trip(trip)
    incoming = body.model_dump()
    for name in TD_GROUPS:
        groups[name] = _merge_group(name, groups[name], incoming.get(name))

    doc = {
        "id": uid(), "trip_id": tid, "shipment_id": trip.get("shipment_id"),
        "provider_id": trip.get("provider_id"), "driver_id": trip.get("driver_id"),
        "vehicle_id": trip.get("vehicle_id"),
        "status": "DRAFT",
        **groups,
        "created_by": user["id"], "created_by_name": user.get("name", ""), "created_by_role": _actor_role(user),
        "updated_by": user["id"], "updated_by_name": user.get("name", ""), "updated_by_role": _actor_role(user),
        "history": [_history_entry(user, "created")],
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.transport_documents.insert_one(doc)
    await _td_audit(user, "transport_document_created", doc["id"],
                    new={"trip_id": tid, "status": "DRAFT"})
    doc.pop("_id", None)
    return doc


@reg_router.get("/trips/{tid}/transport-document")
async def get_trip_transport_document(tid: str, user: dict = Depends(get_current_user)):
    trip = await _load_trip(tid)
    if not _can_read_td(user, trip):
        raise HTTPException(status_code=403, detail="FORBIDDEN")
    doc = await db.transport_documents.find_one({"trip_id": tid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="TRANSPORT_DOCUMENT_NOT_FOUND")
    return doc


@reg_router.get("/transport-documents/{doc_id}")
async def get_transport_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.transport_documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="TRANSPORT_DOCUMENT_NOT_FOUND")
    trip = await db.trips.find_one({"id": doc["trip_id"]}, {"_id": 0}) or {}
    if not _can_read_td(user, trip):
        raise HTTPException(status_code=403, detail="FORBIDDEN")
    return doc


@reg_router.put("/transport-documents/{doc_id}")
async def update_transport_document(doc_id: str, body: TransportDocumentBody,
                                    user: dict = Depends(get_current_user)):
    doc = await db.transport_documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="TRANSPORT_DOCUMENT_NOT_FOUND")
    trip = await db.trips.find_one({"id": doc["trip_id"]}, {"_id": 0}) or {}
    if not _can_write_td(user, trip):
        raise HTTPException(status_code=403, detail="FORBIDDEN")
    if doc.get("status") in TD_TERMINAL:
        raise HTTPException(status_code=400, detail="TRANSPORT_DOCUMENT_LOCKED")

    incoming = body.model_dump()
    updates = {}
    for name in TD_GROUPS:
        if incoming.get(name) is not None:
            updates[name] = _merge_group(name, doc.get(name), incoming.get(name))
    updates["updated_by"] = user["id"]
    updates["updated_by_name"] = user.get("name", "")
    updates["updated_by_role"] = _actor_role(user)
    updates["updated_at"] = now_iso()
    await db.transport_documents.update_one(
        {"id": doc_id},
        {"$set": updates, "$push": {"history": _history_entry(user, "updated")}},
    )
    await _td_audit(user, "transport_document_updated", doc_id,
                    old={"status": doc.get("status")}, new={"fields": [k for k in updates if k in TD_GROUPS]})
    return await db.transport_documents.find_one({"id": doc_id}, {"_id": 0})


@reg_router.post("/transport-documents/{doc_id}/status")
async def transition_transport_document(doc_id: str, body: TDStatusBody,
                                        user: dict = Depends(get_current_user)):
    new_status = (body.status or "").upper()
    if new_status not in TD_STATUSES:
        raise HTTPException(status_code=400, detail="INVALID_STATUS")
    doc = await db.transport_documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="TRANSPORT_DOCUMENT_NOT_FOUND")
    trip = await db.trips.find_one({"id": doc["trip_id"]}, {"_id": 0}) or {}
    if not _can_write_td(user, trip):
        raise HTTPException(status_code=403, detail="FORBIDDEN")
    current = doc.get("status", "DRAFT")
    if new_status not in TD_TRANSITIONS.get(current, set()):
        raise HTTPException(status_code=400, detail="INVALID_TRANSPORT_DOCUMENT_TRANSITION")
    # A document tied to a COMPLETED trip must not be cancelled (no destructive removal).
    if new_status == "CANCELLED" and (trip.get("status") or "").upper() == "COMPLETED":
        raise HTTPException(status_code=400, detail="CANNOT_CANCEL_COMPLETED_TRIP_DOCUMENT")

    await db.transport_documents.update_one(
        {"id": doc_id},
        {"$set": {"status": new_status, "updated_by": user["id"],
                  "updated_by_name": user.get("name", ""), "updated_by_role": _actor_role(user),
                  "updated_at": now_iso()},
         "$push": {"history": _history_entry(user, f"status:{new_status}", note=body.note or "")}},
    )
    action = "transport_document_issued" if new_status == "ISSUED" else "transport_document_updated"
    await _td_audit(user, action, doc_id, old={"status": current}, new={"status": new_status},
                    reason=body.note or "")
    return await db.transport_documents.find_one({"id": doc_id}, {"_id": 0})


@reg_router.get("/admin/transport-documents")
async def admin_list_transport_documents(status: Optional[str] = None,
                                          user: dict = Depends(require_permission("documents.view"))):
    q = {}
    if status:
        q["status"] = status.upper()
    return await db.transport_documents.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)


# ==================================================================================
# COMPLIANCE / ELIGIBILITY (visibility)
# ==================================================================================
@reg_router.get("/admin/compliance/application")
async def admin_application_eligibility(user: dict = Depends(require_permission("documents.view"))):
    lic = await db.settings.find_one({"id": "app_license"}, {"_id": 0}) or {}
    result = await comp.check_application_eligibility()
    await comp.log_compliance_checked(user, "app_license", "app_license", result)
    return {"license_status": lic.get("status", ""), **result}


@reg_router.get("/admin/compliance/check/driver/{driver_id}")
async def admin_check_driver(driver_id: str, user: dict = Depends(require_permission("documents.view"))):
    driver = await db.users.find_one({"id": driver_id, "role": "driver"}, {"_id": 0, "password_hash": 0})
    if not driver:
        raise HTTPException(status_code=404, detail="DRIVER_NOT_FOUND")
    result = await comp.check_driver_eligibility(driver)
    await comp.log_compliance_checked(user, "driver", driver_id, result)
    return {"driver_id": driver_id,
            "driver_training_status": (driver.get("regulatory") or {}).get("driver_training_status", ""),
            **result}


@reg_router.get("/admin/compliance/check/vehicle/{vehicle_id}")
async def admin_check_vehicle(vehicle_id: str, user: dict = Depends(require_permission("documents.view"))):
    vehicle = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="VEHICLE_NOT_FOUND")
    result = await comp.check_vehicle_eligibility(vehicle)
    await comp.log_compliance_checked(user, "vehicle", vehicle_id, result)
    return {"vehicle_id": vehicle_id,
            "operating_card_status": (vehicle.get("regulatory") or {}).get("operating_card_status", ""),
            **result}


@reg_router.get("/admin/compliance/check/provider/{provider_id}")
async def admin_check_provider(provider_id: str, user: dict = Depends(require_permission("documents.view"))):
    provider = await db.users.find_one({"id": provider_id, "role": "provider"}, {"_id": 0, "password_hash": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="PROVIDER_NOT_FOUND")
    result = await comp.check_provider_eligibility(provider)
    await comp.log_compliance_checked(user, "provider", provider_id, result)
    return {"provider_id": provider_id,
            "carrier_license_status": (provider.get("carrier_license") or {}).get("status", ""),
            **result}


@reg_router.get("/admin/compliance/check/trip/{trip_id}")
async def admin_check_trip(trip_id: str, user: dict = Depends(require_permission("documents.view"))):
    trip = await db.trips.find_one({"id": trip_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="TRIP_NOT_FOUND")
    result = await comp.check_trip_eligibility(trip)
    await comp.log_compliance_checked(user, "trip", trip_id, result)
    return {"trip_id": trip_id, **result}


# ---- self-service eligibility (driver / provider can see their own status) ----
@reg_router.get("/driver/eligibility")
async def my_driver_eligibility(user: dict = Depends(get_current_user)):
    if user.get("role") != "driver":
        raise HTTPException(status_code=403, detail="DRIVER_ONLY")
    return await comp.check_driver_eligibility(user)


@reg_router.get("/provider/eligibility")
async def my_provider_eligibility(user: dict = Depends(get_current_user)):
    if user.get("role") != "provider":
        raise HTTPException(status_code=403, detail="PROVIDER_ONLY")
    return await comp.check_provider_eligibility(user)
