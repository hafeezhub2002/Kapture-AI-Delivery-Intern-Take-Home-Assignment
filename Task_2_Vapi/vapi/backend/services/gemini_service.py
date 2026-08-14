from __future__ import annotations

import http.client
import json
import os
import ssl
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, Optional


GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
_GEMINI_HOST = "generativelanguage.googleapis.com"
_GEMINI_PATH = f"/v1beta/models/{GEMINI_MODEL}:generateContent"

# Pre-built SSL context — reused across calls (avoids per-call TLS handshake overhead)
_SSL_CTX = ssl.create_default_context()

# Persistent HTTPS connection — reused across calls (keep-alive, saves ~80 ms per round-trip)
_conn: Optional[http.client.HTTPSConnection] = None


def _get_conn() -> http.client.HTTPSConnection:
    """Return a live keep-alive connection, reconnecting if needed."""
    global _conn
    if _conn is None:
        _conn = http.client.HTTPSConnection(_GEMINI_HOST, timeout=5, context=_SSL_CTX)
    return _conn


@dataclass
class GeminiPlan:
    response_text: str
    intent: str
    language: str = "en"
    should_send_payment_link: bool = False
    should_escalate: bool = False
    ptp_date: Optional[str] = None
    ptp_amount: Optional[float] = None
    escalation_reason: Optional[str] = None

    @classmethod
    def fallback(cls, response_text: str, intent: str) -> "GeminiPlan":
        return cls(response_text=response_text, intent=intent)


def gemini_available() -> bool:
    return bool(GEMINI_API_KEY)


# Cached once at import time — never rebuilt per call
_SYSTEM_PROMPT: str = (
    "You are Maya, a compliant outbound collections assistant for Kapture Finance. "
    "Never reveal debt details before verification. "
    "Reply in 1-2 short sentences only — this is a voice call. "
    "Classify intent from: CONFIRM_IDENTITY, PROMISE_TO_PAY, HARDSHIP_CLAIM, "
    "DISPUTE_DEBT, ALREADY_PAID, REQUEST_DNC, WRONG_PERSON, HOSTILE, CALLBACK_REQUEST, UNKNOWN. "
    "Return only valid JSON matching the schema."
)


def build_system_prompt() -> str:  # kept for compatibility
    return _SYSTEM_PROMPT


def build_request_payload(prompt: str) -> Dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "response_text": {"type": "string"},
            "intent": {
                "type": "string",
                "enum": [
                    "CONFIRM_IDENTITY",
                    "PROMISE_TO_PAY",
                    "HARDSHIP_CLAIM",
                    "DISPUTE_DEBT",
                    "ALREADY_PAID",
                    "REQUEST_DNC",
                    "WRONG_PERSON",
                    "HOSTILE",
                    "CALLBACK_REQUEST",
                    "UNKNOWN",
                ],
            },
            "language": {"type": "string", "enum": ["en", "hi"]},
            "should_send_payment_link": {"type": "boolean"},
            "should_escalate": {"type": "boolean"},
            "ptp_date": {"type": ["string", "null"]},
            "ptp_amount": {"type": ["number", "null"]},
            "escalation_reason": {"type": ["string", "null"]},
        },
        "required": ["response_text", "intent", "language", "should_send_payment_link", "should_escalate"],
        "additionalProperties": False,
    }
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 120,   # voice replies are short — fewer tokens = faster response
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }


def call_gemini(prompt: str) -> GeminiPlan:
    """Call Gemini via a persistent keep-alive HTTPS connection for low latency."""
    if not gemini_available():
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    global _conn
    payload = json.dumps(build_request_payload(prompt)).encode("utf-8")
    path = f"{_GEMINI_PATH}?key={GEMINI_API_KEY}"
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(payload)),
        "Connection": "keep-alive",
    }

    for attempt in range(2):   # one retry on broken-pipe / stale connection
        try:
            conn = _get_conn()
            conn.request("POST", path, body=payload, headers=headers)
            resp = conn.getresponse()
            raw = resp.read().decode("utf-8")
            if resp.status != 200:
                raise RuntimeError(f"Gemini HTTP {resp.status}: {raw[:200]}")
            break
        except (http.client.RemoteDisconnected, BrokenPipeError, ConnectionResetError, OSError):
            # Stale keep-alive — drop and reconnect once
            _conn = None
            if attempt == 1:
                raise

    data = json.loads(raw)
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)
    return GeminiPlan(
        response_text=parsed["response_text"],
        intent=parsed["intent"],
        language=parsed.get("language", "en"),
        should_send_payment_link=bool(parsed.get("should_send_payment_link", False)),
        should_escalate=bool(parsed.get("should_escalate", False)),
        ptp_date=parsed.get("ptp_date"),
        ptp_amount=parsed.get("ptp_amount"),
        escalation_reason=parsed.get("escalation_reason"),
    )

