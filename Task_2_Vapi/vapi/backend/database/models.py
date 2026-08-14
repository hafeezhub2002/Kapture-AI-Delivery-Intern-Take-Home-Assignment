from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from ..services.utils.logger import sanitize_payload


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class CallState(str, Enum):
    INIT = "INIT"
    AUTH_PENDING = "AUTH_PENDING"
    AUTHENTICATED = "AUTHENTICATED"
    NEGOTIATION = "NEGOTIATION"
    PTP_COLLECTED = "PTP_COLLECTED"
    ESCALATED = "ESCALATED"
    CALL_ENDED = "CALL_ENDED"


class AuthenticationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class Intent(str, Enum):
    WILL_PAY = "WILL_PAY"
    CANNOT_PAY = "CANNOT_PAY"
    HARDSHIP = "HARDSHIP"
    DISPUTE = "DISPUTE"
    ALREADY_PAID = "ALREADY_PAID"
    WRONG_PERSON = "WRONG_PERSON"
    WRONG_NUMBER = "WRONG_NUMBER"
    CALLBACK_REQUEST = "CALLBACK_REQUEST"
    HOSTILE = "HOSTILE"
    DO_NOT_CALL = "DO_NOT_CALL"
    UNKNOWN = "UNKNOWN"


class Disposition(str, Enum):
    PROMISE_TO_PAY = "PROMISE_TO_PAY"
    CANNOT_PAY = "CANNOT_PAY"
    ALREADY_PAID = "ALREADY_PAID"
    DISPUTE = "DISPUTE"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED"
    DO_NOT_CALL = "DO_NOT_CALL"
    WRONG_PERSON = "WRONG_PERSON"
    WRONG_NUMBER = "WRONG_NUMBER"
    ESCALATED = "ESCALATED"
    NO_CONTACT = "NO_CONTACT"
    HOSTILE = "HOSTILE"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    NO_ISSUE = "NO_ISSUE"


@dataclass
class CustomerAccount:
    customer_id: str
    customer_name: str
    loan_type: str
    overdue_amount: float
    days_past_due: int
    due_date: Optional[str] = None
    phone_number: Optional[str] = None
    is_dnc: bool = False
    is_paid: bool = False
    verification_tokens: List[str] = field(default_factory=list)
    payment_links: List[Dict[str, Any]] = field(default_factory=list)
    ptp_history: List[Dict[str, Any]] = field(default_factory=list)
    dispositions: List[Dict[str, Any]] = field(default_factory=list)
    escalations: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def safe_view(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "loan_type": self.loan_type,
            "phone_number": self.phone_number,
        }

    def authenticated_view(self) -> Dict[str, Any]:
        data = self.safe_view()
        data.update(
            {
                "overdue_amount": self.overdue_amount,
                "days_past_due": self.days_past_due,
                "due_date": self.due_date,
                "is_dnc": self.is_dnc,
                "is_paid": self.is_paid,
            }
        )
        return data


@dataclass
class CallEvent:
    timestamp: str
    event_type: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CallSession:
    call_id: str
    customer_id: str
    state: CallState = CallState.INIT
    authentication_status: AuthenticationStatus = AuthenticationStatus.UNVERIFIED
    intent: Intent = Intent.UNKNOWN
    disposition: Optional[Disposition] = None
    verification_attempts: int = 0
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    last_user_message: Optional[str] = None
    last_bot_message: Optional[str] = None
    no_input_attempts: int = 0
    hostile_warnings: int = 0
    ptp_amount: Optional[float] = None
    ptp_date: Optional[str] = None
    callback_date: Optional[str] = None
    escalation_reason: Optional[str] = None
    tool_events: List[CallEvent] = field(default_factory=list)
    transcript: List[Dict[str, str]] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def add_event(self, event_type: str, details: Optional[Dict[str, Any]] = None) -> None:
        safe_details = sanitize_payload(details or {})
        self.tool_events.append(
            CallEvent(
                timestamp=utc_now(),
                event_type=event_type,
                details=safe_details,
            )
        )
        self.touch()

    def add_turn(self, role: str, content: str) -> None:
        self.transcript.append({"role": role, "content": content})
        self.touch()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "customer_id": self.customer_id,
            "state": self.state.value,
            "authentication_status": self.authentication_status.value,
            "intent": self.intent.value,
            "disposition": self.disposition.value if self.disposition else None,
            "verification_attempts": self.verification_attempts,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_user_message": self.last_user_message,
            "last_bot_message": self.last_bot_message,
            "no_input_attempts": self.no_input_attempts,
            "hostile_warnings": self.hostile_warnings,
            "ptp_amount": self.ptp_amount,
            "ptp_date": self.ptp_date,
            "callback_date": self.callback_date,
            "escalation_reason": self.escalation_reason,
            "tool_events": [
                {
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "details": event.details,
                }
                for event in self.tool_events
            ],
            "transcript": list(self.transcript),
        }


def new_call_id() -> str:
    return uuid.uuid4().hex


def iso_today() -> str:
    return date.today().isoformat()
