from __future__ import annotations

from typing import Any, Dict, Optional

from ..database.database import DB
from ..database.models import CallSession, Disposition
from .utils.logger import log_event


def _coerce_disposition(value: str | Disposition) -> Disposition:
    if isinstance(value, Disposition):
        return value
    return Disposition(value)


def mark_disposition(
    customer_id: str,
    disposition: str | Disposition,
    call_session: Optional[CallSession] = None,
    details: Optional[Dict[str, Any]] = None,
    call_id: Optional[str] = None,
) -> Dict[str, Any]:
    if call_session is None and call_id is not None:
        call_session = DB.get_session(call_id)
    disp = _coerce_disposition(disposition)
    payload = DB.record_disposition(customer_id, disp, details=details)
    if call_session is not None:
        call_session.disposition = disp
        call_session.add_event("disposition", {"disposition": disp.value, **(details or {})})
        DB.save_session(call_session)
    return payload
