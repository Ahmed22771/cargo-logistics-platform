"""CARGO OTP Service — provider-agnostic one-time-password layer.

Layers (top-down):
  Authentication routes (server.py)  -> thin HTTP adapters only
  OTP Service (this module)          -> lifecycle: issue, expiry, single-use,
                                        verify-attempts, rate limiting
  OTP Provider                       -> delivery channel adapter.
                                        Today: DemoOtpProvider.
                                        Future: Twilio / regional SMS / any OTP
                                        provider — implement BaseOtpProvider,
                                        register it, set OTP_PROVIDER=<name>.

Design rules:
- The raw OTP code NEVER leaves this module except through provider.send().
- The demo code is surfaced to the HTTP response ONLY when
  OTP_DEMO_EXPOSE_CODE=true (development/test). In production set it to false
  (or pick a real provider) — the code then never appears in any API response.
- The rate limiter is a class with a tiny interface (hit/reset) so it can be
  swapped for a Redis-backed implementation later without changing callers.
- This module never touches FastAPI Request/Response; callers pass phone/ip.
  That keeps the service re-implementable in Go/Node/Java with the same
  contract and MongoDB collections.
"""

import os
import random
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from database import db

OTP_ROLES = ("customer", "driver", "provider")


# ---------------------------------------------------------------------------
# Configuration — all env-driven, read lazily so ops/tests can override.
# ---------------------------------------------------------------------------
def _cfg_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def otp_provider_name() -> str:
    return (os.environ.get("OTP_PROVIDER") or "demo").strip().lower()


def otp_demo_expose_code() -> bool:
    return (os.environ.get("OTP_DEMO_EXPOSE_CODE") or "true").strip().lower() in ("1", "true", "yes", "on")


def otp_ttl_seconds() -> int:
    return _cfg_int("OTP_TTL_SECONDS", 300)


def otp_request_max_per_phone() -> int:
    return _cfg_int("OTP_REQUEST_MAX_PER_PHONE", 5)


def otp_request_max_per_ip() -> int:
    return _cfg_int("OTP_REQUEST_MAX_PER_IP", 30)


def otp_verify_max_per_ip() -> int:
    return _cfg_int("OTP_VERIFY_MAX_PER_IP", 60)


def otp_rate_window_seconds() -> int:
    return _cfg_int("OTP_RATE_WINDOW_SECONDS", 600)


def otp_verify_max_attempts() -> int:
    return _cfg_int("OTP_VERIFY_MAX_ATTEMPTS", 5)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Rate limiting — in-memory sliding window, replaceable (Redis) later.
# ---------------------------------------------------------------------------
class InMemoryRateLimiter:
    """Sliding-window counter keyed by an arbitrary string. Process-local:
    correct for a single backend instance. To scale horizontally, implement
    the same hit()/reset() interface against Redis and swap _rate_limiter."""

    def __init__(self):
        self._hits = {}  # key -> list[datetime]

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = _now()
        cutoff = now - timedelta(seconds=window_seconds)
        hits = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(hits) >= limit:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)


_rate_limiter = InMemoryRateLimiter()


# ---------------------------------------------------------------------------
# Provider adapters
# ---------------------------------------------------------------------------
class OtpSendResult:
    def __init__(self, delivered: bool, channel: str, dev_code=None):
        self.delivered = delivered
        self.channel = channel
        # dev_code is ONLY ever populated by the demo provider when explicitly
        # enabled — production providers must leave it None.
        self.dev_code = dev_code


class BaseOtpProvider:
    """Contract for any future SMS/OTP provider (Twilio, Unifonic, ...).
    send() MUST NOT return the raw code in dev_code — that field is reserved
    for the demo provider only."""

    name = "base"

    async def send(self, phone: str, role: str, code: str) -> OtpSendResult:
        raise NotImplementedError


class DemoOtpProvider(BaseOtpProvider):
    """Development/test provider. No external call; the code is surfaced to the
    caller only when OTP_DEMO_EXPOSE_CODE=true. When disabled, the code is
    generated, stored with expiry, but never exposed — the API response then
    contains no demo_code."""

    name = "demo"

    async def send(self, phone: str, role: str, code: str) -> OtpSendResult:
        return OtpSendResult(
            delivered=True,
            channel="demo",
            dev_code=code if otp_demo_expose_code() else None,
        )


_PROVIDERS = {"demo": DemoOtpProvider()}


def register_otp_provider(provider: BaseOtpProvider) -> None:
    """Register a new provider adapter (e.g. register_otp_provider(TwilioProvider(...)))."""
    _PROVIDERS[provider.name] = provider


def get_otp_provider() -> BaseOtpProvider:
    p = _PROVIDERS.get(otp_provider_name())
    if not p:
        # Fail closed: never silently fall back to demo — that would leak codes
        # in an environment that believes a real provider is active.
        raise HTTPException(status_code=500, detail="OTP_PROVIDER_NOT_CONFIGURED")
    return p


# ---------------------------------------------------------------------------
# OTP Service — lifecycle + rate limiting. Pure logic; no HTTP objects.
# ---------------------------------------------------------------------------
async def request_otp(phone: str, role: str, ip: str = None) -> dict:
    """Issue a new OTP for (phone, role) and deliver it via the configured provider.

    Rate limits (429 OTP_RATE_LIMITED):
      - per phone: OTP_REQUEST_MAX_PER_PHONE per OTP_RATE_WINDOW_SECONDS
      - per IP:    OTP_REQUEST_MAX_PER_IP   per OTP_RATE_WINDOW_SECONDS
    """
    if role not in OTP_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")

    window = otp_rate_window_seconds()
    if not _rate_limiter.hit(f"otp:req:phone:{role}:{phone}", otp_request_max_per_phone(), window):
        raise HTTPException(status_code=429, detail="OTP_RATE_LIMITED")
    if ip and not _rate_limiter.hit(f"otp:req:ip:{ip}", otp_request_max_per_ip(), window):
        raise HTTPException(status_code=429, detail="OTP_RATE_LIMITED")

    code = f"{random.randint(0, 999999):06d}"
    now = _now()
    await db.otps.update_one(
        {"phone": phone, "role": role},
        {"$set": {
            "code": code,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=otp_ttl_seconds())).isoformat(),
            "attempts": 0,
        }},
        upsert=True,
    )

    result = await get_otp_provider().send(phone, role, code)
    # SECURITY: the raw code is never logged; it only travels via provider channel.
    resp = {"success": True, "channel": result.channel}
    if result.dev_code is not None:
        resp["demo"] = True
        resp["demo_code"] = result.dev_code
    return resp


async def verify_otp_code(phone: str, role: str, code: str, ip: str = None) -> bool:
    """Validate an OTP: expiry, attempt budget, single-use consumption.

    Returns True on success and CONSUMES the code. Raises 400 with a generic
    detail for every failure mode (no oracle about which stage failed)."""
    if role not in OTP_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")

    if ip and not _rate_limiter.hit(f"otp:ver:ip:{ip}", otp_verify_max_per_ip(), otp_rate_window_seconds()):
        raise HTTPException(status_code=429, detail="OTP_RATE_LIMITED")

    generic = "Invalid or expired code"
    otp = await db.otps.find_one({"phone": phone, "role": role})
    if not otp:
        raise HTTPException(status_code=400, detail=generic)

    exp = otp.get("expires_at")
    if exp:
        try:
            if datetime.fromisoformat(exp) < _now():
                await db.otps.delete_one({"phone": phone, "role": role})
                raise HTTPException(status_code=400, detail=generic)
        except ValueError:
            pass  # unparseable timestamp -> fall through to code comparison

    if int(otp.get("attempts") or 0) >= otp_verify_max_attempts():
        # Attempt budget exhausted: invalidate the code entirely; the user must
        # request a fresh one (which itself is rate-limited per phone).
        await db.otps.delete_one({"phone": phone, "role": role})
        raise HTTPException(status_code=400, detail=generic)

    if otp.get("code") != code:
        await db.otps.update_one({"phone": phone, "role": role}, {"$inc": {"attempts": 1}})
        raise HTTPException(status_code=400, detail=generic)

    # Single-use: consume immediately on success.
    await db.otps.delete_one({"phone": phone, "role": role})
    _rate_limiter.reset(f"otp:req:phone:{role}:{phone}")
    return True
