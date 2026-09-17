"""Phase 1.1: cargo categories, configurable documents, RBAC, finance ledger."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import db
from auth import get_current_user, require_roles, hash_password

extra_api = APIRouter(prefix="/api")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return str(uuid.uuid4())


# ---------------- Permissions catalog ----------------
PERMISSIONS = [
    "users.view", "users.create", "users.edit", "users.suspend", "users.delete",
    "shipments.view", "shipments.edit", "shipments.cancel", "shipments.assign", "shipments.override",
    "documents.view", "documents.review", "documents.approve", "documents.reject",
    "finance.view", "finance.transactions", "finance.commission", "finance.payouts", "finance.adjust", "finance.refund",
    "reports.view", "reports.export",
    "system.settings", "system.roles", "system.permissions", "system.audit",
]


async def get_user_permissions(user: dict) -> List[str]:
    if user.get("role") != "admin":
        return []
    role_key = user.get("admin_role_key", "super_admin")
    if role_key == "super_admin":
        return list(PERMISSIONS)
    role = await db.roles.find_one({"key": role_key})
    return role.get("permissions", []) if role else []


def require_permission(perm: str):
    async def dep(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        perms = await get_user_permissions(user)
        if perm not in perms:
            raise HTTPException(status_code=403, detail=f"Missing permission: {perm}")
        return user
    return dep


async def audit(actor, action, entity, entity_id, old=None, new=None, reason=""):
    await db.audit_logs.insert_one({
        "id": uid(), "admin_id": actor["id"], "admin_name": actor.get("name", ""),
        "action": action, "entity": entity, "entity_id": entity_id,
        "old_value": old, "new_value": new, "reason": reason,
        "result": "success", "timestamp": now_iso(),
    })


async def notify(user_id, type_, ta, te, ba="", be="", entity_type=None, entity_id=None, meta=None):
    m = meta or {}
    if entity_type:
        m["entity_type"] = entity_type
    if entity_id:
        m["entity_id"] = entity_id
    await db.notifications.insert_one({
        "id": uid(), "user_id": user_id, "type": type_, "title_ar": ta, "title_en": te,
        "body_ar": ba, "body_en": be, "read": False, "meta": m,
        "entity_type": entity_type, "entity_id": entity_id, "created_at": now_iso(),
    })


# ================= CATEGORIES =================
class CategoryBody(BaseModel):
    key: Optional[str] = None
    name_ar: str
    name_en: str
    icon: Optional[str] = "package"
    active: Optional[bool] = True
    order: Optional[int] = 0


@extra_api.get("/categories")
async def list_categories():
    return await db.cargo_categories.find({"active": True}, {"_id": 0}).sort("order", 1).to_list(100)


@extra_api.get("/admin/categories")
async def admin_list_categories(user: dict = Depends(require_roles("admin"))):
    return await db.cargo_categories.find({}, {"_id": 0}).sort("order", 1).to_list(100)


@extra_api.post("/admin/categories")
async def admin_create_category(body: CategoryBody, user: dict = Depends(require_permission("system.settings"))):
    doc = {"id": uid(), "key": body.key or uid()[:8], "name_ar": body.name_ar, "name_en": body.name_en,
           "icon": body.icon, "active": body.active, "order": body.order, "created_at": now_iso()}
    await db.cargo_categories.insert_one(doc)
    await audit(user, "category_created", "category", doc["id"], new=body.name_en)
    doc.pop("_id", None)
    return doc


# ================= DOCUMENT TYPES + DOCUMENTS =================
class DocTypeBody(BaseModel):
    key: Optional[str] = None
    name_ar: str
    name_en: str
    owner_type: str = "driver"  # driver | vehicle | provider
    required: bool = False
    has_expiry: bool = True
    active: bool = True


class DocumentBody(BaseModel):
    doc_type_key: str
    file: Optional[str] = ""  # base64 data url or reference
    reference: Optional[str] = ""
    expiry: Optional[str] = ""
    vehicle_id: Optional[str] = None


class DocReview(BaseModel):
    action: str  # approve | reject
    reason: Optional[str] = ""
    notes: Optional[str] = ""


@extra_api.get("/document-types")
async def list_doc_types(owner: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"active": True}
    if owner:
        q["owner_type"] = owner
    return await db.document_types.find(q, {"_id": 0}).to_list(100)


@extra_api.post("/admin/document-types")
async def create_doc_type(body: DocTypeBody, user: dict = Depends(require_permission("system.settings"))):
    doc = {"id": uid(), "key": body.key or uid()[:8], **body.model_dump(exclude={"key"}), "created_at": now_iso()}
    await db.document_types.insert_one(doc)
    await audit(user, "doctype_created", "document_type", doc["id"], new=body.name_en)
    doc.pop("_id", None)
    return doc


def _doc_status(expiry):
    if expiry:
        try:
            exp = datetime.fromisoformat(expiry)
            if exp.date() < datetime.now(timezone.utc).date():
                return "EXPIRED"
        except Exception:
            pass
    return None


@extra_api.post("/documents")
async def upload_document(body: DocumentBody, user: dict = Depends(get_current_user)):
    if user["role"] not in ("driver", "provider"):
        raise HTTPException(status_code=403, detail="Only drivers/providers upload documents")
    dt = await db.document_types.find_one({"key": body.doc_type_key})
    doc = {
        "id": uid(), "owner_id": user["id"], "owner_role": user["role"], "owner_name": user.get("name", ""),
        "doc_type_key": body.doc_type_key,
        "doc_type_name_ar": dt.get("name_ar") if dt else body.doc_type_key,
        "doc_type_name_en": dt.get("name_en") if dt else body.doc_type_key,
        "file": body.file or "", "reference": body.reference or "", "expiry": body.expiry or "",
        "vehicle_id": body.vehicle_id, "status": "PENDING",
        "uploaded_at": now_iso(), "reviewed_by": None, "reviewed_at": None,
        "rejection_reason": "", "notes": "",
    }
    # replace existing same-type doc for this owner
    await db.documents.delete_many({"owner_id": user["id"], "doc_type_key": body.doc_type_key})
    await db.documents.insert_one(doc)
    doc.pop("_id", None)
    return doc


@extra_api.get("/documents/mine")
async def my_documents(user: dict = Depends(get_current_user)):
    return await db.documents.find({"owner_id": user["id"]}, {"_id": 0}).sort("uploaded_at", -1).to_list(200)


@extra_api.get("/admin/documents")
async def admin_documents(status: Optional[str] = None, expiring: Optional[bool] = None,
                          owner_role: Optional[str] = None, doc_type: Optional[str] = None,
                          user: dict = Depends(require_permission("documents.view"))):
    q = {}
    if status:
        q["status"] = status
    if owner_role:
        q["owner_role"] = owner_role
    if doc_type:
        q["doc_type_key"] = doc_type
    docs = await db.documents.find(q, {"_id": 0}).sort("uploaded_at", -1).to_list(1000)
    today = datetime.now(timezone.utc).date()
    out = []
    for d in docs:
        flag = "OK"
        if d.get("expiry"):
            try:
                exp = datetime.fromisoformat(d["expiry"]).date()
                days = (exp - today).days
                if days < 0:
                    flag = "EXPIRED"
                elif days <= 30:
                    flag = "EXPIRING"
            except Exception:
                pass
        d["expiry_flag"] = flag
        if expiring and flag not in ("EXPIRED", "EXPIRING"):
            continue
        out.append(d)
    return out


@extra_api.post("/admin/documents/{doc_id}/review")
async def review_document(doc_id: str, body: DocReview, user: dict = Depends(require_permission("documents.review"))):
    d = await db.documents.find_one({"id": doc_id})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    new_status = "APPROVED" if body.action == "approve" else "REJECTED"
    await db.documents.update_one({"id": doc_id}, {"$set": {
        "status": new_status, "reviewed_by": user.get("name"), "reviewed_at": now_iso(),
        "rejection_reason": body.reason or "", "notes": body.notes or "",
    }})
    await audit(user, f"document_{body.action}", "document", doc_id, old=d.get("status"), new=new_status, reason=body.reason)
    ta, te = ("تم اعتماد المستند", "Document approved") if new_status == "APPROVED" else ("تم رفض المستند", "Document rejected")
    await notify(d["owner_id"], "document", ta, te, body.reason or "", body.reason or "",
                 entity_type="document", entity_id=doc_id)
    return await db.documents.find_one({"id": doc_id}, {"_id": 0})


# ================= RBAC =================
class RoleBody(BaseModel):
    key: Optional[str] = None
    name_ar: str
    name_en: str
    permissions: List[str] = []


class AdminUserBody(BaseModel):
    name: str
    email: str
    password: str
    admin_role_key: str = "operations_manager"


class AssignRoleBody(BaseModel):
    admin_role_key: str


@extra_api.get("/admin/permissions")
async def get_permissions(user: dict = Depends(require_permission("system.roles"))):
    return {"permissions": PERMISSIONS}


@extra_api.get("/admin/roles")
async def list_roles(user: dict = Depends(require_permission("system.roles"))):
    return await db.roles.find({}, {"_id": 0}).to_list(100)


@extra_api.post("/admin/roles")
async def create_role(body: RoleBody, user: dict = Depends(require_permission("system.roles"))):
    doc = {"id": uid(), "key": body.key or body.name_en.lower().replace(" ", "_"),
           "name_ar": body.name_ar, "name_en": body.name_en, "permissions": body.permissions, "created_at": now_iso()}
    await db.roles.insert_one(doc)
    await audit(user, "role_created", "role", doc["id"], new=body.name_en)
    doc.pop("_id", None)
    return doc


@extra_api.put("/admin/roles/{role_id}")
async def update_role(role_id: str, body: RoleBody, user: dict = Depends(require_permission("system.roles"))):
    r = await db.roles.find_one({"id": role_id})
    if not r:
        raise HTTPException(status_code=404, detail="Role not found")
    await db.roles.update_one({"id": role_id}, {"$set": {
        "name_ar": body.name_ar, "name_en": body.name_en, "permissions": body.permissions}})
    await audit(user, "role_updated", "role", role_id, old=r.get("permissions"), new=body.permissions)
    return await db.roles.find_one({"id": role_id}, {"_id": 0})


@extra_api.get("/admin/admins")
async def list_admins(user: dict = Depends(require_permission("users.view"))):
    return await db.users.find({"role": "admin"}, {"_id": 0, "password_hash": 0}).to_list(200)


@extra_api.post("/admin/admins")
async def create_admin(body: AdminUserBody, user: dict = Depends(require_permission("users.create"))):
    existing = await db.users.find_one({"email": body.email.lower(), "role": "admin"})
    if existing:
        raise HTTPException(status_code=400, detail="Admin with this email exists")
    doc = {"id": uid(), "role": "admin", "name": body.name, "email": body.email.lower(),
           "password_hash": hash_password(body.password), "admin_role_key": body.admin_role_key,
           "status": "active", "created_at": now_iso()}
    await db.users.insert_one(doc)
    await audit(user, "admin_created", "user", doc["id"], new=body.email, reason=f"role={body.admin_role_key}")
    return {"id": doc["id"], "name": body.name, "email": body.email, "admin_role_key": body.admin_role_key}


@extra_api.put("/admin/admins/{admin_id}/role")
async def assign_role(admin_id: str, body: AssignRoleBody, user: dict = Depends(require_permission("system.roles"))):
    a = await db.users.find_one({"id": admin_id, "role": "admin"})
    if not a:
        raise HTTPException(status_code=404, detail="Admin not found")
    await db.users.update_one({"id": admin_id}, {"$set": {"admin_role_key": body.admin_role_key}})
    await audit(user, "role_assigned", "user", admin_id, old=a.get("admin_role_key"), new=body.admin_role_key)
    return {"success": True}


@extra_api.get("/admin/me/permissions")
async def my_permissions(user: dict = Depends(require_roles("admin"))):
    return {"role_key": user.get("admin_role_key", "super_admin"), "permissions": await get_user_permissions(user)}


# ================= FINANCE =================
class SettingsBody(BaseModel):
    commission_type: str = "percentage"  # percentage | fixed
    commission_value: float = 10
    currency: str = "OMR"


class AdjustBody(BaseModel):
    account_id: str
    account_role: str
    amount: float
    reason: str
    description: Optional[str] = ""


async def get_settings():
    s = await db.settings.find_one({"id": "platform"})
    if not s:
        s = {"id": "platform", "commission_type": "percentage", "commission_value": 10, "currency": "OMR"}
        await db.settings.insert_one(dict(s))
    s.pop("_id", None)
    return s


async def record_trip_completion(trip: dict):
    """Immutable ledger entries when a trip completes."""
    if await db.transactions.find_one({"trip_id": trip["id"], "type": "driver_earning"}):
        return
    s = await get_settings()
    gross = float(trip.get("price", 0) or 0)
    commission = round(gross * s["commission_value"] / 100, 3) if s["commission_type"] == "percentage" else float(s["commission_value"])
    commission = min(commission, gross)
    net = round(gross - commission, 3)
    cur = s["currency"]
    base = {"shipment_id": trip.get("shipment_id"), "trip_id": trip["id"], "currency": cur,
            "status": "COMPLETED", "created_by": "system", "created_at": now_iso()}
    txns = [
        {**base, "id": uid(), "type": "customer_payment", "account_id": trip["customer_id"], "account_role": "customer",
         "amount": gross, "gross": gross, "commission": 0, "net": gross, "description": f"Payment for {trip.get('shipment_title','')}"},
        {**base, "id": uid(), "type": "platform_commission", "account_id": None, "account_role": "platform",
         "amount": commission, "gross": gross, "commission": commission, "net": commission, "description": "Platform commission"},
        {**base, "id": uid(), "type": "driver_earning", "account_id": trip["driver_id"], "account_role": "driver",
         "amount": net, "gross": gross, "commission": commission, "net": net, "description": f"Earning for {trip.get('shipment_title','')}"},
    ]
    if trip.get("provider_id"):
        txns[-1]["account_role"] = "provider"
        txns[-1]["account_id"] = trip["provider_id"]
    await db.transactions.insert_many(txns)


@extra_api.get("/admin/finance/settings")
async def finance_settings(user: dict = Depends(require_permission("finance.view"))):
    return await get_settings()


@extra_api.put("/admin/finance/settings")
async def update_finance_settings(body: SettingsBody, user: dict = Depends(require_permission("finance.commission"))):
    old = await get_settings()
    await db.settings.update_one({"id": "platform"}, {"$set": body.model_dump()}, upsert=True)
    await audit(user, "commission_updated", "settings", "platform", old=old, new=body.model_dump())
    return await get_settings()


@extra_api.get("/admin/finance/stats")
async def finance_stats(user: dict = Depends(require_permission("finance.view"))):
    txns = await db.transactions.find({}, {"_id": 0}).to_list(5000)
    def total(t):
        return round(sum(x["amount"] for x in txns if x["type"] == t), 3)
    s = await get_settings()
    return {
        "currency": s["currency"],
        "total_revenue": total("customer_payment"),
        "total_commission": total("platform_commission"),
        "driver_earnings": total("driver_earning"),
        "provider_earnings": total("provider_earning"),
        "refunds": total("refund"),
        "adjustments": total("adjustment"),
        "payouts": total("payout"),
        "transaction_count": len(txns),
    }


@extra_api.get("/admin/finance/transactions")
async def list_transactions(type: Optional[str] = None, status: Optional[str] = None,
                            account_role: Optional[str] = None, q: Optional[str] = None,
                            user: dict = Depends(require_permission("finance.transactions"))):
    query = {}
    if type:
        query["type"] = type
    if status:
        query["status"] = status
    if account_role:
        query["account_role"] = account_role
    txns = await db.transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    # attach account names
    ids = list({t["account_id"] for t in txns if t.get("account_id")})
    users = {u["id"]: u.get("name") for u in await db.users.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)}
    for t in txns:
        t["account_name"] = users.get(t.get("account_id"), "CARGO Platform" if t["account_role"] == "platform" else "—")
    if q:
        ql = q.lower()
        txns = [t for t in txns if ql in (t.get("account_name") or "").lower() or ql in (t.get("description") or "").lower()]
    return txns


@extra_api.get("/admin/finance/balances")
async def balances(role: str = "driver", user: dict = Depends(require_permission("finance.view"))):
    earn_type = "provider_earning" if role == "provider" else "driver_earning" if role == "driver" else "customer_payment"
    pipeline = [
        {"$match": {"account_role": role}},
        {"$group": {"_id": "$account_id",
                    "earned": {"$sum": {"$cond": [{"$eq": ["$type", earn_type]}, "$amount", 0]}},
                    "payouts": {"$sum": {"$cond": [{"$eq": ["$type", "payout"]}, "$amount", 0]}},
                    "adjustments": {"$sum": {"$cond": [{"$eq": ["$type", "adjustment"]}, "$amount", 0]}},
                    "refunds": {"$sum": {"$cond": [{"$eq": ["$type", "refund"]}, "$amount", 0]}}}},
    ]
    rows = await db.transactions.aggregate(pipeline).to_list(1000)
    ids = [r["_id"] for r in rows if r["_id"]]
    users = {u["id"]: u for u in await db.users.find({"id": {"$in": ids}}, {"_id": 0, "password_hash": 0}).to_list(1000)}
    out = []
    for r in rows:
        u = users.get(r["_id"], {})
        available = round(r["earned"] + r["adjustments"] - r["payouts"] - r["refunds"], 3)
        out.append({"account_id": r["_id"], "name": u.get("name", "—"), "company_name": u.get("company_name", ""),
                    "earned": round(r["earned"], 3), "payouts": round(r["payouts"], 3),
                    "adjustments": round(r["adjustments"], 3), "available": available})
    return out


@extra_api.post("/admin/finance/adjust")
async def create_adjustment(body: AdjustBody, user: dict = Depends(require_permission("finance.adjust"))):
    s = await get_settings()
    txn = {"id": uid(), "type": "adjustment", "account_id": body.account_id, "account_role": body.account_role,
           "shipment_id": None, "trip_id": None, "amount": body.amount, "gross": body.amount,
           "commission": 0, "net": body.amount, "currency": s["currency"], "status": "COMPLETED",
           "description": body.description or "Manual adjustment", "reason": body.reason,
           "created_by": user.get("name"), "created_at": now_iso()}
    await db.transactions.insert_one(txn)
    await audit(user, "financial_adjustment", "transaction", txn["id"], new=body.amount, reason=body.reason)
    txn.pop("_id", None)
    return txn


# ================= OPS STATS =================
@extra_api.get("/admin/ops-stats")
async def ops_stats(user: dict = Depends(require_roles("admin"))):
    today = datetime.now(timezone.utc).date()
    docs = await db.documents.find({}, {"_id": 0, "expiry": 1, "status": 1}).to_list(5000)
    expiring = expired = 0
    for d in docs:
        if d.get("expiry"):
            try:
                days = (datetime.fromisoformat(d["expiry"]).date() - today).days
                if days < 0:
                    expired += 1
                elif days <= 30:
                    expiring += 1
            except Exception:
                pass
    return {
        "customers": await db.users.count_documents({"role": "customer"}),
        "active_drivers": await db.users.count_documents({"role": "driver", "verification_status": "APPROVED"}),
        "pending_drivers": await db.users.count_documents({"role": "driver", "verification_status": {"$in": ["PENDING", "UNDER_REVIEW"]}}),
        "providers": await db.users.count_documents({"role": "provider"}),
        "active_shipments": await db.shipments.count_documents({"status": {"$in": ["PUBLISHED", "BIDDING", "DRIVER_ASSIGNED", "IN_TRANSIT"]}}),
        "bidding_shipments": await db.shipments.count_documents({"status": "BIDDING"}),
        "active_trips": await db.trips.count_documents({"status": {"$nin": ["COMPLETED", "CANCELLED"]}}),
        "completed_trips": await db.trips.count_documents({"status": "COMPLETED"}),
        "cancelled_shipments": await db.shipments.count_documents({"status": "CANCELLED"}),
        "pending_documents": await db.documents.count_documents({"status": "PENDING"}),
        "expiring_documents": expiring, "expired_documents": expired,
        "pending_transactions": await db.transactions.count_documents({"status": "PENDING"}),
    }
