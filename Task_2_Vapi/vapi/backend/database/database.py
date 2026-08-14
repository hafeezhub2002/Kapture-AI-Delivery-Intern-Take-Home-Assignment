from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Any, Dict, Iterable, Optional

from .models import AuthenticationStatus, CallSession, CallState, CustomerAccount, Disposition, Intent, new_call_id
from ..services.utils.logger import utc_now


class InMemoryCollectionsDB:
    def __init__(self) -> None:
        self._accounts: Dict[str, CustomerAccount] = {}
        self._sessions: Dict[str, CallSession] = {}
        self._verified_customers: set[str] = set()
        self.reset()

    def reset(self) -> None:
        self._accounts = {}
        self._sessions = {}
        self._verified_customers = set()
        self._seed_accounts()

    def _seed_accounts(self) -> None:
        overdue_date = (date.today() - timedelta(days=12)).isoformat()
        rahul = CustomerAccount(
            customer_id="CUST-1001",
            customer_name="Rahul Sharma",
            loan_type="personal loan",
            overdue_amount=8499.0,
            days_past_due=12,
            due_date=overdue_date,
            phone_number="+91-99999-00001",
            # DOB: 4 June 2002  — accepted in multiple spoken/typed formats
            verification_tokens=[
                "04/06/2002", "4/06/2002", "4/6/2002", "04-06-2002",
                "4 june 2002", "june 4 2002", "4th june 2002", "june 4th 2002",
                "04 06 2002", "2002", "04062002",
            ],
        )
        priya = CustomerAccount(
            customer_id="CUST-1002",
            customer_name="Priya Singh",
            loan_type="two-wheeler loan",
            overdue_amount=12840.0,
            days_past_due=4,
            due_date=(date.today() - timedelta(days=4)).isoformat(),
            phone_number="+91-99999-00002",
            # DOB: 22 July 1992  — accepted in multiple spoken/typed formats
            verification_tokens=[
                "22/07/1992", "22-07-1992", "22 july 1992",
                "july 22 1992", "22nd july 1992", "july 22nd 1992",
                "22 07 1992", "1992", "22071992",
            ],
        )
        self._accounts[rahul.customer_id] = rahul
        self._accounts[priya.customer_id] = priya

    def list_accounts(self) -> Iterable[CustomerAccount]:
        return list(self._accounts.values())

    def get_account(self, customer_id: str) -> CustomerAccount:
        try:
            return self._accounts[customer_id]
        except KeyError as exc:
            raise KeyError(f"Unknown customer_id: {customer_id}") from exc

    def upsert_account(self, account: CustomerAccount) -> None:
        self._accounts[account.customer_id] = account

    def create_session(self, customer_id: str, call_id: Optional[str] = None) -> CallSession:
        if customer_id not in self._accounts:
            raise KeyError(f"Unknown customer_id: {customer_id}")
        session = CallSession(call_id=call_id or new_call_id(), customer_id=customer_id)
        self._sessions[session.call_id] = session
        return session

    def get_session(self, call_id: str) -> CallSession:
        try:
            return self._sessions[call_id]
        except KeyError as exc:
            raise KeyError(f"Unknown call_id: {call_id}") from exc

    def save_session(self, session: CallSession) -> CallSession:
        session.touch()
        self._sessions[session.call_id] = session
        return session

    def mark_verified(self, customer_id: str) -> None:
        self._verified_customers.add(customer_id)

    def clear_verified(self, customer_id: str) -> None:
        self._verified_customers.discard(customer_id)

    def is_verified(self, customer_id: str) -> bool:
        return customer_id in self._verified_customers

    def all_sessions(self) -> Iterable[CallSession]:
        return list(self._sessions.values())

    def record_disposition(self, customer_id: str, disposition: Disposition, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        account = self.get_account(customer_id)
        payload = {
            "timestamp": utc_now(),
            "disposition": disposition.value,
            "details": details or {},
        }
        account.dispositions.append(payload)
        if disposition == Disposition.DO_NOT_CALL:
            account.is_dnc = True
        if disposition == Disposition.ALREADY_PAID:
            account.is_paid = True
        return payload


DB = InMemoryCollectionsDB()
