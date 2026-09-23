import os
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request, Depends

from database import db

JWT_ALGORITHM = "HS256"


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def _app_env() -> str:
    return (os.environ.get("APP_ENV") or "development").strip().lower()


def _is_production() -> bool:
    return _app_env() in ("production", "prod")


# Known weak / placeholder values that must never protect a production system.
_WEAK_ADMIN_PASSWORDS = {
    "admin123", "admin", "password", "passw0rd", "changeme",
    "secret", "123456", "cargo123", "admin@123", "test",
}
_WEAK_JWT_SECRETS = {
    "secret", "changeme", "dev", "development", "jwt_secret",
    "your-secret-key", "your-256-bit-secret", "supersecret", "cargo",
    "change-me", "test", "password",
}


def validate_secrets() -> None:
    """Fail-closed startup guard for production secrets.

    Prevents booting production with default/weak credentials. Never logs or
    echoes the actual secret values — only reports which variable is unsafe.
    """
    if not _is_production():
        return

    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_password or admin_password.strip().lower() in _WEAK_ADMIN_PASSWORDS:
        raise RuntimeError(
            "INSECURE_SECRET: ADMIN_PASSWORD is missing or a known-weak value; "
            "set a strong ADMIN_PASSWORD before running in production."
        )
    if len(admin_password) < 12:
        raise RuntimeError(
            "INSECURE_SECRET: ADMIN_PASSWORD must be at least 12 characters in production."
        )

    jwt_secret = os.environ.get("JWT_SECRET", "")
    if not jwt_secret or jwt_secret.strip().lower() in _WEAK_JWT_SECRETS:
        raise RuntimeError(
            "INSECURE_SECRET: JWT_SECRET is missing or a known-weak value; "
            "set a strong random JWT_SECRET before running in production."
        )
    if len(jwt_secret) < 32:
        raise RuntimeError(
            "INSECURE_SECRET: JWT_SECRET must be at least 32 characters in production."
        )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        raw_status = (user.get("status") or "active").lower()
        if raw_status == "suspended" or user.get("verification_status") == "SUSPENDED":
            raise HTTPException(status_code=403, detail="ACCOUNT_SUSPENDED")
        if raw_status in ("inactive", "disabled"):
            raise HTTPException(status_code=403, detail="ACCOUNT_DISABLED")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_roles(*roles):
    async def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Forbidden: insufficient permissions")
        return user

    return dependency
