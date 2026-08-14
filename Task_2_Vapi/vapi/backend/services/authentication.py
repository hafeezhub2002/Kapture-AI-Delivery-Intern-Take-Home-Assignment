from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from ..database.database import DB
from ..database.models import AuthenticationStatus, CallSession
from .utils.logger import log_event


@dataclass
class VerificationResult:
    success: bool
    customer_id: str
    matched_token: Optional[str] = None
    attempts: int = 0
    message: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "success": self.success,
            "customer_id": self.customer_id,
            "matched_token": self.matched_token,
            "attempts": self.attempts,
            "message": self.message,
        }


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def verify_customer(
    customer_id: str,
    verification_value: str,
    call_session: Optional[CallSession] = None,
    call_id: Optional[str] = None,
) -> Dict[str, object]:
    if call_session is None and call_id is not None:
        call_session = DB.get_session(call_id)
    account = DB.get_account(customer_id)
    normalized = _normalize(verification_value)
    attempt_count = 0 if call_session is None else call_session.verification_attempts + 1
    matched = next((token for token in account.verification_tokens if _normalize(token) == normalized), None)
    success = matched is not None  # Verified only if the supplied DOB matches a registered token

    if call_session is not None:
        call_session.verification_attempts = attempt_count
        call_session.authentication_status = AuthenticationStatus.VERIFIED if success else AuthenticationStatus.FAILED
        call_session.add_event("verification", {"success": success, "attempts": attempt_count})
        if success:
            DB.mark_verified(customer_id)
        else:
            DB.clear_verified(customer_id)
        DB.save_session(call_session)
    else:
        if success:
            DB.mark_verified(customer_id)

    result = VerificationResult(
        success=success,
        customer_id=customer_id,
        matched_token=matched,
        attempts=attempt_count,
        message="Identity verified." if success else "Verification failed. Please check your date of birth and try again.",
    )
    return result.to_dict()


def authenticate_session(call_session: CallSession, verification_value: str) -> Dict[str, object]:
    result = verify_customer(call_session.customer_id, verification_value, call_session=call_session)
    if result["success"]:
        call_session.authentication_status = AuthenticationStatus.VERIFIED
    else:
        call_session.authentication_status = AuthenticationStatus.FAILED
    DB.save_session(call_session)
    return result


def is_verified(call_session: CallSession) -> bool:
    return call_session.authentication_status == AuthenticationStatus.VERIFIED


def is_customer_verified(customer_id: str) -> bool:
    return DB.is_verified(customer_id)
