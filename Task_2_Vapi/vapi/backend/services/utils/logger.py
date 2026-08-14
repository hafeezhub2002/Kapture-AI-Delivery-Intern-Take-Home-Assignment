from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log_event(event_type: str, **details: Any) -> Dict[str, Any]:
    return {"timestamp": utc_now(), "event_type": event_type, "details": sanitize_payload(details)}


def redact_sensitive(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if len(value) <= 2:
        return "**"
    return value[0] + "*" * (len(value) - 2) + value[-1]


def sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    redacted: Dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            if key in {"customer_name", "verification_value"}:
                redacted[key] = redact_sensitive(value)
            elif key in {"phone_number", "aadhaar", "pan", "email"}:
                redacted[key] = "***REDACTED***"
            elif key == "message" and value:
                redacted[key] = value[:24] + ("..." if len(value) > 24 else "")
            else:
                redacted[key] = value
        else:
            redacted[key] = value
    return redacted
