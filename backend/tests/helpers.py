"""Shared helpers for tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Dict, Optional
from urllib.parse import urlencode

TEST_BOT_TOKEN = "999999:TEST_TOKEN"
TEST_SECRET_KEY = "test-secret-key"


def generate_init_data(bot_token: str, overrides: Optional[Dict[str, str]] = None) -> str:
    """Create signed initData payload resembling Telegram WebApp data."""

    payload = {
        "query_id": "test-query",
        "user": json.dumps(
            {
                "id": 123456,
                "first_name": "John",
                "last_name": "Doe",
                "username": "john_doe",
            },
            separators=(",", ":"),
        ),
        "auth_date": str(int(time.time())),
    }
    if overrides:
        payload.update(overrides)

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hmac.new(
        key="WebAppData".encode(),
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()
    hash_value = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    payload["hash"] = hash_value
    return urlencode(payload)
