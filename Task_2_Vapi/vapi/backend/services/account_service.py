from __future__ import annotations

from typing import Any, Dict, List

from ..database.database import DB
from ..database.models import CallSession
from .authentication import is_customer_verified, is_verified


def get_account_details(
    customer_id: str,
    call_session: CallSession | None = None,
    call_id: str | None = None,
) -> Dict[str, Any]:
    if call_session is None and call_id is not None:
        call_session = DB.get_session(call_id)
    account = DB.get_account(customer_id)
    if call_session is not None and call_session.customer_id != customer_id:
        raise ValueError("Call session does not match customer_id.")
    if call_session is not None and not is_verified(call_session):
        raise PermissionError("Identity verification required before account disclosure.")
    if call_session is None and not is_customer_verified(customer_id):
        raise PermissionError("Identity verification required before account disclosure.")
    return account.authenticated_view()


def get_safe_account_summary(customer_id: str) -> Dict[str, Any]:
    return DB.get_account(customer_id).safe_view()


def list_accounts() -> List[Dict[str, Any]]:
    return [account.safe_view() for account in DB.list_accounts()]
