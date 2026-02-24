"""Shared Ghost Admin API JWT builder.

Builds an HS256 JWT for Ghost Admin API authentication.
The admin_api_key format is "{id}:{secret}" — the id becomes the kid header,
and the hex-decoded secret is the HMAC signing key.

Used by both kerygma_social.ghost (publishing) and
kerygma_strategy.ghost_metrics (metrics pull-back).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64encode


def build_ghost_jwt(admin_api_key: str) -> str:
    """Build an HS256 JWT for Ghost Admin API authentication.

    Args:
        admin_api_key: Ghost admin key in "{id}:{secret}" format.

    Returns:
        Signed JWT string.

    Raises:
        ValueError: If the key format is invalid.
    """
    parts = admin_api_key.split(":")
    if len(parts) != 2:
        raise ValueError("Ghost admin_api_key must be in {id}:{secret} format")
    key_id, secret_hex = parts

    header = {"alg": "HS256", "typ": "JWT", "kid": key_id}
    now = int(time.time())
    payload = {"iat": now, "exp": now + 300, "aud": "/admin/"}

    def _b64(data: bytes) -> str:
        return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    header_b64 = _b64(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}"
    secret_bytes = bytes.fromhex(secret_hex)
    signature = hmac.new(secret_bytes, signing_input.encode(), hashlib.sha256).digest()

    return f"{signing_input}.{_b64(signature)}"
