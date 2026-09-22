"""CARGO Compliance / Eligibility Service — pure business logic, HTTP-independent.

Regulatory basis for this phase: the CONFIRMED requirements referenced by the user
from MTCIT Ministerial Decision 114/2021 (smart-application licensing, operating cards,
linkage to the Naql platform, and service suspension when a license/operating card
expires). ONLY the explicitly-confirmed status rules are enforced here — no invented
conditions (no vehicle age, insurance type, weight limits, specific license class...).

Rules enforced (block ONLY on explicit negative statuses; empty/unknown does NOT block
in this phase, except driver training which the confirmed rule requires to be COMPLETED):
  * Application license (CARGO):   ACTIVE allowed; EXPIRED/SUSPENDED/INACTIVE -> blocked.
  * Carrier / provider license:    EXPIRED/SUSPENDED/INACTIVE -> blocked.
  * Vehicle operating card:        EXPIRED/SUSPENDED/INACTIVE -> blocked.
  * Driver application training:    COMPLETED -> allowed; anything else -> blocked.

The service is deliberately a set of small pure-ish async functions returning a stable
result contract {eligible: bool, reasons: [{code, category, message, source}]} so a
future Go / Node / TypeScript / Java extraction reuses the same contract, and so a
NaqlProvider can later feed real statuses without rewriting callers.
"""
import uuid
from datetime import datetime, timezone

from database import db

# Statuses that block a regulated activity when explicitly set.
NEGATIVE_STATUSES = {"EXPIRED", "SUSPENDED", "INACTIVE"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reason(code: str, category: str, message: str, source: str) -> dict:
    return {"code": code, "category": category, "message": message, "source": source}


def _result(reasons: list) -> dict:
    return {"eligible": len(reasons) == 0, "reasons": reasons}


# ---------------- individual rule evaluators ----------------
async def _application_reasons() -> list:
    doc = await db.settings.find_one({"id": "app_license"}, {"_id": 0})
    status = ((doc or {}).get("status") or "").upper()
    if status in NEGATIVE_STATUSES:
        return [_reason(f"APPLICATION_LICENSE_{status}", "application",
                        f"CARGO application license status is {status}", "app_license")]
    return []


def _driver_reasons(driver: dict) -> list:
    reg = (driver or {}).get("regulatory") or {}
    training = (reg.get("driver_training_status") or "").upper()
    if training != "COMPLETED":
        return [_reason("DRIVER_APP_TRAINING_NOT_COMPLETED", "driver",
                        "Driver application training is not completed", "driver_regulatory")]
    return []


def _vehicle_reasons(vehicle: dict) -> list:
    reg = (vehicle or {}).get("regulatory") or {}
    status = (reg.get("operating_card_status") or "").upper()
    if status in NEGATIVE_STATUSES:
        return [_reason(f"VEHICLE_OPERATING_CARD_{status}", "vehicle",
                        f"Vehicle operating card status is {status}", "vehicle_regulatory")]
    return []


def _provider_reasons(provider: dict) -> list:
    cl = (provider or {}).get("carrier_license") or {}
    status = (cl.get("status") or "").upper()
    if status in NEGATIVE_STATUSES:
        return [_reason(f"CARRIER_LICENSE_{status}", "provider",
                        f"Carrier license status is {status}", "carrier_license")]
    return []


# ---------------- public composite checks ----------------
async def check_application_eligibility() -> dict:
    return _result(await _application_reasons())


async def check_driver_eligibility(driver: dict) -> dict:
    reasons = await _application_reasons()
    reasons += _driver_reasons(driver)
    return _result(reasons)


async def check_vehicle_eligibility(vehicle: dict) -> dict:
    # Vehicle eligibility is scoped to the operating card only (confirmed rule).
    return _result(_vehicle_reasons(vehicle))


async def check_provider_eligibility(provider: dict) -> dict:
    reasons = await _application_reasons()
    reasons += _provider_reasons(provider)
    return _result(reasons)


async def check_trip_eligibility(trip: dict) -> dict:
    """Composite gate used at assignment / trip start. Missing links are skipped
    (do not block) except the always-on application + driver-training gates."""
    reasons = await _application_reasons()
    driver = None
    if trip.get("driver_id"):
        driver = await db.users.find_one({"id": trip["driver_id"]}, {"_id": 0, "password_hash": 0})
    reasons += _driver_reasons(driver or {})
    if trip.get("provider_id"):
        provider = await db.users.find_one({"id": trip["provider_id"]}, {"_id": 0, "password_hash": 0})
        reasons += _provider_reasons(provider or {})
    if trip.get("vehicle_id"):
        vehicle = await db.vehicles.find_one({"id": trip["vehicle_id"]}, {"_id": 0})
        reasons += _vehicle_reasons(vehicle or {})
    return _result(reasons)


# ---------------- audit helpers (write directly to keep this module HTTP-free) ----------------
async def _audit(actor: dict, action: str, entity: str, entity_id: str, reason: str = "", extra=None):
    a = actor or {}
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": a.get("id", "system"), "admin_name": a.get("name", "system"),
        "actor_id": a.get("id", "system"), "actor_name": a.get("name", "system"),
        "actor_role": a.get("role", "system"),
        "action": action, "entity": entity, "entity_id": entity_id,
        "old_value": None, "new_value": extra, "reason": reason,
        "result": "success", "timestamp": _now_iso(),
    })


async def log_eligibility_blocked(actor: dict, entity: str, entity_id: str, result: dict):
    codes = ",".join(r["code"] for r in result.get("reasons", []))
    await _audit(actor, "eligibility_blocked", entity, entity_id, reason=codes,
                 extra={"reasons": result.get("reasons", [])})


async def log_eligibility_restored(actor: dict, entity: str, entity_id: str):
    await _audit(actor, "eligibility_restored", entity, entity_id, reason="",
                 extra={"eligible": True})


async def log_compliance_checked(actor: dict, entity: str, entity_id: str, result: dict):
    await _audit(actor, "compliance_status_checked", entity, entity_id,
                 reason=("eligible" if result.get("eligible") else "blocked"),
                 extra={"eligible": result.get("eligible"), "reasons": result.get("reasons", [])})
