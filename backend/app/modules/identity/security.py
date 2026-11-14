"""Security primitives for H-05. Never log raw tokens or credentials."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import re
import secrets
from functools import lru_cache

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


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    """Random non-account Argon2 hash for equalizing unknown-user verification."""
    return PASSWORD_HASHER.hash(new_secret())


def verify_known_or_dummy(hashed: str | None, password: str) -> bool:
    """Keep unknown/disabled and real-user login timing in a similar hash-work class."""
    return check_password(hashed or _dummy_password_hash(), password)


def login_email_key(email: str) -> str:
    """Avoid low-entropy unsalted email digests in the login throttle table."""
    pepper = os.environ.get("HESABYAR_LOGIN_PEPPER", "")
    if len(pepper) < 32:
        raise RuntimeError("HESABYAR_LOGIN_PEPPER must be a private 32+ character secret")
    return hmac.new(pepper.encode("utf-8"), email.encode("utf-8"), hashlib.sha256).hexdigest()


def bound_csrf(session_id: str, expires_at: str) -> str:
    """HMAC-bind a new random CSRF nonce to cookie nonce, origin and expiry.

    The 256-bit HttpOnly cookie value is an unpredictable per-session HMAC key;
    the completed token is also stored by digest for strict single-current-token
    rotation (and never persisted in plaintext).
    """
    origin = os.environ.get("HESABYAR_ALLOWED_ORIGIN", "").rstrip("/")
    if not origin.startswith("https://"):
        raise RuntimeError("Explicit HTTPS HESABYAR_ALLOWED_ORIGIN required")
    nonce = new_secret()
    tag = hmac.new(
        session_id.encode("utf-8"),
        f"{origin}|{expires_at}|{nonce}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return nonce + "." + tag


def csrf_hmac_valid(session_id: str, expires_at: str, token: str) -> bool:
    """Verify the HMAC-bound token without accepting stale or altered origins."""
    try:
        nonce, tag = token.rsplit(".", 1)
    except ValueError:
        return False
    if not nonce or len(tag) != 64:
        return False
    origin = os.environ.get("HESABYAR_ALLOWED_ORIGIN", "").rstrip("/")
    expected = hmac.new(
        session_id.encode("utf-8"),
        f"{origin}|{expires_at}|{nonce}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(tag, expected)
