"""Phase 1.1: cargo categories, configurable documents, RBAC, finance ledger."""
import uuid
import httpx
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
    "finance.view", "finance.transactions", "finance.commission", "finance.payouts", "finance.adjust", "finance.refund", "finance.reverse",
    "reports.view", "reports.export",
    "system.settings", "system.roles", "system.permissions", "system.audit",
    "disputes.view", "disputes.resolve",
    "privacy.view", "privacy.manage", "privacy.requests", "privacy.breaches", "privacy.ropa",
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
                          owner_type: Optional[str] = None, q: Optional[str] = None,
                          user: dict = Depends(require_permission("documents.view"))):
    """List documents for admin review. Supports filters:
    - status: PENDING | APPROVED | REJECTED
    - owner_role: driver | provider
    - owner_type: driver | vehicle | provider   (derived via document_types)
    - doc_type: document_types.key
    - expiring: True limits to EXPIRED or EXPIRING soon
    - q: free-text search across owner name and doc_type name
    """
    query = {}
    if status:
        query["status"] = status
    if owner_role:
        query["owner_role"] = owner_role
    if doc_type:
        query["doc_type_key"] = doc_type
    docs = await db.documents.find(query, {"_id": 0}).sort("uploaded_at", -1).to_list(2000)

    # Build a doc_type_key -> owner_type map so we can classify DRIVER vs VEHICLE documents.
    types = await db.document_types.find({}, {"_id": 0, "key": 1, "owner_type": 1}).to_list(200)
    type_owner = {t["key"]: t.get("owner_type", "driver") for t in types}

    today = datetime.now(timezone.utc).date()
    ql = (q or "").lower().strip()
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
        d["owner_type"] = type_owner.get(d.get("doc_type_key"), "driver")
        if expiring and flag not in ("EXPIRED", "EXPIRING"):
            continue
        if owner_type and d["owner_type"] != owner_type:
            continue
        if ql and ql not in (d.get("owner_name", "") or "").lower() \
                and ql not in (d.get("doc_type_name_en", "") or "").lower() \
                and ql not in (d.get("doc_type_name_ar", "") or "").lower() \
                and ql not in (d.get("reference", "") or "").lower():
            continue
        out.append(d)
    return out


@extra_api.get("/admin/documents/{doc_id}")
async def admin_document_detail(doc_id: str, user: dict = Depends(require_permission("documents.view"))):
    d = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    dt = await db.document_types.find_one({"key": d.get("doc_type_key")}, {"_id": 0})
    d["owner_type"] = dt.get("owner_type", "driver") if dt else "driver"
    return d


@extra_api.post("/admin/documents/{doc_id}/review")
async def review_document(doc_id: str, body: DocReview, user: dict = Depends(require_permission("documents.review"))):
    d = await db.documents.find_one({"id": doc_id})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Invalid action")
    new_status = "APPROVED" if body.action == "approve" else "REJECTED"
    old_status = d.get("status")
    await db.documents.update_one({"id": doc_id}, {"$set": {
        "status": new_status,
        "reviewed_by": user.get("name"),
        "reviewed_by_id": user["id"],
        "reviewed_at": now_iso(),
        "rejection_reason": body.reason or "" if new_status == "REJECTED" else "",
        "notes": body.notes or "",
    }})
    action_name = "DOCUMENT_APPROVED" if new_status == "APPROVED" else "DOCUMENT_REJECTED"
    await db.audit_logs.insert_one({
        "id": uid(), "admin_id": user["id"], "admin_name": user.get("name", ""),
        "actor_id": user["id"], "actor_name": user.get("name", ""), "actor_role": user.get("admin_role_key", "admin"),
        "action": action_name, "entity": "document", "entity_id": doc_id,
        "old_value": {"status": old_status},
        "new_value": {"status": new_status, "owner_id": d.get("owner_id"),
                      "owner_role": d.get("owner_role"), "doc_type_key": d.get("doc_type_key"),
                      "rejection_reason": body.reason or "", "notes": body.notes or ""},
        "reason": body.reason or "", "result": "success", "timestamp": now_iso(),
    })
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
    if body.key == "super_admin" and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="PLATFORM_ADMIN_ROLE_REQUIRED")
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
    if r.get("key") == "super_admin" and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="SUPER_ADMIN_PROTECTED")
    if body.key == "super_admin" and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="PLATFORM_ADMIN_ROLE_REQUIRED")
    await db.roles.update_one({"id": role_id}, {"$set": {
        "name_ar": body.name_ar, "name_en": body.name_en, "permissions": body.permissions}})
    await audit(user, "role_updated", "role", role_id, old=r.get("permissions"), new=body.permissions)
    return await db.roles.find_one({"id": role_id}, {"_id": 0})


@extra_api.get("/admin/admins")
async def list_admins(user: dict = Depends(require_permission("users.view"))):
    return await db.users.find({"role": "admin"}, {"_id": 0, "password_hash": 0}).to_list(200)


@extra_api.post("/admin/admins")
async def create_admin(body: AdminUserBody, user: dict = Depends(require_permission("users.create"))):
    if body.admin_role_key == "super_admin" and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="PLATFORM_ADMIN_ROLE_REQUIRED")
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
    _protect_super_admin_target(user, a)
    if body.admin_role_key == "super_admin" and not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="PLATFORM_ADMIN_ROLE_REQUIRED")
    await _ensure_not_last_super_admin_demotion(a, body.admin_role_key)
    await db.users.update_one({"id": admin_id}, {"$set": {"admin_role_key": body.admin_role_key}})
    await audit(user, "role_assigned", "user", admin_id, old=a.get("admin_role_key"), new=body.admin_role_key)
    return {"success": True}


@extra_api.get("/admin/me/permissions")
async def my_permissions(user: dict = Depends(require_roles("admin"))):
    return {"role_key": user.get("admin_role_key", "super_admin"), "permissions": await get_user_permissions(user)}


# ================= USER MANAGEMENT =================
class UserUpdateBody(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    admin_role_key: Optional[str] = None


class StatusBody(BaseModel):
    status: str  # active | disabled


class ResetPwBody(BaseModel):
    password: str


def _is_disabled(u: dict) -> bool:
    return (u.get("status") or "active").lower() in ("disabled", "inactive", "suspended")


def _is_super_admin(user: dict) -> bool:
    return user.get("role") == "admin" and user.get("admin_role_key") == "super_admin"


def _is_super_admin_target(target: dict) -> bool:
    return target.get("role") == "admin" and target.get("admin_role_key") == "super_admin"


def _protect_super_admin_target(actor: dict, target: dict):
    """Only a platform super_admin may operate on a platform super_admin account."""
    if _is_super_admin_target(target) and not _is_super_admin(actor):
        raise HTTPException(status_code=403, detail="SUPER_ADMIN_PROTECTED")


async def _ensure_not_last_super_admin_demotion(target: dict, new_role: str):
    """Preserve the last active platform super_admin during role changes."""
    if _is_super_admin_target(target) and new_role != "super_admin":
        active = await _count_active_super_admins()
        target_active = (target.get("status") or "active").lower() not in ("disabled", "inactive", "suspended")
        if target_active and active <= 1:
            raise HTTPException(status_code=400, detail="CANNOT_MODIFY_LAST_SUPER_ADMIN")


@extra_api.put("/admin/users/{target_id}")
async def admin_update_user(target_id: str, body: UserUpdateBody, user: dict = Depends(require_permission("users.edit"))):
    target = await db.users.find_one({"id": target_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _protect_super_admin_target(user, target)
    updates = {}
    for f in ("name", "email", "phone", "notes"):
        v = getattr(body, f)
        if v is not None:
            updates[f] = v.lower().strip() if f == "email" else v
    if body.admin_role_key is not None and target.get("role") == "admin":
        if body.admin_role_key == "super_admin" and not _is_super_admin(user):
            raise HTTPException(status_code=403, detail="PLATFORM_ADMIN_ROLE_REQUIRED")
        await _ensure_not_last_super_admin_demotion(target, body.admin_role_key)
        updates["admin_role_key"] = body.admin_role_key
    if not updates:
        raise HTTPException(status_code=400, detail="No changes provided")
    await db.users.update_one({"id": target_id}, {"$set": {**updates, "updated_at": now_iso()}})
    await audit(user, "user_updated", "user", target_id,
                old={k: target.get(k) for k in updates}, new=updates)
    return await db.users.find_one({"id": target_id}, {"_id": 0, "password_hash": 0})


@extra_api.post("/admin/users/{target_id}/status")
async def admin_set_status(target_id: str, body: StatusBody, user: dict = Depends(require_permission("users.suspend"))):
    if target_id == user["id"]:
        raise HTTPException(status_code=400, detail="CANNOT_DISABLE_SELF")
    target = await db.users.find_one({"id": target_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _protect_super_admin_target(user, target)
    new_status = "disabled" if body.status.lower() in ("disabled", "inactive", "suspended") else "active"
    if _is_super_admin_target(target) and new_status == "disabled":
        active = await _count_active_super_admins()
        target_active = (target.get("status") or "active").lower() not in ("disabled", "inactive", "suspended")
        if target_active and active <= 1:
            raise HTTPException(status_code=400, detail="CANNOT_SUSPEND_LAST_SUPER_ADMIN")
    await db.users.update_one({"id": target_id}, {"$set": {"status": new_status, "updated_at": now_iso()}})
    await audit(user, "user_disabled" if new_status == "disabled" else "user_enabled",
                "user", target_id, old=target.get("status", "active"), new=new_status)
    return {"id": target_id, "status": new_status}


@extra_api.post("/admin/users/{target_id}/reset-password")
async def admin_reset_password(target_id: str, body: ResetPwBody, user: dict = Depends(require_permission("users.edit"))):
    target = await db.users.find_one({"id": target_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _protect_super_admin_target(user, target)
    if target.get("role") != "admin":
        raise HTTPException(status_code=400, detail="PASSWORD_ONLY_FOR_ADMIN")
    if len(body.password or "") < 6:
        raise HTTPException(status_code=400, detail="PASSWORD_TOO_SHORT")
    await db.users.update_one({"id": target_id}, {"$set": {"password_hash": hash_password(body.password), "updated_at": now_iso()}})
    await audit(user, "password_reset", "user", target_id)
    return {"success": True}


# ================= SUSPEND / ACTIVATE (Phase 4) =================
class SuspendBody(BaseModel):
    reason: Optional[str] = ""


async def _count_active_super_admins() -> int:
    """Count admins with admin_role_key=super_admin that are not currently suspended/disabled."""
    cur = db.users.find(
        {"role": "admin", "admin_role_key": "super_admin"},
        {"_id": 0, "id": 1, "status": 1},
    )
    n = 0
    async for u in cur:
        st = (u.get("status") or "active").lower()
        if st not in ("disabled", "inactive", "suspended"):
            n += 1
    return n


@extra_api.post("/admin/users/{target_id}/suspend")
async def suspend_user(target_id: str, body: SuspendBody, user: dict = Depends(require_permission("users.suspend"))):
    """Suspend any user (customer/driver/provider/admin). Blocks future authentication."""
    if target_id == user["id"]:
        raise HTTPException(status_code=400, detail="CANNOT_SUSPEND_SELF")
    target = await db.users.find_one({"id": target_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _protect_super_admin_target(user, target)
    # Protect the last active Super Admin
    if target.get("role") == "admin" and target.get("admin_role_key") == "super_admin":
        active = await _count_active_super_admins()
        # If this super_admin is currently active, suspending them would drop the count by one
        target_active = (target.get("status") or "active").lower() not in ("disabled", "inactive", "suspended")
        if target_active and active <= 1:
            raise HTTPException(status_code=400, detail="CANNOT_SUSPEND_LAST_SUPER_ADMIN")

    reason = (body.reason or "").strip()
    history_entry = {
        "id": uid(), "action": "SUSPENDED", "reason": reason,
        "by_id": user["id"], "by_name": user.get("name", ""),
        "at": now_iso(),
    }
    updates = {
        "status": "suspended",
        "suspension_reason": reason,
        "suspended_by": user.get("name", ""),
        "suspended_by_id": user["id"],
        "suspended_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.users.update_one(
        {"id": target_id},
        {"$set": updates, "$push": {"suspension_history": history_entry}},
    )
    await db.audit_logs.insert_one({
        "id": uid(), "admin_id": user["id"], "admin_name": user.get("name", ""),
        "actor_id": user["id"], "actor_name": user.get("name", ""), "actor_role": user.get("admin_role_key", "admin"),
        "action": "USER_SUSPENDED", "entity": "user", "entity_id": target_id,
        "old_value": {"status": target.get("status", "active")},
        "new_value": {"status": "suspended", "target_role": target.get("role"),
                      "target_name": target.get("name"), "reason": reason},
        "reason": reason, "result": "success", "timestamp": now_iso(),
    })
    ta, te = ("تم إيقاف حسابك", "Your account has been suspended")
    await notify(target_id, "account", ta, te, reason, reason,
                 entity_type="user", entity_id=target_id)
    return {"id": target_id, "status": "suspended", "reason": reason}


@extra_api.post("/admin/users/{target_id}/activate")
async def activate_user(target_id: str, user: dict = Depends(require_permission("users.suspend"))):
    """Reactivate a previously suspended (or legacy-disabled) user. Preserves suspension_history."""
    target = await db.users.find_one({"id": target_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _protect_super_admin_target(user, target)
    old_status = target.get("status", "active")
    history_entry = {
        "id": uid(), "action": "ACTIVATED", "reason": "",
        "by_id": user["id"], "by_name": user.get("name", ""),
        "at": now_iso(),
    }
    await db.users.update_one(
        {"id": target_id},
        {
            "$set": {
                "status": "active",
                "activated_by": user.get("name", ""),
                "activated_by_id": user["id"],
                "activated_at": now_iso(),
                "updated_at": now_iso(),
            },
            "$push": {"suspension_history": history_entry},
        },
    )
    await db.audit_logs.insert_one({
        "id": uid(), "admin_id": user["id"], "admin_name": user.get("name", ""),
        "actor_id": user["id"], "actor_name": user.get("name", ""), "actor_role": user.get("admin_role_key", "admin"),
        "action": "USER_ACTIVATED", "entity": "user", "entity_id": target_id,
        "old_value": {"status": old_status},
        "new_value": {"status": "active", "target_role": target.get("role"),
                      "target_name": target.get("name")},
        "reason": "", "result": "success", "timestamp": now_iso(),
    })
    ta, te = ("تم تفعيل حسابك", "Your account has been reactivated")
    await notify(target_id, "account", ta, te, "", "",
                 entity_type="user", entity_id=target_id)
    return {"id": target_id, "status": "active"}


@extra_api.get("/admin/users/{target_id}/suspension-history")
async def suspension_history(target_id: str, user: dict = Depends(require_permission("users.view"))):
    u = await db.users.find_one({"id": target_id}, {"_id": 0, "password_hash": 0})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": target_id,
        "status": u.get("status", "active"),
        "suspension_reason": u.get("suspension_reason", ""),
        "suspended_by": u.get("suspended_by", ""),
        "suspended_at": u.get("suspended_at"),
        "activated_by": u.get("activated_by", ""),
        "activated_at": u.get("activated_at"),
        "history": u.get("suspension_history", []),
    }


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


class RefundBody(BaseModel):
    account_id: str
    account_role: str = "customer"
    amount: float
    reason: str
    shipment_id: Optional[str] = None
    trip_id: Optional[str] = None
    description: Optional[str] = ""


class ReverseBody(BaseModel):
    reason: str


async def get_settings():
    s = await db.settings.find_one({"id": "platform"})
    if not s:
        s = {"id": "platform", "commission_type": "percentage", "commission_value": 10,
             "currency": "OMR", "auto_complete_hours": 48}
        await db.settings.insert_one(dict(s))
    if "auto_complete_hours" not in s:
        # Backward-compat: older settings docs get the default lazily.
        await db.settings.update_one({"id": "platform"}, {"$set": {"auto_complete_hours": 48}})
        s["auto_complete_hours"] = 48
    s.pop("_id", None)
    return s


async def record_trip_completion(trip: dict):
    """Create the immutable completion ledger exactly once.

    DISPUTED is a hard financial boundary: a disputed trip may remain HELD, but
    it must never create customer_payment, platform_commission, or driver_earning
    transactions even if an alternate caller reaches this helper.
    """
    if (trip.get("status") or "").upper() == "DISPUTED":
        return
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
        "adjustments": round(total("adjustment") + total("reversal"), 3),
        "payouts": total("payout"),
        "transaction_count": len(txns),
    }


@extra_api.get("/admin/finance/transactions")
async def list_transactions(type: Optional[str] = None, status: Optional[str] = None,
                            account_role: Optional[str] = None, account_id: Optional[str] = None,
                            date_from: Optional[str] = None, date_to: Optional[str] = None,
                            q: Optional[str] = None,
                            user: dict = Depends(require_permission("finance.transactions"))):
    query = {}
    if type:
        query["type"] = type
    if status:
        query["status"] = status
    if account_role:
        query["account_role"] = account_role
    if account_id:
        query["account_id"] = account_id
    if date_from or date_to:
        rng = {}
        if date_from:
            rng["$gte"] = date_from
        if date_to:
            rng["$lte"] = date_to + "T23:59:59"
        query["created_at"] = rng
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
                    "adjustments": {"$sum": {"$cond": [{"$in": ["$type", ["adjustment", "reversal"]]}, "$amount", 0]}},
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


@extra_api.post("/admin/finance/refund")
async def create_refund(body: RefundBody, user: dict = Depends(require_permission("finance.refund"))):
    s = await get_settings()
    amt = abs(float(body.amount))
    txn = {"id": uid(), "type": "refund", "account_id": body.account_id, "account_role": body.account_role,
           "shipment_id": body.shipment_id, "trip_id": body.trip_id, "amount": amt, "gross": amt,
           "commission": 0, "net": amt, "currency": s["currency"], "status": "COMPLETED",
           "description": body.description or "Refund", "reason": body.reason,
           "created_by": user.get("name"), "created_by_id": user["id"], "created_at": now_iso()}
    await db.transactions.insert_one(txn)
    await audit(user, "refund_created", "transaction", txn["id"], new=amt, reason=body.reason)
    txn.pop("_id", None)
    return txn


@extra_api.post("/admin/finance/transactions/{txn_id}/reverse")
async def reverse_transaction(txn_id: str, body: ReverseBody, user: dict = Depends(require_permission("finance.reverse"))):
    orig = await db.transactions.find_one({"id": txn_id}, {"_id": 0})
    if not orig:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if orig.get("reversed"):
        raise HTTPException(status_code=400, detail="ALREADY_REVERSED")
    if orig.get("type") == "reversal":
        raise HTTPException(status_code=400, detail="CANNOT_REVERSE_REVERSAL")
    rev = {**orig, "id": uid(), "type": "reversal",
           "amount": -float(orig.get("amount", 0) or 0),
           "gross": -float(orig.get("gross", 0) or 0),
           "commission": -float(orig.get("commission", 0) or 0),
           "net": -float(orig.get("net", 0) or 0),
           "status": "COMPLETED",
           "description": f"Reversal of {orig.get('type')} #{txn_id[:8]}",
           "reason": body.reason, "reverses_txn_id": txn_id,
           "created_by": user.get("name"), "created_by_id": user["id"], "created_at": now_iso()}
    rev.pop("_id", None)
    await db.transactions.insert_one(rev)
    # mark the original as reversed WITHOUT erasing its trace (amount preserved)
    await db.transactions.update_one({"id": txn_id}, {"$set": {
        "reversed": True, "reversed_by": user.get("name"), "reversed_at": now_iso(), "reversal_txn_id": rev["id"]}})
    await audit(user, "transaction_reversed", "transaction", txn_id, old=orig.get("amount"), new=rev["id"], reason=body.reason)
    rev.pop("_id", None)
    return rev


@extra_api.get("/admin/finance/account/{account_id}")
async def finance_account(account_id: str, user: dict = Depends(require_permission("finance.view"))):
    acc = await db.users.find_one({"id": account_id}, {"_id": 0, "password_hash": 0})
    txns = await db.transactions.find({"account_id": account_id}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    s = await get_settings()

    def sm(*types):
        return round(sum(float(t.get("amount", 0) or 0) for t in txns if t.get("type") in types), 3)

    role = (acc or {}).get("role", "")
    earned = sm("driver_earning", "provider_earning")
    paid = sm("customer_payment")
    payouts = sm("payout")
    refunds = sm("refund")
    adjustments = sm("adjustment", "reversal")
    commission = round(sum(float(t.get("commission", 0) or 0) for t in txns
                           if t.get("type") in ("driver_earning", "provider_earning")), 3)
    if role == "customer":
        balance = round(paid - refunds + adjustments, 3)
    else:
        balance = round(earned + adjustments - payouts - refunds, 3)
    return {"account_id": account_id, "user": acc, "currency": s["currency"],
            "totals": {"earned": earned, "paid": paid, "payouts": payouts, "refunds": refunds,
                       "adjustments": adjustments, "commission": commission, "balance": balance},
            "transactions": txns}


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



# ================= COMPANY / PROVIDER PORTAL =================
from models import VehicleBody, VehicleAssignBody, ProviderLinkDriverBody, ProviderBidBody  # noqa: E402


def _provider_only(user: dict):
    if user.get("role") != "provider":
        raise HTTPException(status_code=403, detail="PROVIDER_ONLY")


async def _get_company_driver(provider_id: str, driver_id: str) -> Optional[dict]:
    return await db.users.find_one(
        {"id": driver_id, "role": "driver", "company_id": provider_id},
        {"_id": 0, "password_hash": 0},
    )


# ---- Vehicles ----
@extra_api.get("/provider/vehicles")
async def list_vehicles(user: dict = Depends(get_current_user)):
    _provider_only(user)
    docs = await db.vehicles.find({"owner_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    driver_ids = [d.get("assigned_driver_id") for d in docs if d.get("assigned_driver_id")]
    drivers = {}
    if driver_ids:
        cur = db.users.find({"id": {"$in": driver_ids}}, {"_id": 0, "id": 1, "name": 1, "phone": 1})
        for d in await cur.to_list(500):
            drivers[d["id"]] = d
    for v in docs:
        did = v.get("assigned_driver_id")
        v["assigned_driver"] = drivers.get(did) if did else None
    return docs


@extra_api.get("/provider/vehicles/{vid}")
async def get_vehicle(vid: str, user: dict = Depends(get_current_user)):
    _provider_only(user)
    v = await db.vehicles.find_one({"id": vid, "owner_id": user["id"]}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if v.get("assigned_driver_id"):
        drv = await db.users.find_one(
            {"id": v["assigned_driver_id"]}, {"_id": 0, "id": 1, "name": 1, "phone": 1}
        )
        v["assigned_driver"] = drv
    return v


@extra_api.post("/provider/vehicles")
async def create_vehicle(body: VehicleBody, user: dict = Depends(get_current_user)):
    _provider_only(user)
    plate = (body.plate_number or "").strip()
    if not plate:
        raise HTTPException(status_code=400, detail="PLATE_REQUIRED")
    dup = await db.vehicles.find_one({"owner_id": user["id"], "plate_number": plate})
    if dup:
        raise HTTPException(status_code=400, detail="PLATE_DUPLICATE")
    if body.assigned_driver_id:
        drv = await _get_company_driver(user["id"], body.assigned_driver_id)
        if not drv:
            raise HTTPException(status_code=400, detail="DRIVER_NOT_IN_COMPANY")
    doc = {
        "id": uid(), "owner_id": user["id"], "plate_number": plate,
        "vehicle_type": body.vehicle_type or "", "make": body.make or "",
        "model": body.model or "", "year": body.year or "", "color": body.color or "",
        "capacity": body.capacity or "", "notes": body.notes or "",
        "status": (body.status or "ACTIVE").upper(),
        "assigned_driver_id": body.assigned_driver_id,
        "regulatory": _normalize_vehicle_regulatory(body.regulatory, None),
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.vehicles.insert_one(doc)
    doc.pop("_id", None)
    return doc


@extra_api.put("/provider/vehicles/{vid}")
async def update_vehicle(vid: str, body: VehicleBody, user: dict = Depends(get_current_user)):
    _provider_only(user)
    v = await db.vehicles.find_one({"id": vid, "owner_id": user["id"]})
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    plate = (body.plate_number or "").strip()
    if not plate:
        raise HTTPException(status_code=400, detail="PLATE_REQUIRED")
    if plate != v.get("plate_number"):
        dup = await db.vehicles.find_one({"owner_id": user["id"], "plate_number": plate, "id": {"$ne": vid}})
        if dup:
            raise HTTPException(status_code=400, detail="PLATE_DUPLICATE")
    if body.assigned_driver_id:
        drv = await _get_company_driver(user["id"], body.assigned_driver_id)
        if not drv:
            raise HTTPException(status_code=400, detail="DRIVER_NOT_IN_COMPANY")
    updates = {
        "plate_number": plate,
        "vehicle_type": body.vehicle_type or "", "make": body.make or "",
        "model": body.model or "", "year": body.year or "", "color": body.color or "",
        "capacity": body.capacity or "", "notes": body.notes or "",
        "status": (body.status or "ACTIVE").upper(),
        "assigned_driver_id": body.assigned_driver_id,
        "updated_at": now_iso(),
    }
    # Only touch regulatory data when the client actually sends it, so partial
    # updates from older clients never wipe existing regulatory readiness fields.
    if body.regulatory is not None:
        updates["regulatory"] = _normalize_vehicle_regulatory(body.regulatory, v.get("regulatory"))
    await db.vehicles.update_one({"id": vid}, {"$set": updates})
    return await db.vehicles.find_one({"id": vid}, {"_id": 0})


@extra_api.delete("/provider/vehicles/{vid}")
async def delete_vehicle(vid: str, user: dict = Depends(get_current_user)):
    _provider_only(user)
    v = await db.vehicles.find_one({"id": vid, "owner_id": user["id"]})
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    await db.vehicles.delete_one({"id": vid})
    return {"success": True}


@extra_api.post("/provider/vehicles/{vid}/assign")
async def assign_vehicle_driver(vid: str, body: VehicleAssignBody, user: dict = Depends(get_current_user)):
    _provider_only(user)
    v = await db.vehicles.find_one({"id": vid, "owner_id": user["id"]})
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    driver_id = body.driver_id or None
    if driver_id:
        drv = await _get_company_driver(user["id"], driver_id)
        if not drv:
            raise HTTPException(status_code=400, detail="DRIVER_NOT_IN_COMPANY")
    await db.vehicles.update_one({"id": vid}, {"$set": {
        "assigned_driver_id": driver_id, "updated_at": now_iso()}})
    return {"success": True, "assigned_driver_id": driver_id}


# ---- Company drivers ----
@extra_api.get("/provider/drivers")
async def list_company_drivers(user: dict = Depends(get_current_user)):
    _provider_only(user)
    drivers = await db.users.find(
        {"role": "driver", "company_id": user["id"]},
        {"_id": 0, "password_hash": 0},
    ).sort("created_at", -1).to_list(500)
    # Attach current active trip and vehicle summary
    active_states = {"DRIVER_ASSIGNED", "PICKUP_ARRIVED", "PICKED_UP", "IN_TRANSIT",
                     "DRIVER_ARRIVED_DESTINATION", "DELIVERED_PENDING_CONFIRMATION"}
    for d in drivers:
        trip = await db.trips.find_one(
            {"driver_id": d["id"], "status": {"$in": list(active_states)}},
            {"_id": 0, "id": 1, "status": 1, "shipment_title": 1},
        )
        d["active_trip"] = trip
        veh = await db.vehicles.find_one(
            {"owner_id": user["id"], "assigned_driver_id": d["id"]},
            {"_id": 0, "id": 1, "plate_number": 1, "vehicle_type": 1},
        )
        d["current_vehicle"] = veh
    return drivers


@extra_api.get("/provider/drivers/{driver_id}")
async def get_company_driver(driver_id: str, user: dict = Depends(get_current_user)):
    _provider_only(user)
    d = await _get_company_driver(user["id"], driver_id)
    if not d:
        raise HTTPException(status_code=404, detail="Driver not found")
    d["documents"] = await db.documents.find({"owner_id": driver_id}, {"_id": 0}).to_list(200)
    d["current_vehicle"] = await db.vehicles.find_one(
        {"owner_id": user["id"], "assigned_driver_id": driver_id}, {"_id": 0}
    )
    d["trips"] = await db.trips.find(
        {"driver_id": driver_id, "provider_id": user["id"]},
        {"_id": 0},
    ).sort("created_at", -1).to_list(100)
    return d


@extra_api.post("/provider/drivers/link")
async def link_driver_to_company(body: ProviderLinkDriverBody, user: dict = Depends(get_current_user)):
    _provider_only(user)
    phone = (body.phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="PHONE_REQUIRED")
    drv = await db.users.find_one({"role": "driver", "phone": phone}, {"_id": 0, "password_hash": 0})
    if not drv:
        raise HTTPException(status_code=404, detail="DRIVER_NOT_FOUND")
    existing_company = drv.get("company_id")
    if existing_company and existing_company != user["id"]:
        raise HTTPException(status_code=400, detail="DRIVER_IN_OTHER_COMPANY")
    if drv.get("verification_status") != "APPROVED":
        raise HTTPException(status_code=400, detail="DRIVER_NOT_APPROVED")
    await db.users.update_one({"id": drv["id"]}, {"$set": {"company_id": user["id"], "updated_at": now_iso()}})
    return {"success": True, "driver_id": drv["id"], "name": drv.get("name"), "phone": drv.get("phone")}


@extra_api.delete("/provider/drivers/{driver_id}")
async def unlink_driver(driver_id: str, user: dict = Depends(get_current_user)):
    _provider_only(user)
    d = await _get_company_driver(user["id"], driver_id)
    if not d:
        raise HTTPException(status_code=404, detail="Driver not found")
    # unassign from any vehicle first
    await db.vehicles.update_many(
        {"owner_id": user["id"], "assigned_driver_id": driver_id},
        {"$set": {"assigned_driver_id": None, "updated_at": now_iso()}},
    )
    await db.users.update_one({"id": driver_id}, {"$unset": {"company_id": ""}, "$set": {"updated_at": now_iso()}})
    return {"success": True}


# ---- Provider trips ----
@extra_api.get("/provider/trips")
async def list_provider_trips(user: dict = Depends(get_current_user)):
    _provider_only(user)
    trips = await db.trips.find({"provider_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return trips


# ---- Provider bidding (on behalf of a company driver) ----
@extra_api.post("/provider/shipments/{sid}/bids")
async def provider_submit_bid(sid: str, body: ProviderBidBody, user: dict = Depends(get_current_user)):
    _provider_only(user)
    if body.price is None or body.price <= 0:
        raise HTTPException(status_code=400, detail="INVALID_PRICE")
    drv = await _get_company_driver(user["id"], body.driver_id)
    if not drv:
        raise HTTPException(status_code=400, detail="DRIVER_NOT_IN_COMPANY")
    if drv.get("verification_status") != "APPROVED":
        raise HTTPException(status_code=400, detail="DRIVER_NOT_APPROVED")
    if (drv.get("status") or "active").lower() in ("inactive", "suspended", "disabled"):
        raise HTTPException(status_code=400, detail="DRIVER_INACTIVE")
    # Regulatory eligibility gate: provider (carrier license) + driver (app training) + app license.
    from compliance import check_provider_eligibility, check_driver_eligibility, log_eligibility_blocked
    pe = await check_provider_eligibility(user)
    de = await check_driver_eligibility(drv)
    seen = set()
    reasons = [r for r in (pe["reasons"] + de["reasons"]) if not (r["code"] in seen or seen.add(r["code"]))]
    if reasons:
        await log_eligibility_blocked(user, "shipment", sid, {"eligible": False, "reasons": reasons})
        raise HTTPException(status_code=403, detail={"code": "NOT_ELIGIBLE", "reasons": reasons})
    s = await db.shipments.find_one({"id": sid})
    if not s or s.get("status") not in ("PUBLISHED", "BIDDING"):
        raise HTTPException(status_code=400, detail="Shipment not open for bids")
    # customer_max_offer is the customer's TARGET/budget price, not a cap. Providers
    # may bid below/equal/above it; the customer decides. No max-offer rejection here.
    if existing:
        raise HTTPException(status_code=400, detail="ALREADY_BID")
    bid = {
        "id": uid(), "shipment_id": sid, "driver_id": drv["id"], "driver_name": drv.get("name", ""),
        "provider_id": user["id"], "price": float(body.price), "note": body.note or "",
        "status": "PENDING", "driver_rating": drv.get("rating", 0),
        "driver_rating_count": drv.get("rating_count", 0),
        "driver_completed_trips": drv.get("completed_trips", 0),
        "driver_vehicle": drv.get("vehicle", {}),
        "driver_verification": drv.get("verification_status"),
        "submitted_by_role": "provider",
        "created_at": now_iso(), "updated_at": now_iso(),
    }
    await db.bids.insert_one(bid)
    if s["status"] == "PUBLISHED":
        await db.shipments.update_one({"id": sid}, {"$set": {"status": "BIDDING", "updated_at": now_iso()}})
    # notify customer using existing notifications collection
    await notify(
        s["customer_id"], "new_bid", "عرض جديد على شحنتك", "New bid on your shipment",
        f"عرض بقيمة {body.price} ر.ع على «{s['title']}»",
        f"A bid of OMR {body.price} on \"{s['title']}\"",
        entity_type="shipment", entity_id=sid,
        meta={"shipment_id": sid, "bid_id": bid["id"]},
    )
    bid.pop("_id", None)
    return bid


# ---- Provider finance summary (uses existing transactions) ----
@extra_api.get("/provider/finance/summary")
async def provider_finance_summary(user: dict = Depends(get_current_user)):
    _provider_only(user)
    txns = await db.transactions.find(
        {"account_id": user["id"], "account_role": "provider"}, {"_id": 0}
    ).to_list(2000)
    total_earnings = 0.0
    held = 0.0
    completed = 0.0
    platform_commission = 0.0
    for t in txns:
        amt = float(t.get("amount") or 0)
        typ = t.get("type", "")
        st = (t.get("status") or "").upper()
        if typ in ("provider_earning", "driver_earning"):
            total_earnings += amt
            if st in ("HELD", "PENDING"):
                held += amt
            elif st in ("COMPLETED", "SETTLED", "PAID"):
                completed += amt
        if typ == "platform_commission":
            platform_commission += amt
    return {
        "total_earnings": total_earnings,
        "held": held,
        "completed": completed,
        "platform_commission": platform_commission,
        "net_earnings": total_earnings - platform_commission,
        "transactions_count": len(txns),
    }


# ================= GEOCODING PROXY (OSM Nominatim, server-side) =================
# MapPicker previously called nominatim.openstreetmap.org directly from the browser.
# Browser-side calls were being blocked/failing for some clients (CORS/referer/UA
# policy + network-level blocks), which broke Search and Reverse Geocoding.
# These endpoints proxy the SAME free OSM Nominatim service server-side with a
# compliant User-Agent. No new paid service, no API keys, no new provider.
NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
GEO_UA = {"User-Agent": "CARGO-logistics-app/1.0 (contact: admin@cargo.om)", "Accept": "application/json"}


@extra_api.get("/geo/search")
async def geo_search(q: str, lang: Optional[str] = "ar", user: dict = Depends(get_current_user)):
    q = (q or "").strip()
    if not q:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=GEO_UA) as client:
            r = await client.get(f"{NOMINATIM_BASE}/search", params={
                "format": "jsonv2", "addressdetails": 1, "countrycodes": "om",
                "limit": 6, "accept-language": lang or "ar", "q": q,
            })
            r.raise_for_status()
            data = r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="GEO_SEARCH_UNAVAILABLE")
    if not isinstance(data, list):
        return []
    # pass through only fields the UI needs
    return [{"lat": d.get("lat"), "lon": d.get("lon"), "display_name": d.get("display_name", ""),
             "address": d.get("address", {})} for d in data]


@extra_api.get("/geo/reverse")
async def geo_reverse(lat: float, lng: float, lang: Optional[str] = "ar", user: dict = Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=GEO_UA) as client:
            r = await client.get(f"{NOMINATIM_BASE}/reverse", params={
                "format": "jsonv2", "addressdetails": 1, "zoom": 18,
                "lat": lat, "lon": lng, "accept-language": lang or "ar",
            })
            r.raise_for_status()
            data = r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="GEO_REVERSE_UNAVAILABLE")
    if not data or data.get("error"):
        raise HTTPException(status_code=404, detail="GEO_REVERSE_EMPTY")
    return {"display_name": data.get("display_name", ""), "address": data.get("address", {})}



# ================= DISPUTE RESOLUTION (Financial Resolution Core — service layer) =================
class DisputeResolveBody(BaseModel):
    outcome: str  # RELEASE_TO_DRIVER | FULL_REFUND
    reason: str


ALLOWED_DISPUTE_OUTCOMES = {"RELEASE_TO_DRIVER", "FULL_REFUND"}

# Payment-hold (escrow) lifecycle. The original payment_hold ledger row is NEVER
# deleted or replaced — only its current status transitions, preserving history:
#   HELD -> RELEASED  (dispute resolved in the driver's/provider's favor)
#   HELD -> REFUNDED  (dispute resolved as a full refund to the customer)
HOLD_STATUS_HELD = "HELD"
HOLD_STATUS_RELEASED = "RELEASED"
HOLD_STATUS_REFUNDED = "REFUNDED"


async def _notify_all_admins(type_, title_ar, title_en, body_ar, body_en, meta=None):
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(200)
    for a in admins:
        await notify(a["id"], type_, title_ar, title_en, body_ar, body_en, meta=meta)


async def _finalize_payment_hold(trip_id: str, new_status: str, actor: dict, now: str,
                                 outcome: str, extra: Optional[dict] = None) -> Optional[dict]:
    """Transition the trip's payment_hold ledger row HELD -> RELEASED|REFUNDED.

    The original row is preserved for audit/history; only its status and
    resolution-linkage fields change. The conditional filter on status=HELD makes
    the transition safe under retries (a second call is a no-op). Returns the hold
    document as it was BEFORE the transition, or None when the trip has no hold.
    """
    hold = await db.transactions.find_one({"trip_id": trip_id, "type": "payment_hold"}, {"_id": 0})
    if not hold:
        return None
    updates = {
        "status": new_status,
        "resolution_outcome": outcome,
        "resolved_at": now,
        "resolved_by_id": actor["id"],
        "resolved_by_name": actor.get("name", ""),
    }
    if extra:
        updates.update(extra)
    await db.transactions.update_one({"id": hold["id"], "status": HOLD_STATUS_HELD}, {"$set": updates})
    return hold


@extra_api.get("/admin/disputes")
async def list_disputes(status: Optional[str] = None,
                        user: dict = Depends(require_permission("disputes.view"))):
    """List trips currently in DISPUTED plus resolved disputes. Filter by status
    when the UI needs open/resolved sections."""
    query = {"dispute": {"$exists": True}}
    trips = await db.trips.find(query, {"_id": 0}).sort("updated_at", -1).to_list(500)
    out = []
    for tr in trips:
        d = tr.get("dispute") or {}
        state = "OPEN" if tr.get("status") == "DISPUTED" else "RESOLVED"
        if status and status.upper() != state:
            continue
        out.append({
            "trip_id": tr["id"], "shipment_id": tr.get("shipment_id"),
            "shipment_title": tr.get("shipment_title"),
            "trip_status": tr.get("status"), "payment_status": tr.get("payment_status"),
            "customer_id": tr.get("customer_id"), "customer_name": tr.get("customer_name"),
            "driver_id": tr.get("driver_id"), "driver_name": tr.get("driver_name"),
            "provider_id": tr.get("provider_id"),
            "amount": tr.get("price"),
            "opened_at": d.get("opened_at"), "reason": d.get("reason"),
            "state": state, "outcome": d.get("outcome"),
            "resolved_by_name": d.get("resolved_by_name"), "resolved_at": d.get("resolved_at"),
        })
    return out


@extra_api.get("/admin/disputes/{trip_id}")
async def dispute_detail(trip_id: str, user: dict = Depends(require_permission("disputes.view"))):
    tr = await db.trips.find_one({"id": trip_id}, {"_id": 0})
    if not tr or not tr.get("dispute"):
        raise HTTPException(status_code=404, detail="Dispute not found")
    shipment = await db.shipments.find_one({"id": tr.get("shipment_id")}, {"_id": 0})
    hold = await db.transactions.find_one(
        {"trip_id": trip_id, "type": "payment_hold"}, {"_id": 0}
    )
    txns = await db.transactions.find({"trip_id": trip_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return {"trip": tr, "shipment": shipment, "payment_hold": hold, "transactions": txns}


async def execute_dispute_resolution(trip_id: str, outcome: str, reason: str, actor: dict) -> dict:
    """Financial Resolution Core — route-agnostic service layer.

    Owns the complete state + ledger transition for resolving a disputed trip so
    the HTTP layer stays a thin adapter and this logic can later be extracted
    (or re-implemented in Go/Node/Java) without touching routes or UI.

    Outcomes:
      RELEASE_TO_DRIVER: trip DISPUTED -> COMPLETED, shipment -> COMPLETED,
        payment_hold HELD -> RELEASED, trip.payment_status -> RELEASED, then the
        existing settlement ledger (customer_payment + platform_commission +
        driver/provider_earning) is created exactly once via record_trip_completion().
      FULL_REFUND: trip DISPUTED -> REFUNDED, shipment -> REFUNDED,
        payment_hold HELD -> REFUNDED, trip.payment_status -> REFUNDED, and exactly
        one refund transaction is created. No driver/provider earning and no
        platform commission are created for the refunded amount.

    Idempotency & conflicts:
      * Any second resolve call — same OR different outcome — finds the trip no
        longer DISPUTED (or dispute.status == RESOLVED) and raises 409
        ALREADY_RESOLVED. The first decision is never modified.
      * The atomic claim filter guarantees a single winner under concurrency.
      * The payment_hold row is preserved (status transition only); refund
        creation is guarded by an existing-refund check.
    """
    outcome = (outcome or "").upper()
    if outcome not in ALLOWED_DISPUTE_OUTCOMES:
        raise HTTPException(status_code=400, detail="INVALID_DISPUTE_OUTCOME")
    if not (reason or "").strip():
        raise HTTPException(status_code=400, detail="DISPUTE_REASON_REQUIRED")

    tr = await db.trips.find_one({"id": trip_id})
    if not tr or not tr.get("dispute"):
        raise HTTPException(status_code=404, detail="Dispute not found")
    if tr.get("status") != "DISPUTED" or (tr.get("dispute") or {}).get("status") == "RESOLVED":
        # Already resolved (either outcome) or moved out of DISPUTED — reject
        # without touching the previous decision or its ledger effects.
        raise HTTPException(status_code=409, detail="ALREADY_RESOLVED")

    now = now_iso()
    amount = float(tr.get("price", 0) or 0)
    old_payment_status = tr.get("payment_status") or "NONE"
    resolved_payload = {
        "status": "RESOLVED", "outcome": outcome, "resolution_reason": reason,
        "resolved_by_id": actor["id"], "resolved_by_name": actor.get("name", ""),
        "resolved_at": now,
    }
    dispute_id = (tr.get("dispute") or {}).get("opened_at")  # one dispute per trip; opened_at identifies it
    base_audit = {
        "id": uid(), "admin_id": actor["id"], "admin_name": actor.get("name", ""),
        "actor_id": actor["id"], "actor_name": actor.get("name", ""), "actor_role": "admin",
        "entity": "trip", "entity_id": trip_id, "reason": reason,
        "result": "success", "timestamp": now,
    }

    if outcome == "RELEASE_TO_DRIVER":
        # Atomic claim DISPUTED -> COMPLETED. The compound filter guarantees only
        # the first concurrent request wins; any duplicate request will fail the
        # filter and see modified_count == 0.
        claimed = await db.trips.update_one(
            {"id": trip_id, "status": "DISPUTED", "dispute.status": {"$ne": "RESOLVED"}},
            {"$set": {
                "status": "COMPLETED", "customer_confirmed": True,
                "payment_status": HOLD_STATUS_RELEASED,
                "dispute": {**tr["dispute"], **resolved_payload},
                "delivered_at": tr.get("delivered_at") or now,
                "completed_at": now, "updated_at": now,
            }},
        )
        if claimed.modified_count != 1:
            raise HTTPException(status_code=409, detail="ALREADY_RESOLVED")
        await db.shipments.update_one({"id": tr["shipment_id"]}, {"$set": {"status": "COMPLETED", "updated_at": now}})

        # Escrow release: original payment_hold row preserved, status -> RELEASED.
        hold_before = await _finalize_payment_hold(trip_id, HOLD_STATUS_RELEASED, actor, now, outcome)

        # Reuse the existing settlement helper — it short-circuits if the earning
        # already exists, so duplicate calls can never create duplicate ledger rows.
        # Provider trips automatically produce provider_earning (existing logic).
        fresh = await db.trips.find_one({"id": trip_id}, {"_id": 0})
        await record_trip_completion(fresh)

        await db.audit_logs.insert_one({
            **base_audit,
            "action": "DISPUTE_RESOLVED_RELEASE",
            "old_value": {"status": "DISPUTED", "dispute_state": "OPEN",
                          "payment_status": old_payment_status,
                          "hold_status": (hold_before or {}).get("status")},
            "new_value": {"status": "COMPLETED", "outcome": outcome, "amount": amount,
                          "payment_status": HOLD_STATUS_RELEASED, "hold_status": HOLD_STATUS_RELEASED,
                          "shipment_id": tr.get("shipment_id"), "trip_id": trip_id,
                          "dispute_id": dispute_id},
        })
        # Notify parties
        await notify(tr["driver_id"], "dispute_resolved", "تم حل النزاع لصالحك",
                     "Dispute resolved in your favor", reason, reason,
                     entity_type="trip", entity_id=trip_id)
        await notify(tr["customer_id"], "dispute_resolved", "تم حل النزاع",
                     "Dispute resolved", reason, reason,
                     entity_type="trip", entity_id=trip_id)
        await _notify_all_admins("dispute_resolved", "تم حل نزاع", "Dispute resolved",
                                 reason, reason,
                                 meta={"trip_id": trip_id, "outcome": outcome})
        return fresh

    # ---- FULL_REFUND ----
    # Atomic claim DISPUTED -> REFUNDED.
    claimed = await db.trips.update_one(
        {"id": trip_id, "status": "DISPUTED", "dispute.status": {"$ne": "RESOLVED"}},
        {"$set": {
            "status": "REFUNDED",
            "payment_status": HOLD_STATUS_REFUNDED,
            "dispute": {**tr["dispute"], **resolved_payload},
            "refunded_at": now, "updated_at": now,
        }},
    )
    if claimed.modified_count != 1:
        raise HTTPException(status_code=409, detail="ALREADY_RESOLVED")
    await db.shipments.update_one({"id": tr["shipment_id"]}, {"$set": {"status": "REFUNDED", "updated_at": now}})

    # Exactly one refund transaction per trip (idempotent under retries).
    # No driver/provider earning and no platform commission are created here.
    s = await get_settings()
    existing_refund = await db.transactions.find_one({"trip_id": trip_id, "type": "refund"})
    refund_txn_id = (existing_refund or {}).get("id")
    if not existing_refund:
        refund_txn_id = uid()
        await db.transactions.insert_one({
            "id": refund_txn_id, "type": "refund",
            "account_id": tr["customer_id"], "account_role": "customer",
            "shipment_id": tr.get("shipment_id"), "trip_id": trip_id,
            "amount": amount, "gross": amount, "commission": 0, "net": amount,
            "currency": s["currency"], "status": "COMPLETED",
            "description": f"Dispute full refund for {tr.get('shipment_title','')}",
            "reason": reason,
            "created_by": actor.get("name"), "created_by_id": actor["id"], "created_at": now,
        })

    # Escrow refund: original payment_hold row preserved, status -> REFUNDED,
    # linked to the refund transaction.
    hold_before = await _finalize_payment_hold(trip_id, HOLD_STATUS_REFUNDED, actor, now, outcome,
                                               {"refund_txn_id": refund_txn_id})

    await db.audit_logs.insert_one({
        **base_audit,
        "action": "DISPUTE_RESOLVED_REFUND",
        "old_value": {"status": "DISPUTED", "dispute_state": "OPEN",
                      "payment_status": old_payment_status,
                      "hold_status": (hold_before or {}).get("status")},
        "new_value": {"status": "REFUNDED", "outcome": outcome, "amount": amount,
                      "payment_status": HOLD_STATUS_REFUNDED, "hold_status": HOLD_STATUS_REFUNDED,
                      "refund_txn_id": refund_txn_id,
                      "shipment_id": tr.get("shipment_id"), "trip_id": trip_id,
                      "dispute_id": dispute_id},
    })
    await notify(tr["customer_id"], "dispute_refunded", "تم رد المبلغ بالكامل",
                 "Full refund issued", reason, reason,
                 entity_type="trip", entity_id=trip_id)
    await notify(tr["driver_id"], "dispute_resolved", "تم حل النزاع",
                 "Dispute resolved", reason, reason,
                 entity_type="trip", entity_id=trip_id)
    await _notify_all_admins("dispute_resolved", "تم حل نزاع (استرداد)", "Dispute resolved (refund)",
                             reason, reason,
                             meta={"trip_id": trip_id, "outcome": outcome})
    return await db.trips.find_one({"id": trip_id}, {"_id": 0})


@extra_api.post("/admin/disputes/{trip_id}/resolve")
async def resolve_dispute(trip_id: str, body: DisputeResolveBody,
                          user: dict = Depends(require_permission("disputes.resolve"))):
    """Thin HTTP adapter — all financial/state logic lives in execute_dispute_resolution()."""
    return await execute_dispute_resolution(trip_id, body.outcome, body.reason, user)



# ==================================================================================
# CHAT CORE
# ==================================================================================
# Design: trip-scoped conversations (one thread per trip) whose participant set is
# derived from the trip itself (customer + driver + provider if any) plus admins
# who gain access lazily when a dispute exists OR they hold the chat.access_all
# permission. Two collections:
#   * chat_conversations : id, trip_id, shipment_id, dispute_id?, participants[],
#                          last_message_*, unread_by[user_id]
#   * chat_messages       : id, conversation_id, sender_id, sender_name, sender_role,
#                          text, created_at, read_by[user_id]
# The chat_service functions below (build/authorize/list/create/mark_read) are pure
# and stateless with respect to HTTP — HTTP routes are thin adapters so a future
# Go / Node / TypeScript / Java extraction can reuse the exact same contracts and
# data shapes without touching the customer/driver/provider/admin flows.


class ChatSendBody(BaseModel):
    text: str


class ChatContextBody(BaseModel):
    trip_id: Optional[str] = None
    shipment_id: Optional[str] = None


def _chat_participant(user: dict) -> dict:
    return {"user_id": user["id"], "role": user["role"],
            "name": user.get("company_name") or user.get("name") or user["id"]}


async def _chat_build_participants_for_trip(trip: dict) -> list:
    """Derive the authoritative participant set from a trip. Names are looked up
    at conversation creation time so that later renames don't require re-writes."""
    ids = [pid for pid in [trip.get("customer_id"), trip.get("driver_id"), trip.get("provider_id")] if pid]
    users = await db.users.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "name": 1, "role": 1, "company_name": 1}).to_list(20)
    umap = {u["id"]: u for u in users}
    out = []
    for pid in ids:
        u = umap.get(pid)
        if u:
            out.append(_chat_participant(u))
    return out


async def _chat_get_or_create_for_trip(trip_id: str, actor: dict) -> dict:
    """Idempotent conversation resolver. Never creates duplicates for the same trip."""
    conv = await db.chat_conversations.find_one({"trip_id": trip_id}, {"_id": 0})
    trip = await db.trips.find_one({"id": trip_id}, {"_id": 0})
    if not trip:
        raise HTTPException(status_code=404, detail="TRIP_NOT_FOUND")
    if not await _chat_authorize_trip(actor, trip):
        raise HTTPException(status_code=403, detail="NOT_A_PARTICIPANT")
    participants = await _chat_build_participants_for_trip(trip)
    now = now_iso()
    if not conv:
        conv = {
            "id": uid(), "trip_id": trip_id, "shipment_id": trip.get("shipment_id"),
            "dispute_id": (trip.get("dispute") or {}).get("opened_at") if trip.get("dispute") else None,
            "shipment_title": trip.get("shipment_title", ""),
            "participants": participants, "created_at": now,
            "last_message_at": None, "last_message_preview": "", "last_message_sender_id": None,
            "unread_by": {},
        }
        await db.chat_conversations.insert_one(dict(conv))
        conv.pop("_id", None)
    else:
        # Keep participants / dispute link fresh without duplicating records.
        new_dispute = (trip.get("dispute") or {}).get("opened_at") if trip.get("dispute") else None
        await db.chat_conversations.update_one({"id": conv["id"]}, {"$set": {
            "participants": participants, "dispute_id": new_dispute,
            "shipment_id": trip.get("shipment_id"), "shipment_title": trip.get("shipment_title", ""),
        }})
        conv["participants"] = participants
        conv["dispute_id"] = new_dispute
    return conv


async def _chat_authorize_trip(user: dict, trip: dict) -> bool:
    """Trip-level authorization used both for creation and messaging.
    Admins get access when the trip has a dispute or when they hold chat.access_all."""
    if not trip:
        return False
    uid_ = user["id"]
    if uid_ in (trip.get("customer_id"), trip.get("driver_id"), trip.get("provider_id")):
        return True
    if user.get("role") == "admin":
        if trip.get("dispute"):
            return True
        perms = set(await get_user_permissions(user))
        if "chat.access_all" in perms or "disputes.resolve" in perms or user.get("admin_role_key") == "super_admin":
            return True
    return False


async def _chat_authorize_conversation(user: dict, conv: dict) -> bool:
    """Conversation-level authorization. The trip is the single source of truth."""
    if not conv:
        return False
    trip = await db.trips.find_one({"id": conv["trip_id"]}, {"_id": 0})
    return await _chat_authorize_trip(user, trip or {})


async def _chat_visible_conversations_for(user: dict) -> list:
    """Return the conversations the user is authorized to see, sorted by recency."""
    role = user.get("role")
    if role == "customer":
        q = {"participants.user_id": user["id"]}
    elif role == "driver":
        q = {"participants.user_id": user["id"]}
    elif role == "provider":
        q = {"participants.user_id": user["id"]}
    elif role == "admin":
        perms = set(await get_user_permissions(user))
        if "chat.access_all" in perms or user.get("admin_role_key") == "super_admin":
            q = {}
        else:
            q = {"dispute_id": {"$ne": None}}
    else:
        q = {"participants.user_id": user["id"]}
    return await db.chat_conversations.find(q, {"_id": 0}).sort("last_message_at", -1).to_list(200)


async def _chat_send_message(conv: dict, sender: dict, text: str) -> dict:
    """Append a message and update conversation cache atomically (best-effort).
    Also fires an in-app notification to every OTHER participant so the existing
    notification bell surfaces the new message without a separate transport."""
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="MESSAGE_EMPTY")
    if len(text) > 4000:
        raise HTTPException(status_code=400, detail="MESSAGE_TOO_LONG")
    now = now_iso()
    msg = {
        "id": uid(), "conversation_id": conv["id"], "sender_id": sender["id"],
        "sender_name": sender.get("company_name") or sender.get("name") or sender["id"],
        "sender_role": sender.get("role"),
        "text": text, "created_at": now,
        "trip_id": conv.get("trip_id"), "shipment_id": conv.get("shipment_id"),
        "read_by": [sender["id"]],
    }
    await db.chat_messages.insert_one(dict(msg))
    msg.pop("_id", None)
    # Update conversation cache. Increment unread counters for every other participant.
    unread_updates = {f"unread_by.{p['user_id']}": 1
                      for p in (conv.get("participants") or []) if p["user_id"] != sender["id"]}
    upd = {"$set": {
        "last_message_at": now, "last_message_preview": text[:120],
        "last_message_sender_id": sender["id"], "last_message_sender_name": msg["sender_name"],
    }}
    if unread_updates:
        upd["$inc"] = unread_updates
    await db.chat_conversations.update_one({"id": conv["id"]}, upd)
    # Fan-out notifications (reusing existing bell/count system).
    for p in (conv.get("participants") or []):
        if p["user_id"] == sender["id"]:
            continue
        preview = text if len(text) <= 80 else (text[:77] + "...")
        await notify(
            p["user_id"], "chat_message",
            f"رسالة جديدة من {msg['sender_name']}", f"New message from {msg['sender_name']}",
            preview, preview,
            entity_type="conversation", entity_id=conv["id"],
            meta={"conversation_id": conv["id"], "trip_id": conv.get("trip_id"),
                  "shipment_id": conv.get("shipment_id")},
        )
    return msg


async def _chat_mark_read(conv: dict, user: dict) -> None:
    await db.chat_conversations.update_one({"id": conv["id"]}, {"$set": {f"unread_by.{user['id']}": 0}})
    await db.chat_messages.update_many(
        {"conversation_id": conv["id"], "read_by": {"$ne": user["id"]}},
        {"$addToSet": {"read_by": user["id"]}},
    )


# ---- HTTP adapters -----------------------------------------------------------------
@extra_api.get("/chat/conversations")
async def chat_list_conversations(user: dict = Depends(get_current_user)):
    convs = await _chat_visible_conversations_for(user)
    for c in convs:
        c["unread"] = int((c.get("unread_by") or {}).get(user["id"]) or 0)
        # Peer preview for the conversation list (first non-self participant).
        peers = [p for p in (c.get("participants") or []) if p["user_id"] != user["id"]]
        c["peer_name"] = ", ".join(p["name"] for p in peers) if peers else ""
        c["peer_role"] = peers[0]["role"] if peers else ""
    return convs


@extra_api.post("/chat/conversations/context")
async def chat_context_conversation(body: ChatContextBody, user: dict = Depends(get_current_user)):
    """Resolve (or create idempotently) the conversation for a given trip or shipment.
    Shipments without a trip yet return CHAT_NOT_AVAILABLE — chat is trip-scoped."""
    trip_id = body.trip_id
    if not trip_id and body.shipment_id:
        sh = await db.shipments.find_one({"id": body.shipment_id}, {"_id": 0, "trip_id": 1, "customer_id": 1})
        if not sh:
            raise HTTPException(status_code=404, detail="SHIPMENT_NOT_FOUND")
        if not sh.get("trip_id"):
            raise HTTPException(status_code=400, detail="CHAT_NOT_AVAILABLE_BEFORE_TRIP")
        trip_id = sh["trip_id"]
    if not trip_id:
        raise HTTPException(status_code=400, detail="TRIP_OR_SHIPMENT_REQUIRED")
    return await _chat_get_or_create_for_trip(trip_id, user)


@extra_api.get("/chat/conversations/{cid}")
async def chat_get_conversation(cid: str, user: dict = Depends(get_current_user)):
    conv = await db.chat_conversations.find_one({"id": cid}, {"_id": 0})
    if not conv or not await _chat_authorize_conversation(user, conv):
        raise HTTPException(status_code=403, detail="NOT_A_PARTICIPANT")
    conv["unread"] = int((conv.get("unread_by") or {}).get(user["id"]) or 0)
    return conv


@extra_api.get("/chat/conversations/{cid}/messages")
async def chat_list_messages(cid: str, after: Optional[str] = None, limit: int = 100,
                             user: dict = Depends(get_current_user)):
    conv = await db.chat_conversations.find_one({"id": cid}, {"_id": 0})
    if not conv or not await _chat_authorize_conversation(user, conv):
        raise HTTPException(status_code=403, detail="NOT_A_PARTICIPANT")
    q = {"conversation_id": cid}
    if after:
        # Delta polling: transport-agnostic so we can swap to websockets later
        # without changing the message model or the authorization boundary.
        q["created_at"] = {"$gt": after}
    limit = max(1, min(int(limit or 100), 500))
    return await db.chat_messages.find(q, {"_id": 0}).sort("created_at", 1).to_list(limit)


@extra_api.post("/chat/conversations/{cid}/messages")
async def chat_post_message(cid: str, body: ChatSendBody, user: dict = Depends(get_current_user)):
    conv = await db.chat_conversations.find_one({"id": cid}, {"_id": 0})
    if not conv or not await _chat_authorize_conversation(user, conv):
        raise HTTPException(status_code=403, detail="NOT_A_PARTICIPANT")
    return await _chat_send_message(conv, user, body.text)


@extra_api.post("/chat/conversations/{cid}/read")
async def chat_mark_read(cid: str, user: dict = Depends(get_current_user)):
    conv = await db.chat_conversations.find_one({"id": cid}, {"_id": 0})
    if not conv or not await _chat_authorize_conversation(user, conv):
        raise HTTPException(status_code=403, detail="NOT_A_PARTICIPANT")
    await _chat_mark_read(conv, user)
    return {"success": True}



# ==================================================================================
# REGULATORY READINESS (Oman) — DATA STRUCTURE ONLY
# ==================================================================================
# Purpose: let CARGO *store* (a) the platform's Smart Transport Application license,
# (b) driver licensing data, and (c) vehicle operating-card / barcode readiness — so
# future Omani regulatory requirements can be accommodated without a rebuild.
#
# Explicitly OUT OF SCOPE here (do NOT add): eligibility/compliance engine,
# block/unblock rules, Naql API integration, real barcode issuance, SMS/GPS/payment.
# Everything below is additive and backward-compatible: missing fields default to
# empty, old records without these fields keep working, and no dummy/real license
# numbers are ever generated. Vehicle documents remain in Unified Documents (the
# `documents` collection) — these fields only hold identifiers/dates, not files.
from models import AppLicenseBody, DriverRegulatoryBody  # noqa: E402

APP_LICENSE_ID = "app_license"

DRIVER_REG_KEYS = [
    "driving_license_number", "license_class", "license_issue_date",
    "license_expiry_date", "license_status", "driver_training_status",
    "driver_training_date", "regulatory_notes",
]

VEHICLE_REG_KEYS = [
    "chassis_number", "operating_card_number", "operating_card_issue_date",
    "operating_card_expiry_date", "operating_card_status",
    "registration_reference", "ownership_reference", "regulatory_notes",
    # Regulatory identifier / barcode readiness (NOT a real government barcode).
    "regulatory_identifier", "barcode_value", "barcode_status",
]


def _normalize_vehicle_regulatory(incoming, existing) -> dict:
    """Return a dict containing exactly the known regulatory keys. Starts from the
    existing stored block (so unspecified keys are preserved) and overlays any
    provided keys. Unknown keys in `incoming` are ignored to keep the shape stable
    for future language/service extraction (stable data contract)."""
    out = {k: "" for k in VEHICLE_REG_KEYS}
    if isinstance(existing, dict):
        for k in VEHICLE_REG_KEYS:
            if existing.get(k) is not None:
                out[k] = existing.get(k)
    if isinstance(incoming, dict):
        for k in VEHICLE_REG_KEYS:
            if k in incoming and incoming.get(k) is not None:
                out[k] = incoming.get(k)
    return out


def _normalize_driver_regulatory(body: DriverRegulatoryBody) -> dict:
    data = body.model_dump()
    return {k: (data.get(k) or "") for k in DRIVER_REG_KEYS}


async def get_app_license() -> dict:
    """Lazy singleton, mirrors the get_settings() pattern. Never fabricates a real
    license number — returns an empty skeleton until an admin fills it in."""
    doc = await db.settings.find_one({"id": APP_LICENSE_ID}, {"_id": 0})
    if not doc:
        doc = {
            "id": APP_LICENSE_ID, "license_number": "", "license_type": "",
            "issuing_authority": "", "issue_date": "", "expiry_date": "",
            "status": "", "document_id": None, "notes": "",
            "created_at": now_iso(), "updated_at": now_iso(),
        }
        await db.settings.insert_one(dict(doc))
    return doc


# ---- Smart Transport Application license (platform-level) ----
@extra_api.get("/admin/app-license")
async def read_app_license(user: dict = Depends(require_permission("system.settings"))):
    return await get_app_license()


@extra_api.put("/admin/app-license")
async def update_app_license(body: AppLicenseBody,
                             user: dict = Depends(require_permission("system.settings"))):
    old = await get_app_license()
    updates = body.model_dump()
    updates["id"] = APP_LICENSE_ID
    updates["updated_at"] = now_iso()
    updates["updated_by"] = user.get("name", "")
    await db.settings.update_one({"id": APP_LICENSE_ID}, {"$set": updates}, upsert=True)
    await audit(user, "app_license_updated", "app_license", APP_LICENSE_ID,
                old={k: old.get(k) for k in updates if k in old}, new=updates)
    return await get_app_license()


# ---- Driver regulatory / licensing data (driver-owned) ----
@extra_api.get("/driver/regulatory")
async def read_driver_regulatory(user: dict = Depends(require_roles("driver"))):
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    reg = (fresh or {}).get("regulatory") or {}
    # Return a full, stable shape even for legacy drivers who never saved it.
    return {k: (reg.get(k) or "") for k in DRIVER_REG_KEYS}


@extra_api.put("/driver/regulatory")
async def update_driver_regulatory(body: DriverRegulatoryBody,
                                   user: dict = Depends(require_roles("driver"))):
    reg = _normalize_driver_regulatory(body)
    await db.users.update_one({"id": user["id"]},
                              {"$set": {"regulatory": reg, "updated_at": now_iso()}})
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return fresh
