import os
import uuid
from datetime import datetime, timezone, timedelta

from database import db
from auth import hash_password, verify_password


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return str(uuid.uuid4())


async def seed_admin():
    email = os.environ["ADMIN_EMAIL"].lower()
    password = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": email, "role": "admin"})
    if not existing:
        await db.users.insert_one({
            "id": uid(),
            "role": "admin",
            "name": "CARGO Administrator",
            "email": email,
            "password_hash": hash_password(password),
            "admin_role_key": "super_admin",
            "status": "active",
            "created_at": now_iso(),
        })
    else:
        upd = {"admin_role_key": existing.get("admin_role_key", "super_admin")}
        if not verify_password(password, existing.get("password_hash", "")):
            upd["password_hash"] = hash_password(password)
        await db.users.update_one({"id": existing["id"]}, {"$set": upd})


DEMO_DRIVERS = [
    {
        "phone": "+96890000002", "name": "خالد العامري",
        "verification_status": "APPROVED", "rating": 4.8, "rating_count": 42, "completed_trips": 58,
        "vehicle": {"type": "flatbed", "plate": "AB-1234", "capacity": "10", "model": "Isuzu FVR 2021"},
    },
    {
        "phone": "+96890000003", "name": "سعيد الحارثي",
        "verification_status": "APPROVED", "rating": 4.6, "rating_count": 30, "completed_trips": 35,
        "vehicle": {"type": "container", "plate": "CD-5678", "capacity": "20", "model": "Volvo FH 2020"},
    },
    {
        "phone": "+96890000004", "name": "يوسف الرئيسي",
        "verification_status": "PENDING", "rating": 0, "rating_count": 0, "completed_trips": 0,
        "vehicle": {"type": "pickup", "plate": "EF-9012", "capacity": "3", "model": "Toyota Hilux 2022"},
    },
]


async def seed_users():
    # Customer
    if not await db.users.find_one({"phone": "+96890000001", "role": "customer"}):
        await db.users.insert_one({
            "id": uid(), "role": "customer", "name": "أحمد البلوشي",
            "phone": "+96890000001", "email": "", "created_at": now_iso(),
        })
    # Drivers
    for d in DEMO_DRIVERS:
        if not await db.users.find_one({"phone": d["phone"], "role": "driver"}):
            docs = []
            if d["verification_status"] == "APPROVED":
                docs = [
                    {"type": "driving_license", "status": "APPROVED", "reference": "DL-" + d["phone"][-4:], "expiry": "2028-01-01", "notes": "", "submitted_at": now_iso(), "reviewed_at": now_iso()},
                    {"type": "vehicle_registration", "status": "APPROVED", "reference": "VR-" + d["phone"][-4:], "expiry": "2027-06-01", "notes": "", "submitted_at": now_iso(), "reviewed_at": now_iso()},
                    {"type": "insurance", "status": "APPROVED", "reference": "IN-" + d["phone"][-4:], "expiry": "2026-12-01", "notes": "", "submitted_at": now_iso(), "reviewed_at": now_iso()},
                ]
            elif d["verification_status"] == "PENDING":
                docs = [
                    {"type": "driving_license", "status": "PENDING", "reference": "DL-" + d["phone"][-4:], "expiry": "2028-01-01", "notes": "", "submitted_at": now_iso(), "reviewed_at": None},
                ]
            await db.users.insert_one({
                "id": uid(), "role": "driver", "name": d["name"], "phone": d["phone"], "email": "",
                "verification_status": d["verification_status"],
                "rating": d["rating"], "rating_count": d["rating_count"], "completed_trips": d["completed_trips"],
                "vehicle": d["vehicle"], "documents": docs, "created_at": now_iso(),
            })
    # Provider
    if not await db.users.find_one({"phone": "+96890000005", "role": "provider"}):
        await db.users.insert_one({
            "id": uid(), "role": "provider", "name": "فهد المعمري",
            "phone": "+96890000005", "email": "",
            "company_name": "شركة الخليج للنقل والشحن",
            "cr_number": "1234567", "service_areas": ["مسقط", "صحار", "صلالة"],
            "company_role": "COMPANY_ADMIN", "verification_status": "APPROVED",
            "created_at": now_iso(),
        })


async def seed_shipments():
    customer = await db.users.find_one({"phone": "+96890000001", "role": "customer"})
    if not customer:
        return
    if await db.shipments.find_one({"customer_id": customer["id"]}):
        return
    samples = [
        {
            "title": "نقل حاويات من ميناء صحار إلى مسقط",
            "description": "حاوية 20 قدم تحتوي على معدات صناعية",
            "category": "معدات صناعية", "quantity": "1", "weight": "8000", "dimensions": "6x2.4x2.6م",
            "pickup_location": {"address": "ميناء صحار الصناعي، صحار", "lat": 24.4833, "lng": 56.6167},
            "delivery_location": {"address": "المنطقة الصناعية بالرسيل، مسقط", "lat": 23.5333, "lng": 58.2833},
            "pickup_date": "2026-07-01", "pickup_time": "08:00",
            "delivery_date": "2026-07-01", "delivery_time": "16:00",
            "vehicle_type": "container", "required_capacity": "20",
            "loading_service": True, "unloading_service": True,
            "special_instructions": "يرجى التعامل بحذر مع المعدات",
            "expected_price": "150",
        },
        {
            "title": "توصيل مواد بناء من نزوى إلى صلالة",
            "description": "أكياس أسمنت ومواد بناء",
            "category": "مواد بناء", "quantity": "200", "weight": "10000", "dimensions": "شحنة مسطحة",
            "pickup_location": {"address": "نزوى، الداخلية", "lat": 22.9333, "lng": 57.5333},
            "delivery_location": {"address": "صلالة، ظفار", "lat": 17.0194, "lng": 54.0897},
            "pickup_date": "2026-07-03", "pickup_time": "06:00",
            "delivery_date": "2026-07-04", "delivery_time": "12:00",
            "vehicle_type": "flatbed", "required_capacity": "10",
            "loading_service": False, "unloading_service": True,
            "special_instructions": "",
            "expected_price": "300",
        },
    ]
    for s in samples:
        await db.shipments.insert_one({
            "id": uid(), "customer_id": customer["id"], "customer_name": customer["name"],
            "images": [], "status": "PUBLISHED",
            "accepted_bid_id": None, "assigned_driver_id": None, "trip_id": None,
            "created_at": now_iso(), "updated_at": now_iso(), **s,
        })


async def seed_phase11():
    # Cargo categories
    if await db.cargo_categories.count_documents({}) == 0:
        cats = [
            ("furniture", "أثاث", "Furniture", "sofa"),
            ("household", "أغراض منزلية", "Household items", "home"),
            ("electronics", "إلكترونيات", "Electronics", "smartphone"),
            ("food", "مواد غذائية", "Food", "utensils"),
            ("construction", "مواد بناء", "Construction materials", "hard-hat"),
            ("commercial", "بضائع تجارية", "Commercial goods", "shopping-bag"),
            ("machinery", "آلات ومعدات", "Machinery / Equipment", "cog"),
            ("documents", "مستندات", "Documents", "file-text"),
            ("vehicle", "مركبة", "Vehicle", "car"),
            ("other", "أخرى", "Other", "package"),
        ]
        await db.cargo_categories.insert_many([
            {"id": uid(), "key": k, "name_ar": ar, "name_en": en, "icon": ic, "active": True, "order": i, "created_at": now_iso()}
            for i, (k, ar, en, ic) in enumerate(cats)
        ])
    # Document types
    if await db.document_types.count_documents({}) == 0:
        types = [
            ("driving_license", "رخصة القيادة", "Driving License", "driver", True, True),
            ("national_id", "الهوية الوطنية", "National ID", "driver", True, True),
            ("vehicle_registration", "استمارة المركبة", "Vehicle Registration", "vehicle", True, True),
            ("vehicle_insurance", "تأمين المركبة", "Vehicle Insurance", "vehicle", True, True),
            ("vehicle_inspection", "الفحص الفني", "Vehicle Inspection", "vehicle", False, True),
            ("health_certificate", "شهادة صحية", "Health Certificate", "driver", False, True),
            ("commercial_permit", "تصريح تجاري", "Commercial Permit", "provider", False, True),
        ]
        await db.document_types.insert_many([
            {"id": uid(), "key": k, "name_ar": ar, "name_en": en, "owner_type": ot,
             "required": req, "has_expiry": exp, "active": True, "created_at": now_iso()}
            for (k, ar, en, ot, req, exp) in types
        ])
    # RBAC roles
    if await db.roles.count_documents({}) == 0:
        from extra import PERMISSIONS
        roles = [
            ("super_admin", "مدير عام", "Super Admin", list(PERMISSIONS)),
            ("operations_manager", "مدير العمليات", "Operations Manager",
             ["users.view", "shipments.view", "shipments.edit", "shipments.cancel", "shipments.assign", "documents.view", "reports.view"]),
            ("document_reviewer", "مدقق المستندات", "Document Reviewer",
             ["documents.view", "documents.review", "documents.approve", "documents.reject"]),
            ("finance_manager", "مدير مالي", "Finance Manager",
             ["finance.view", "finance.transactions", "finance.commission", "finance.payouts", "finance.adjust", "finance.refund", "reports.view", "reports.export"]),
            ("support", "دعم العملاء", "Customer Support", ["users.view", "shipments.view"]),
        ]
        await db.roles.insert_many([
            {"id": uid(), "key": k, "name_ar": ar, "name_en": en, "permissions": p, "created_at": now_iso()}
            for (k, ar, en, p) in roles
        ])
    # Platform settings
    if not await db.settings.find_one({"id": "platform"}):
        await db.settings.insert_one({"id": "platform", "commission_type": "percentage", "commission_value": 10, "currency": "OMR"})


async def run_seed():
    await seed_admin()
    await seed_users()
    await seed_shipments()
    await seed_phase11()
