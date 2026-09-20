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
    "finance.view", "finance.transactions", "finance.commission", "finance.payouts", "finance.adjust", "finance.refund", "finance.reverse",
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
    s = await db.shipments.find_one({"id": sid})
    if not s or s.get("status") not in ("PUBLISHED", "BIDDING"):
        raise HTTPException(status_code=400, detail="Shipment not open for bids")
    existing = await db.bids.find_one({"shipment_id": sid, "driver_id": drv["id"], "status": "PENDING"})
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
