from __future__ import annotations

from typing import Any, Dict, Optional

from ..database.database import DB
from ..database.models import CallSession, Disposition
from .authentication import is_verified
from .disposition_service import mark_disposition
from .utils.logger import utc_now


def _normalize_amount(amount: Any) -> float:
    try:
        return float(str(amount).replace(",", "").strip())
    except Exception as exc:
        raise ValueError("Invalid amount.") from exc


def log_promise_to_pay(
    customer_id: str,
    amount: Any,
    ptp_date: str,
    call_session: Optional[CallSession] = None,
    call_id: Optional[str] = None,
) -> Dict[str, Any]:
    if call_session is None and call_id is not None:
        call_session = DB.get_session(call_id)
    account = DB.get_account(customer_id)
    normalized_amount = _normalize_amount(amount)
    payload = {
        "timestamp": utc_now(),
        "customer_id": customer_id,
        "amount": normalized_amount,
        "ptp_date": ptp_date,
    }
    account.ptp_history.append(payload)
    account.notes.append(f"PTP recorded for {normalized_amount} on {ptp_date}")
    if call_session is not None:
        if not is_verified(call_session):
            raise PermissionError("PTP logging requires verified identity.")
        call_session.ptp_amount = normalized_amount
        call_session.ptp_date = ptp_date
        call_session.add_event("ptp_logged", payload)
        DB.save_session(call_session)
        mark_disposition(customer_id, Disposition.PROMISE_TO_PAY, call_session=call_session, details=payload)
        account.payment_links.append(
            {
                "timestamp": utc_now(),
                "customer_id": customer_id,
                "channel": "sms",
                "payment_link": f"https://pay.example.com/{customer_id.lower()}?channel=sms",
            }
        )
        call_session.add_event("payment_link_sent", {"channel": "sms"})
        DB.save_session(call_session)
    else:
        account.payment_links.append(
            {
                "timestamp": utc_now(),
                "customer_id": customer_id,
                "channel": "sms",
                "payment_link": f"https://pay.example.com/{customer_id.lower()}?channel=sms",
            }
        )
    return payload


def send_payment_link(customer_id: str, channel: str = "sms", call_id: Optional[str] = None) -> Dict[str, Any]:
    account = DB.get_account(customer_id)
    link = f"https://pay.example.com/{customer_id.lower()}?channel={channel}"
    payload = {
        "timestamp": utc_now(),
        "customer_id": customer_id,
        "channel": channel,
        "payment_link": link,
    }
    account.payment_links.append(payload)
    return payload


def record_already_paid(
    customer_id: str,
    call_session: Optional[CallSession] = None,
    details: Optional[Dict[str, Any]] = None,
    call_id: Optional[str] = None,
) -> Dict[str, Any]:
    if call_session is None and call_id is not None:
        call_session = DB.get_session(call_id)
    account = DB.get_account(customer_id)
    account.is_paid = True
    payload = {
        "timestamp": utc_now(),
        "customer_id": customer_id,
        "details": details or {},
    }
    if call_session is not None:
        call_session.add_event("already_paid", payload)
        DB.save_session(call_session)
        mark_disposition(customer_id, Disposition.ALREADY_PAID, call_session=call_session, details=details or {})
    return payload
