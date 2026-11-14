"""Security primitives for H-05. Never log raw tokens or credentials."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLES = ("owner", "admin", "accountant", "viewer")


def normalize_email(value: str) -> str:
    result = value.strip().casefold()
    if len(result) > 320 or not EMAIL_PATTERN.fullmatch(result):
        raise ValueError("Invalid email")
    return result


def validate_password(password: str) -> None:
    if not 12 <= len(password) <= 1024 or not any(c.islower() for c in password) or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least 12 characters, upper/lowercase and digits")


def new_secret() -> str:
    return secrets.token_urlsafe(32)  # 256 random bits, opaque URL-safe string


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def equal_digest(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def instant(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def expiry(minutes: int) -> str:
    return instant(utcnow() + timedelta(minutes=minutes))


def now_string() -> str:
    return instant(utcnow())


def password_hash(password: str) -> str:
    validate_password(password)
    return PASSWORD_HASHER.hash(password)


def check_password(hashed: str | None, password: str) -> bool:
    if not hashed:
        return False
    try:
        return PASSWORD_HASHER.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
