"""CARGO Privacy & Data Governance — Oman PDPL *technical readiness* only.

Regulatory context (NOT legal advice, NOT compliance certification): Oman Personal
Data Protection Law (Royal Decree 6/2022) + Executive Regulation (Ministerial Decision
34/2024), with the 2025 amendment to be applied when the final policy is adopted.

This module ONLY provides architecture + data-governance registers + business services
+ RBAC + audit. It performs NO destructive deletion, NO real cross-border transfer, NO
real breach notification to any authority, NO DPO workflow, NO external provider wiring.

All HTTP endpoints are thin adapters over simple registers so a future language/service
extraction (Go/Node/Java) can reuse the same data contracts.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body

from database import db
from auth import get_current_user
from extra import require_permission

privacy_router = APIRouter(prefix="/api")

# Internal SLA placeholder for data-subject requests (NOT a legal deadline assertion).
DSR_RESPONSE_DAYS = 30

DATA_CATEGORIES = [
    "PUBLIC", "INTERNAL", "PERSONAL", "SENSITIVE_PERSONAL",
    "REGULATORY", "FINANCIAL", "LOCATION", "AUTHENTICATION",
]
CONSENT_BASES = ["consent", "contractual_necessity", "legal_obligation", "legitimate_basis", "other"]
DSR_TYPES = ["ACCESS", "RECTIFICATION", "ERASURE", "WITHDRAW_CONSENT", "PORTABILITY", "RESTRICTION", "OBJECTION"]
DSR_STATUSES = ["RECEIVED", "UNDER_REVIEW", "APPROVED", "REJECTED", "COMPLETED"]
BREACH_STATUSES = ["OPEN", "INVESTIGATING", "CONTAINED", "NOTIFIED", "RESOLVED", "CLOSED"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid() -> str:
    return str(uuid.uuid4())


def _pick(payload: dict, keys: list) -> dict:
    payload = payload or {}
    return {k: payload.get(k) for k in keys if k in payload}


async def _paudit(user: dict, action: str, entity: str, entity_id: str, reason: str = "", new=None, old=None):
    """Privacy audit writes into the EXISTING audit_logs collection (no new audit system)."""
    a = user or {}
    await db.audit_logs.insert_one({
        "id": uid(), "admin_id": a.get("id", "system"), "admin_name": a.get("name", "system"),
        "actor_id": a.get("id", "system"), "actor_name": a.get("name", "system"),
        "actor_role": a.get("role", "system"),
        "action": action, "entity": entity, "entity_id": entity_id,
        "old_value": old, "new_value": new, "reason": reason,
        "result": "success", "timestamp": now_iso(),
    })


# ==================================================================================
# 1) DATA CLASSIFICATION
# ==================================================================================
CLASS_KEYS = ["collection", "field", "category", "notes", "active"]


@privacy_router.get("/admin/privacy/classifications")
async def list_classifications(user: dict = Depends(require_permission("privacy.view"))):
    return await db.data_classifications.find({}, {"_id": 0}).sort("collection", 1).to_list(500)


@privacy_router.post("/admin/privacy/classifications")
async def create_classification(payload: dict = Body(...), user: dict = Depends(require_permission("privacy.manage"))):
    data = _pick(payload, CLASS_KEYS)
    if (data.get("category") or "") not in DATA_CATEGORIES:
        raise HTTPException(status_code=400, detail="INVALID_CATEGORY")
    doc = {"id": uid(), "collection": data.get("collection", ""), "field": data.get("field", ""),
           "category": data["category"], "notes": data.get("notes", ""),
           "active": data.get("active", True), "created_at": now_iso(), "updated_at": now_iso()}
    await db.data_classifications.insert_one(doc)
    await _paudit(user, "classification_set", "data_classification", doc["id"], new=doc["category"])
    doc.pop("_id", None)
    return doc


@privacy_router.put("/admin/privacy/classifications/{cid}")
async def update_classification(cid: str, payload: dict = Body(...), user: dict = Depends(require_permission("privacy.manage"))):
    existing = await db.data_classifications.find_one({"id": cid})
    if not existing:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    data = _pick(payload, CLASS_KEYS)
    if "category" in data and data["category"] not in DATA_CATEGORIES:
        raise HTTPException(status_code=400, detail="INVALID_CATEGORY")
    data["updated_at"] = now_iso()
    await db.data_classifications.update_one({"id": cid}, {"$set": data})
    await _paudit(user, "classification_set", "data_classification", cid, new=data.get("category"))
    return await db.data_classifications.find_one({"id": cid}, {"_id": 0})


@privacy_router.get("/privacy/categories")
async def get_categories(user: dict = Depends(get_current_user)):
    return {"data_categories": DATA_CATEGORIES, "consent_bases": CONSENT_BASES,
            "dsr_types": DSR_TYPES, "dsr_statuses": DSR_STATUSES, "breach_statuses": BREACH_STATUSES}


# ==================================================================================
# 2) CONSENT / PROCESSING BASIS
# ==================================================================================
@privacy_router.post("/privacy/consent")
async def record_consent(payload: dict = Body(...), user: dict = Depends(get_current_user)):
    basis = (payload or {}).get("basis") or "consent"
    if basis not in CONSENT_BASES:
        raise HTTPException(status_code=400, detail="INVALID_BASIS")
    doc = {
        "id": uid(), "user_id": user["id"], "user_role": user.get("role", ""),
        "purpose": (payload or {}).get("purpose", ""), "basis": basis,
        "version": (payload or {}).get("version", ""), "source": (payload or {}).get("source", "app"),
        "status": "ACTIVE", "collected_at": now_iso(), "withdrawn_at": None, "created_at": now_iso(),
    }
    await db.consent_records.insert_one(doc)
    await _paudit(user, "consent_recorded", "consent", doc["id"], reason=doc["purpose"], new={"basis": basis})
    doc.pop("_id", None)
    return doc


@privacy_router.get("/privacy/consent/mine")
async def my_consents(user: dict = Depends(get_current_user)):
    return await db.consent_records.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@privacy_router.post("/privacy/consent/{cid}/withdraw")
async def withdraw_consent(cid: str, user: dict = Depends(get_current_user)):
    c = await db.consent_records.find_one({"id": cid, "user_id": user["id"]})
    if not c:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    if c.get("status") == "WITHDRAWN":
        return await db.consent_records.find_one({"id": cid}, {"_id": 0})
    # NOTE: withdrawal does NOT auto-delete data/account — that requires a defined policy.
    await db.consent_records.update_one({"id": cid}, {"$set": {"status": "WITHDRAWN", "withdrawn_at": now_iso()}})
    await _paudit(user, "consent_withdrawn", "consent", cid, reason=c.get("purpose", ""))
    return await db.consent_records.find_one({"id": cid}, {"_id": 0})


@privacy_router.get("/admin/privacy/consent")
async def admin_list_consent(user_id: Optional[str] = None, user: dict = Depends(require_permission("privacy.view"))):
    q = {"user_id": user_id} if user_id else {}
    return await db.consent_records.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)


# ==================================================================================
# 4) PRIVACY POLICY VERSIONING (stored in existing settings collection)
# ==================================================================================
async def _get_privacy_policy() -> dict:
    doc = await db.settings.find_one({"id": "privacy_policy"}, {"_id": 0})
    if not doc:
        doc = {"id": "privacy_policy", "privacy_policy_version": "draft-0", "effective_date": "",
               "policy_document_reference": "", "status": "DRAFT",
               "created_at": now_iso(), "updated_at": now_iso()}
        await db.settings.insert_one(dict(doc))
    return doc


@privacy_router.get("/privacy/policy")
async def get_policy(user: dict = Depends(get_current_user)):
    return await _get_privacy_policy()


@privacy_router.post("/privacy/policy/accept")
async def accept_policy(user: dict = Depends(get_current_user)):
    pol = await _get_privacy_policy()
    doc = {
        "id": uid(), "user_id": user["id"], "user_role": user.get("role", ""),
        "purpose": "privacy_policy_acceptance", "basis": "consent",
        "version": pol.get("privacy_policy_version", ""), "source": "app",
        "status": "ACTIVE", "collected_at": now_iso(), "withdrawn_at": None, "created_at": now_iso(),
    }
    await db.consent_records.insert_one(doc)
    await db.users.update_one({"id": user["id"]},
                              {"$set": {"privacy_policy_accepted_version": pol.get("privacy_policy_version", ""),
                                        "privacy_policy_accepted_at": now_iso()}})
    await _paudit(user, "privacy_policy_accepted", "privacy_policy", pol.get("privacy_policy_version", ""),
                  new={"version": pol.get("privacy_policy_version", "")})
    doc.pop("_id", None)
    return {"accepted_version": pol.get("privacy_policy_version", ""), "record": doc}


@privacy_router.get("/admin/privacy/policy")
async def admin_get_policy(user: dict = Depends(require_permission("privacy.view"))):
    return await _get_privacy_policy()


@privacy_router.put("/admin/privacy/policy")
async def admin_update_policy(payload: dict = Body(...), user: dict = Depends(require_permission("privacy.manage"))):
    old = await _get_privacy_policy()
    data = _pick(payload, ["privacy_policy_version", "effective_date", "policy_document_reference", "status"])
    data["updated_at"] = now_iso()
    await db.settings.update_one({"id": "privacy_policy"}, {"$set": data}, upsert=True)
    await _paudit(user, "privacy_policy_updated", "privacy_policy",
                  "privacy_policy", old={"v": old.get("privacy_policy_version")},
                  new={"v": data.get("privacy_policy_version")})
    return await _get_privacy_policy()


# ==================================================================================
# 5) DATA SUBJECT REQUESTS
# ==================================================================================
@privacy_router.post("/privacy/requests")
async def create_dsr(payload: dict = Body(...), user: dict = Depends(get_current_user)):
    rtype = (payload or {}).get("request_type", "")
    if rtype not in DSR_TYPES:
        raise HTTPException(status_code=400, detail="INVALID_REQUEST_TYPE")
    received = datetime.now(timezone.utc)
    doc = {
        "id": uid(), "requester_id": user["id"], "requester_role": user.get("role", ""),
        "request_type": rtype, "reason": (payload or {}).get("reason", ""),
        "status": "RECEIVED", "received_at": received.isoformat(),
        "due_at": (received + timedelta(days=DSR_RESPONSE_DAYS)).isoformat(),
        "resolved_at": None, "resolved_by": None, "resolution_notes": "",
        "created_at": now_iso(),
    }
    await db.data_subject_requests.insert_one(doc)
    await _paudit(user, "data_subject_request_created", "data_subject_request", doc["id"], reason=rtype)
    doc.pop("_id", None)
    return doc


@privacy_router.get("/privacy/requests/mine")
async def my_dsr(user: dict = Depends(get_current_user)):
    return await db.data_subject_requests.find({"requester_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@privacy_router.get("/admin/privacy/requests")
async def admin_list_dsr(status: Optional[str] = None, user: dict = Depends(require_permission("privacy.requests"))):
    q = {"status": status.upper()} if status else {}
    return await db.data_subject_requests.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)


@privacy_router.get("/admin/privacy/requests/{rid}")
async def admin_get_dsr(rid: str, user: dict = Depends(require_permission("privacy.requests"))):
    d = await db.data_subject_requests.find_one({"id": rid}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return d


@privacy_router.put("/admin/privacy/requests/{rid}/status")
async def admin_update_dsr(rid: str, payload: dict = Body(...), user: dict = Depends(require_permission("privacy.requests"))):
    d = await db.data_subject_requests.find_one({"id": rid})
    if not d:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    new_status = (payload or {}).get("status", "").upper()
    if new_status not in DSR_STATUSES:
        raise HTTPException(status_code=400, detail="INVALID_STATUS")
    updates = {"status": new_status, "resolution_notes": (payload or {}).get("resolution_notes", d.get("resolution_notes", ""))}
    if new_status in ("COMPLETED", "REJECTED", "APPROVED"):
        updates["resolved_at"] = now_iso()
        updates["resolved_by"] = user.get("name", "")
    await db.data_subject_requests.update_one({"id": rid}, {"$set": updates})
    await _paudit(user, "data_subject_request_resolved", "data_subject_request", rid,
                  old={"status": d.get("status")}, new={"status": new_status})
    return await db.data_subject_requests.find_one({"id": rid}, {"_id": 0})


# ==================================================================================
# 6) RECORDS OF PROCESSING ACTIVITIES (RoPA)
# ==================================================================================
ROPA_KEYS = ["name", "purpose", "data_categories", "data_subject_categories", "systems", "processors",
             "recipients", "retention_period", "storage_locations", "transfer_outside_oman",
             "transfer_country", "security_measures", "legal_basis", "owner", "review_date", "status"]


@privacy_router.get("/admin/privacy/ropa")
async def list_ropa(user: dict = Depends(require_permission("privacy.ropa"))):
    return await db.processing_activities.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@privacy_router.post("/admin/privacy/ropa")
async def create_ropa(payload: dict = Body(...), user: dict = Depends(require_permission("privacy.ropa"))):
    doc = {"id": uid(), "processing_activity_id": uid(), **{k: (payload or {}).get(k) for k in ROPA_KEYS},
           "created_at": now_iso(), "updated_at": now_iso()}
    if doc.get("status") is None:
        doc["status"] = "DRAFT"
    await db.processing_activities.insert_one(doc)
    await _paudit(user, "ropa_saved", "processing_activity", doc["id"], new={"name": doc.get("name")})
    doc.pop("_id", None)
    return doc


@privacy_router.put("/admin/privacy/ropa/{pid}")
async def update_ropa(pid: str, payload: dict = Body(...), user: dict = Depends(require_permission("privacy.ropa"))):
    existing = await db.processing_activities.find_one({"id": pid})
    if not existing:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    data = {k: (payload or {}).get(k) for k in ROPA_KEYS if k in (payload or {})}
    data["updated_at"] = now_iso()
    await db.processing_activities.update_one({"id": pid}, {"$set": data})
    await _paudit(user, "ropa_saved", "processing_activity", pid, new={"updated": list(data.keys())})
    return await db.processing_activities.find_one({"id": pid}, {"_id": 0})


# ==================================================================================
# 7) DATA RETENTION (policy only — NO auto deletion)
# ==================================================================================
RETENTION_KEYS = ["data_category", "retention_period", "retention_basis", "deletion_method",
                  "archive_required", "legal_hold", "status", "notes"]


@privacy_router.get("/admin/privacy/retention")
async def list_retention(user: dict = Depends(require_permission("privacy.view"))):
    return await db.retention_policies.find({}, {"_id": 0}).sort("data_category", 1).to_list(500)


@privacy_router.post("/admin/privacy/retention")
async def create_retention(payload: dict = Body(...), user: dict = Depends(require_permission("privacy.manage"))):
    doc = {"id": uid(), **{k: (payload or {}).get(k) for k in RETENTION_KEYS},
           "created_at": now_iso(), "updated_at": now_iso()}
    if doc.get("status") is None:
        doc["status"] = "DRAFT"
    await db.retention_policies.insert_one(doc)
    await _paudit(user, "retention_policy_changed", "retention_policy", doc["id"], new={"cat": doc.get("data_category")})
    doc.pop("_id", None)
    return doc


@privacy_router.put("/admin/privacy/retention/{rid}")
async def update_retention(rid: str, payload: dict = Body(...), user: dict = Depends(require_permission("privacy.manage"))):
    existing = await db.retention_policies.find_one({"id": rid})
    if not existing:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    data = {k: (payload or {}).get(k) for k in RETENTION_KEYS if k in (payload or {})}
    data["updated_at"] = now_iso()
    await db.retention_policies.update_one({"id": rid}, {"$set": data})
    await _paudit(user, "retention_policy_changed", "retention_policy", rid, new={"updated": list(data.keys())})
    return await db.retention_policies.find_one({"id": rid}, {"_id": 0})


# ==================================================================================
# 8/9) DATA BREACH / INCIDENT (structure + audit only — NO real notification)
# ==================================================================================
BREACH_KEYS = ["severity", "affected_data_categories", "affected_users_count", "description",
               "containment_status", "authority_notification_status", "user_notification_status",
               "incident_owner", "resolution"]


@privacy_router.get("/admin/privacy/breaches")
async def list_breaches(user: dict = Depends(require_permission("privacy.breaches"))):
    return await db.data_breaches.find({}, {"_id": 0}).sort("detected_at", -1).to_list(500)


@privacy_router.get("/admin/privacy/breaches/{bid}")
async def get_breach(bid: str, user: dict = Depends(require_permission("privacy.breaches"))):
    b = await db.data_breaches.find_one({"id": bid}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return b


@privacy_router.post("/admin/privacy/breaches")
async def create_breach(payload: dict = Body(...), user: dict = Depends(require_permission("privacy.breaches"))):
    doc = {
        "id": uid(), "status": "OPEN",
        "detected_at": (payload or {}).get("detected_at") or now_iso(),
        "reported_at": (payload or {}).get("reported_at"),
        **{k: (payload or {}).get(k) for k in BREACH_KEYS},
        "authority_notification_status": (payload or {}).get("authority_notification_status", "NOT_NOTIFIED"),
        "user_notification_status": (payload or {}).get("user_notification_status", "NOT_NOTIFIED"),
        "detected_by": user.get("name", ""),
        "history": [{"action": "created", "by": user.get("name", ""), "at": now_iso()}],
        "closed_at": None, "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.data_breaches.insert_one(doc)
    await _paudit(user, "breach_created", "data_breach", doc["id"], new={"severity": doc.get("severity")})
    doc.pop("_id", None)
    return doc


@privacy_router.put("/admin/privacy/breaches/{bid}/status")
async def update_breach_status(bid: str, payload: dict = Body(...), user: dict = Depends(require_permission("privacy.breaches"))):
    b = await db.data_breaches.find_one({"id": bid})
    if not b:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    new_status = (payload or {}).get("status", "").upper()
    if new_status not in BREACH_STATUSES:
        raise HTTPException(status_code=400, detail="INVALID_STATUS")
    updates = {"status": new_status, "updated_at": now_iso()}
    for k in ("authority_notification_status", "user_notification_status", "resolution", "containment_status"):
        if k in (payload or {}):
            updates[k] = payload[k]
    if new_status == "CLOSED":
        updates["closed_at"] = now_iso()
    await db.data_breaches.update_one(
        {"id": bid},
        {"$set": updates,
         "$push": {"history": {"action": f"status:{new_status}", "by": user.get("name", ""), "at": now_iso()}}},
    )
    await _paudit(user, "breach_status_changed", "data_breach", bid,
                  old={"status": b.get("status")}, new={"status": new_status})
    return await db.data_breaches.find_one({"id": bid}, {"_id": 0})


# ==================================================================================
# 10) DATA PROCESSORS / THIRD PARTIES
# ==================================================================================
PROCESSOR_KEYS = ["provider_name", "service_type", "country", "data_categories", "purpose",
                  "processor_or_recipient", "contract_reference", "active", "transfer_outside_oman", "security_notes"]


@privacy_router.get("/admin/privacy/processors")
async def list_processors(user: dict = Depends(require_permission("privacy.view"))):
    return await db.data_processors.find({}, {"_id": 0}).sort("provider_name", 1).to_list(500)


@privacy_router.post("/admin/privacy/processors")
async def create_processor(payload: dict = Body(...), user: dict = Depends(require_permission("privacy.manage"))):
    doc = {"id": uid(), **{k: (payload or {}).get(k) for k in PROCESSOR_KEYS},
           "created_at": now_iso(), "updated_at": now_iso()}
    if doc.get("active") is None:
        doc["active"] = True
    await db.data_processors.insert_one(doc)
    await _paudit(user, "processor_added", "data_processor", doc["id"], new={"name": doc.get("provider_name")})
    doc.pop("_id", None)
    return doc


# ==================================================================================
# 11) CROSS-BORDER TRANSFER READINESS (documentation only)
# ==================================================================================
TRANSFER_KEYS = ["data_categories", "destination_country", "recipient", "transfer_purpose", "legal_basis",
                 "explicit_consent_required", "consent_status", "protection_assessment", "approval_status", "notes"]


@privacy_router.get("/admin/privacy/transfers")
async def list_transfers(user: dict = Depends(require_permission("privacy.view"))):
    return await db.cross_border_transfers.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@privacy_router.post("/admin/privacy/transfers")
async def create_transfer(payload: dict = Body(...), user: dict = Depends(require_permission("privacy.manage"))):
    doc = {"id": uid(), "transfer_id": uid(), **{k: (payload or {}).get(k) for k in TRANSFER_KEYS},
           "created_at": now_iso(), "updated_at": now_iso()}
    if doc.get("approval_status") is None:
        doc["approval_status"] = "PENDING"
    await db.cross_border_transfers.insert_one(doc)
    await _paudit(user, "transfer_recorded", "cross_border_transfer", doc["id"],
                  new={"destination": doc.get("destination_country")})
    doc.pop("_id", None)
    return doc


# ==================================================================================
# 12) DPO + 17) DATA RESIDENCY (stored in existing settings collection)
# ==================================================================================
async def _get_setting(sid: str, default: dict) -> dict:
    doc = await db.settings.find_one({"id": sid}, {"_id": 0})
    if not doc:
        doc = {"id": sid, **default, "created_at": now_iso(), "updated_at": now_iso()}
        await db.settings.insert_one(dict(doc))
    return doc


@privacy_router.get("/admin/privacy/dpo")
async def get_dpo(user: dict = Depends(require_permission("privacy.view"))):
    return await _get_setting("dpo", {"dpo_name": "", "dpo_contact": "", "dpo_status": "NOT_APPOINTED",
                                      "appointed_at": "", "privacy_contact_email": "", "privacy_contact_phone": ""})


@privacy_router.put("/admin/privacy/dpo")
async def update_dpo(payload: dict = Body(...), user: dict = Depends(require_permission("privacy.manage"))):
    await _get_setting("dpo", {"dpo_status": "NOT_APPOINTED"})
    data = _pick(payload, ["dpo_name", "dpo_contact", "dpo_status", "appointed_at",
                           "privacy_contact_email", "privacy_contact_phone"])
    data["updated_at"] = now_iso()
    await db.settings.update_one({"id": "dpo"}, {"$set": data}, upsert=True)
    await _paudit(user, "dpo_updated", "dpo", "dpo", new=data)
    return await db.settings.find_one({"id": "dpo"}, {"_id": 0})


@privacy_router.get("/admin/privacy/residency")
async def get_residency(user: dict = Depends(require_permission("privacy.view"))):
    import os
    default = {"environment": (os.environ.get("APP_ENV") or "development").lower(),
               "database_region": "UNKNOWN", "object_storage_region": "UNKNOWN",
               "backup_region": "UNKNOWN", "logs_region": "UNKNOWN",
               "notes": "Preview/dev environment — NOT a production Oman residency claim."}
    return await _get_setting("data_residency", default)


@privacy_router.put("/admin/privacy/residency")
async def update_residency(payload: dict = Body(...), user: dict = Depends(require_permission("privacy.manage"))):
    await _get_setting("data_residency", {"environment": "development"})
    data = _pick(payload, ["environment", "database_region", "object_storage_region",
                           "backup_region", "logs_region", "notes"])
    data["updated_at"] = now_iso()
    await db.settings.update_one({"id": "data_residency"}, {"$set": data}, upsert=True)
    await _paudit(user, "residency_updated", "data_residency", "data_residency", new=data)
    return await db.settings.find_one({"id": "data_residency"}, {"_id": 0})


# ==================================================================================
# SEED — truthful starter governance data (idempotent). No fabricated values.
# ==================================================================================
async def seed_privacy_governance():
    import os
    # Data classification catalog (reflects the actual CARGO data model).
    if await db.data_classifications.count_documents({}) == 0:
        catalog = [
            ("users", "name", "PERSONAL"), ("users", "phone", "PERSONAL"),
            ("users", "email", "PERSONAL"), ("users", "address", "PERSONAL"),
            ("users", "password_hash", "AUTHENTICATION"),
            ("users", "regulatory", "REGULATORY"), ("users", "carrier_license", "REGULATORY"),
            ("otps", "code", "AUTHENTICATION"),
            ("documents", "file", "SENSITIVE_PERSONAL"), ("documents", "reference", "REGULATORY"),
            ("shipments", "pickup_location", "LOCATION"), ("shipments", "delivery_location", "LOCATION"),
            ("shipments", "images", "PERSONAL"),
            ("trips", "tracking_events", "LOCATION"), ("trips", "delivery_proof", "LOCATION"),
            ("vehicles", "plate_number", "REGULATORY"), ("vehicles", "regulatory", "REGULATORY"),
            ("chat_messages", "text", "PERSONAL"),
            ("transactions", "amount", "FINANCIAL"),
            ("audit_logs", "*", "INTERNAL"),
        ]
        await db.data_classifications.insert_many([
            {"id": uid(), "collection": c, "field": f, "category": cat, "notes": "seeded",
             "active": True, "created_at": now_iso(), "updated_at": now_iso()}
            for (c, f, cat) in catalog
        ])
    # Known current external processor (the ONLY external egress today).
    if not await db.data_processors.find_one({"provider_name": "OpenStreetMap Nominatim"}):
        await db.data_processors.insert_one({
            "id": uid(), "provider_name": "OpenStreetMap Nominatim", "service_type": "Maps/Geocoding",
            "country": "EU/Global (outside Oman)", "data_categories": ["LOCATION"],
            "purpose": "Forward/reverse geocoding of pickup/delivery coordinates",
            "processor_or_recipient": "processor", "contract_reference": "",
            "active": True, "transfer_outside_oman": True,
            "security_notes": "Public API; coordinates+address queries leave Oman. Pending assessment.",
            "created_at": now_iso(), "updated_at": now_iso(),
        })
    # Documented cross-border transfer for that processor (documentation only).
    if not await db.cross_border_transfers.find_one({"recipient": "OpenStreetMap Nominatim"}):
        await db.cross_border_transfers.insert_one({
            "id": uid(), "transfer_id": uid(), "data_categories": ["LOCATION"],
            "destination_country": "Outside Oman (OSM servers)", "recipient": "OpenStreetMap Nominatim",
            "transfer_purpose": "Geocoding", "legal_basis": "pending_legal_review",
            "explicit_consent_required": True, "consent_status": "NOT_COLLECTED",
            "protection_assessment": "NOT_DONE", "approval_status": "PENDING",
            "notes": "Documented for readiness; not an authorization to transfer.",
            "created_at": now_iso(), "updated_at": now_iso(),
        })
    # Starter RoPA entries reflecting real CARGO processing (extensible).
    if await db.processing_activities.count_documents({}) == 0:
        await db.processing_activities.insert_many([
            {"id": uid(), "processing_activity_id": uid(), "name": "User account & identity",
             "purpose": "Account creation, authentication, role management",
             "data_categories": ["PERSONAL", "AUTHENTICATION"], "data_subject_categories": ["customer", "driver", "provider", "admin"],
             "systems": ["MongoDB users", "JWT", "OTP"], "processors": [], "recipients": [],
             "retention_period": "", "storage_locations": ["MongoDB"], "transfer_outside_oman": False,
             "transfer_country": "", "security_measures": ["RBAC", "JWT", "bcrypt(admin)"],
             "legal_basis": "contractual_necessity", "owner": "", "review_date": "", "status": "DRAFT",
             "created_at": now_iso(), "updated_at": now_iso()},
            {"id": uid(), "processing_activity_id": uid(), "name": "Shipment & trip location processing",
             "purpose": "Pickup/delivery locations, trip tracking, proof of delivery",
             "data_categories": ["LOCATION", "PERSONAL"], "data_subject_categories": ["customer", "driver"],
             "systems": ["MongoDB shipments/trips", "Nominatim geocoding"],
             "processors": ["OpenStreetMap Nominatim"], "recipients": [],
             "retention_period": "", "storage_locations": ["MongoDB"], "transfer_outside_oman": True,
             "transfer_country": "Outside Oman (OSM)", "security_measures": ["RBAC", "object-level authz"],
             "legal_basis": "contractual_necessity", "owner": "", "review_date": "", "status": "DRAFT",
             "created_at": now_iso(), "updated_at": now_iso()},
        ])
    # Starter retention policies — placeholders only, NO durations asserted, NO auto-deletion.
    if await db.retention_policies.count_documents({}) == 0:
        for cat in ["PERSONAL", "AUTHENTICATION", "LOCATION", "FINANCIAL", "REGULATORY", "INTERNAL", "SENSITIVE_PERSONAL"]:
            await db.retention_policies.insert_one({
                "id": uid(), "data_category": cat, "retention_period": "",
                "retention_basis": "pending_legal_review", "deletion_method": "",
                "archive_required": False, "legal_hold": False, "status": "DRAFT",
                "notes": "Placeholder — duration pending legal/administrative decision.",
                "created_at": now_iso(), "updated_at": now_iso(),
            })
    # Privacy policy + DPO + residency singletons (lazy, honest defaults).
    await _get_privacy_policy()
    await _get_setting("dpo", {"dpo_name": "", "dpo_contact": "", "dpo_status": "NOT_APPOINTED",
                               "appointed_at": "", "privacy_contact_email": "", "privacy_contact_phone": ""})
    await _get_setting("data_residency", {"environment": (os.environ.get("APP_ENV") or "development").lower(),
                                          "database_region": "UNKNOWN", "object_storage_region": "UNKNOWN",
                                          "backup_region": "UNKNOWN", "logs_region": "UNKNOWN",
                                          "notes": "Preview/dev environment — NOT a production Oman residency claim."})
