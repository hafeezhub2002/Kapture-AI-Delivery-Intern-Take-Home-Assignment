from __future__ import annotations

from typing import Any, Dict, Optional

from ..database.database import DB
from ..database.models import CallSession, Disposition
from .disposition_service import mark_disposition
from .utils.logger import log_event


def escalate_to_agent(
    customer_id: str,
    reason: str,
    call_session: Optional[CallSession] = None,
    call_id: Optional[str] = None,
) -> Dict[str, Any]:
    if call_session is None and call_id is not None:
        call_session = DB.get_session(call_id)
    account = DB.get_account(customer_id)
    payload = {
        "customer_id": customer_id,
        "reason": reason,
        "escalated": True,
    }
    account.escalations.append(
        {
            "timestamp": log_event("escalation", customer_id=customer_id, reason=reason)["timestamp"],
            "reason": reason,
        }
    )
    if call_session is not None:
        call_session.escalation_reason = reason
        call_session.add_event("escalation", {"reason": reason})
        DB.save_session(call_session)
    return payload


def escalate_and_close(
    customer_id: str,
    reason: str,
    call_session: Optional[CallSession] = None,
    call_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload = escalate_to_agent(customer_id, reason, call_session=call_session, call_id=call_id)
    mark_disposition(customer_id, Disposition.ESCALATED, call_session=call_session, call_id=call_id, details={"reason": reason})
    return payload
