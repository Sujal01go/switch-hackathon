"""Authentication and session token generation for Switch Gateway API."""

import datetime
from typing import Optional
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import jwt

CONSOLE_SECRET = "ca8a3740bcc152d4945dd664add5dc7d7143e3e0957bb6c6e2dea232a422b657"
DEFAULT_USER_ID = "f4df2d4f-dc9c-4621-99f4-97fc6b1af001"
DEFAULT_EMAIL = "admin@switch.local"
DEFAULT_ROLE = "admin"
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000000"


def derive_session_key(secret: str = CONSOLE_SECRET) -> bytes:
    """Derive session HMAC key using HKDF-SHA256 matching Switch Core keys.py."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"switch:gateway-session-jwt",
    )
    return hkdf.derive(secret.encode("utf-8"))


def generate_switch_auth_token(
    user_id: str = DEFAULT_USER_ID,
    email: str = DEFAULT_EMAIL,
    role: str = DEFAULT_ROLE,
    tenant_id: str = DEFAULT_TENANT_ID,
    secret: str = CONSOLE_SECRET,
    expires_hours: int = 24,
) -> str:
    """Generate a valid signed switch_auth JWT session cookie value."""
    key = derive_session_key(secret)
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "exp": now + datetime.timedelta(hours=expires_hours),
        "iat": now,
    }
    return jwt.encode(payload, key, algorithm="HS256", headers={"kid": "console"})

