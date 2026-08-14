from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional

from .database.database import DB
from .database.models import AuthenticationStatus, CallSession, CallState, Disposition, Intent
from .services.account_service import get_account_details, get_safe_account_summary
from .services.authentication import authenticate_session, verify_customer
from .services.disposition_service import mark_disposition
from .services.escalation_service import escalate_and_close
from .services.gemini_service import GeminiPlan, call_gemini, gemini_available
from .services.payment_service import log_promise_to_pay, record_already_paid, send_payment_link


class CollectionsOrchestrator:
    """Stateful collections conversation helper that enforces verification before disclosure."""

    NO_INPUT_TRIGGERS = {
        "",
        "voicemail",
        "mailbox",
        "beep",
        "silence",
        "no input",
        "no response",
        "[voicemail]",
    }
    MAX_NO_INPUT_ATTEMPTS = 3
    MAX_HOSTILE_WARNINGS = 1

    def _now_local(self) -> datetime:
        try:
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo("Asia/Kolkata"))
        except Exception:
            return datetime.now(timezone(timedelta(hours=5, minutes=30)))

    def _within_call_window(self) -> bool:
        now = self._now_local().time()
        return time(8, 0) <= now <= time(19, 0)

    def _is_hindi(self, message: str) -> bool:
        text = (message or "").lower()
        hindi_markers = ["नहीं", "हां", "पैसे", "कल", "भुगतान", "मैं", "कर दूँगा", "कर दूंगी"]
        return any(marker in text for marker in hindi_markers)

    def _build_locale_response(self, english_text: str, hindi_text: str, message: str) -> str:
        return hindi_text if self._is_hindi(message) else english_text

    def create_call(self, customer_id: str, call_id: Optional[str] = None) -> Dict[str, Any]:
        session = DB.create_session(customer_id=customer_id, call_id=call_id)
        session.state = CallState.INIT
        DB.save_session(session)
        return session.to_dict()

    def get_call(self, call_id: str) -> Dict[str, Any]:
        return DB.get_session(call_id).to_dict()

    def verify(self, call_id: str, verification_value: str) -> Dict[str, Any]:
        session = DB.get_session(call_id)
        result = authenticate_session(session, verification_value)
        if result["success"]:
            session.state = CallState.AUTHENTICATED
        else:
            session.state = CallState.CALL_ENDED
        DB.save_session(session)
        return result

    def disclose_account(self, call_id: str) -> Dict[str, Any]:
        session = DB.get_session(call_id)
        if session.authentication_status != AuthenticationStatus.VERIFIED:
            raise PermissionError("Verification required before disclosure.")
        session.state = CallState.AUTHENTICATED
        DB.save_session(session)
        return get_account_details(session.customer_id, session)

    def classify_intent(self, message: str) -> Intent:
        text = (message or "").strip().lower()
        if not text:
            return Intent.UNKNOWN
        if any(phrase in text for phrase in ["don't call", "do not call", "stop calling", "unsubscribe"]):
            return Intent.DO_NOT_CALL
        if any(phrase in text for phrase in ["already paid", "paid already", "i paid", "payment done"]):
            return Intent.ALREADY_PAID
        if any(phrase in text for phrase in ["wrong person", "not rahul", "not priya", "wrong number", "not me"]):
            return Intent.WRONG_PERSON if "person" in text or "not me" in text or "not rahul" in text else Intent.WRONG_NUMBER
        if any(phrase in text for phrase in ["can't pay", "cannot pay", "unable to pay", "hardship", "job loss", "no money"]):
            return Intent.HARDSHIP
        if any(phrase in text for phrase in ["dispute", "incorrect", "wrong amount", "not due", "challenge"]):
            return Intent.DISPUTE
        if any(phrase in text for phrase in ["i'll pay", "i will pay", "pay tomorrow", "pay next", "settle", "promise to pay"]):
            return Intent.WILL_PAY
        if any(phrase in text for phrase in ["call me", "callback", "reach me", "ring me", "follow up"]):
            return Intent.CALLBACK_REQUEST
        if any(phrase in text for phrase in ["angry", "stop", "harass", "complaint", "legal"]):
            return Intent.HOSTILE
        return Intent.UNKNOWN

    def _extract_amount(self, message: str, fallback: Optional[float] = None) -> Optional[float]:
        import re

        if fallback is not None:
            return fallback
        match = re.search(r"(\d[\d,]*\.?\d*)", message.replace("₹", " ").replace("$", " "))
        if not match:
            return None
        return float(match.group(1).replace(",", ""))

    def _extract_ptp_date(self, message: str) -> str:
        text = (message or "").lower()
        if "tomorrow" in text:
            return "tomorrow"
        weekdays = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        for day in weekdays:
            if day in text:
                return day.title()
        if "next week" in text:
            return "next week"
        if "today" in text:
            return "today"
        return "next available business day"

    def _is_no_input(self, message: str) -> bool:
        normalized = (message or "").strip().lower()
        return normalized in self.NO_INPUT_TRIGGERS or normalized.startswith("voicemail")

    def _handle_no_input(self, session: CallSession) -> Dict[str, Any]:
        session.no_input_attempts += 1
        if session.no_input_attempts >= self.MAX_NO_INPUT_ATTEMPTS:
            mark_disposition(session.customer_id, Disposition.NO_CONTACT, call_session=session, details={"reason": "voicemail_or_no_input"})
            session.state = CallState.CALL_ENDED
            response = "I couldn't reach anyone after several attempts. I will close this call for now."
        else:
            session.state = CallState.AUTH_PENDING if session.authentication_status == AuthenticationStatus.UNVERIFIED else CallState.NEGOTIATION
            response = "I couldn't hear a response. I'll try again shortly."
        session.last_bot_message = response
        session.add_turn("assistant", response)
        DB.save_session(session)
        return {
            "call_id": session.call_id,
            "response": response,
            "state": session.state.value,
            "disposition": session.disposition.value if session.disposition else None,
            "no_input_attempts": session.no_input_attempts,
        }

    def handle_message(self, call_id: str, message: str) -> Dict[str, Any]:
        session = DB.get_session(call_id)
        account = DB.get_account(session.customer_id)
        session.last_user_message = message
        session.add_turn("user", message)

        if self._is_no_input(message):
            return self._handle_no_input(session)

        session.no_input_attempts = 0

        if not self._within_call_window():
            session.state = CallState.CALL_ENDED
            mark_disposition(session.customer_id, Disposition.NO_CONTACT, call_session=session, details={"reason": "outside_call_window"})
            response = "I’m calling outside permitted hours, so I’ll end this call for now."
            session.last_bot_message = response
            session.add_turn("assistant", response)
            DB.save_session(session)
            return {"call_id": call_id, "response": response, "state": session.state.value, "disposition": session.disposition.value, "language": "en"}

        if account.is_dnc:
            session.state = CallState.CALL_ENDED
            session.disposition = Disposition.DO_NOT_CALL
            DB.save_session(session)
            return {
                "call_id": call_id,
                "response": "I understand. I will not contact you again.",
                "state": session.state.value,
                "disposition": session.disposition.value,
            }

        if session.authentication_status != AuthenticationStatus.VERIFIED:
            session.state = CallState.AUTH_PENDING
            pre_auth_intent = self.classify_intent(message)
            if pre_auth_intent == Intent.HOSTILE and session.hostile_warnings < self.MAX_HOSTILE_WARNINGS:
                session.hostile_warnings += 1
                response = self._build_locale_response(
                    "I understand this is frustrating. Please stay on the line so I can help.",
                    "मैं समझती हूँ कि यह परेशानी भरा है। कृपया लाइन पर बने रहें ताकि मैं मदद कर सकूँ।",
                    message,
                )
                session.last_bot_message = response
                session.add_turn("assistant", response)
                DB.save_session(session)
                return {"call_id": call_id, "response": response, "state": session.state.value, "language": "hi" if self._is_hindi(message) else "en"}
            if pre_auth_intent == Intent.HOSTILE:
                escalate_and_close(session.customer_id, "Hostile caller before verification", call_session=session)
                session.state = CallState.ESCALATED
                DB.save_session(session)
                response = "I’m ending this call now."
                session.last_bot_message = response
                session.add_turn("assistant", response)
                return {"call_id": call_id, "response": response, "state": session.state.value, "disposition": session.disposition.value}
            if pre_auth_intent in {Intent.WRONG_PERSON, Intent.WRONG_NUMBER}:
                escalate_and_close(session.customer_id, "Wrong person or number before verification", call_session=session)
                session.state = CallState.CALL_ENDED
                DB.save_session(session)
                response = "Sorry for the inconvenience. I will end this call."
                session.last_bot_message = response
                session.add_turn("assistant", response)
                return {"call_id": call_id, "response": response, "state": session.state.value, "disposition": session.disposition.value}
            response = self._build_locale_response(
                "Before I discuss the account, I need to verify your identity.",
                "बात आगे बढ़ाने से पहले मुझे आपकी पहचान सत्यापित करनी होगी।",
                message,
            )
            session.last_bot_message = response
            session.add_turn("assistant", response)
            DB.save_session(session)
            return {"call_id": call_id, "response": response, "state": session.state.value}

        intent = self.classify_intent(message)
        session.intent = intent

        if intent == Intent.DO_NOT_CALL:
            mark_disposition(session.customer_id, Disposition.DO_NOT_CALL, call_session=session, details={"message": message})
            session.state = CallState.CALL_ENDED
            response = self._build_locale_response("Understood. I will not contact you again.", "समझ गया। मैं अब आपको संपर्क नहीं करूंगी।", message)
        elif intent == Intent.ALREADY_PAID:
            record_already_paid(session.customer_id, call_session=session, details={"message": message})
            session.state = CallState.CALL_ENDED
            response = self._build_locale_response("Thank you. I have recorded that you already paid.", "धन्यवाद, मैंने आपके भुगतान की जानकारी दर्ज कर ली है।", message)
        elif intent in {Intent.DISPUTE, Intent.HARDSHIP, Intent.HOSTILE}:
            reason = {
                Intent.DISPUTE: "Customer disputed the balance",
                Intent.HARDSHIP: "Customer reported hardship",
                Intent.HOSTILE: "Hostile caller",
            }[intent]
            if intent == Intent.HOSTILE and session.hostile_warnings < self.MAX_HOSTILE_WARNINGS:
                session.hostile_warnings += 1
                session.state = CallState.NEGOTIATION
                response = self._build_locale_response(
                    "I understand this is frustrating. Please stay on the line so I can help.",
                    "मैं समझती हूँ कि यह परेशानी भरा है। कृपया लाइन पर बने रहें ताकि मैं मदद कर सकूँ।",
                    message,
                )
            else:
                escalate_and_close(session.customer_id, reason, call_session=session)
                session.state = CallState.ESCALATED
                response = (
                    "मैं इस मामले को आगे सहायता के लिए भेज रही हूँ।"
                    if self._is_hindi(message)
                    else "I understand. I am escalating this for further assistance."
                )
        elif intent == Intent.CALLBACK_REQUEST:
            session.callback_date = self._extract_ptp_date(message)
            mark_disposition(session.customer_id, Disposition.CALLBACK_REQUESTED, call_session=session, details={"message": message})
            session.state = CallState.CALL_ENDED
            response = self._build_locale_response("Sure. I have recorded your callback request.", "ज़रूर, मैंने आपकी callback request दर्ज कर ली है।", message)
        elif intent == Intent.WILL_PAY:
            amount = self._extract_amount(message, fallback=account.overdue_amount)
            ptp_date = self._extract_ptp_date(message)
            log_promise_to_pay(session.customer_id, amount, ptp_date, call_session=session)
            session.state = CallState.PTP_COLLECTED
            response = self._build_locale_response(
                f"Thank you. I have recorded your promise to pay {amount:.2f} by {ptp_date}.",
                f"धन्यवाद। मैंने {amount:.2f} रुपये {ptp_date} तक भुगतान करने की आपकी प्रतिबद्धता दर्ज कर ली है।",
                message,
            )
        else:
            session.state = CallState.NEGOTIATION
            if gemini_available():
                try:
                    plan = self._gemini_plan(session=session, account=account, message=message, intent_hint=intent)
                    response = plan.response_text
                except Exception:
                    response = f"Thank you for confirming. Your overdue amount is {account.overdue_amount:.2f}. How would you like to proceed?"
            else:
                response = f"Thank you for confirming. Your overdue amount is {account.overdue_amount:.2f}. How would you like to proceed?"

        session.last_bot_message = response
        session.add_turn("assistant", response)
        DB.save_session(session)
        return {
            "call_id": call_id,
            "response": response,
            "state": session.state.value,
            "intent": session.intent.value,
            "disposition": session.disposition.value if session.disposition else None,
            "language": "hi" if self._is_hindi(message) else "en",
        }

    def _gemini_plan(self, session: CallSession, account, message: str, intent_hint: Intent) -> GeminiPlan:
        # Minimal prompt — fewer input tokens means faster first-token latency
        prompt = {
            "customer_name": account.customer_name,
            "overdue": account.overdue_amount,
            "dpd": account.days_past_due,
            "verified": session.authentication_status == AuthenticationStatus.VERIFIED,
            "msg": message,
            "intent": intent_hint.value,
            "state": session.state.value,
        }
        return call_gemini(json.dumps(prompt, separators=(",", ":")))

    def get_metrics(self) -> Dict[str, Any]:
        sessions = list(DB.all_sessions())
        if not sessions:
            return {
                "total_calls": 0,
                "containment_rate": 0.0,
                "ptp_rate": 0.0,
                "fcr_rate": 0.0,
                "auth_success_rate": 0.0,
                "escalation_rate": 0.0,
                "tool_failure_rate": 0.0,
            }

        total_calls = len(sessions)
        verified_calls = sum(1 for s in sessions if s.authentication_status == AuthenticationStatus.VERIFIED)
        ptp_calls = sum(1 for s in sessions if s.disposition == Disposition.PROMISE_TO_PAY)
        escalated_calls = sum(1 for s in sessions if s.disposition == Disposition.ESCALATED)
        valid_dispositions = sum(1 for s in sessions if s.disposition is not None)
        tool_failures = sum(1 for s in sessions if any(event.event_type == "tool_failure" for event in s.tool_events))
        contained_calls = sum(1 for s in sessions if s.disposition not in {Disposition.ESCALATED, Disposition.NO_CONTACT})

        return {
            "total_calls": total_calls,
            "containment_rate": round(contained_calls / total_calls, 3),
            "ptp_rate": round(ptp_calls / total_calls, 3),
            "fcr_rate": round(valid_dispositions / total_calls, 3),
            "auth_success_rate": round(verified_calls / total_calls, 3),
            "escalation_rate": round(escalated_calls / total_calls, 3),
            "tool_failure_rate": round(tool_failures / total_calls, 3),
        }


orchestrator = CollectionsOrchestrator()
app = orchestrator


def create_call(customer_id: str, call_id: Optional[str] = None) -> Dict[str, Any]:
    return orchestrator.create_call(customer_id, call_id=call_id)


def verify_customer_tool(customer_id: str, verification_value: str, call_id: Optional[str] = None) -> Dict[str, Any]:
    session = DB.get_session(call_id) if call_id else None
    return verify_customer(customer_id, verification_value, call_session=session)


def get_account_details_tool(customer_id: str, call_id: Optional[str] = None) -> Dict[str, Any]:
    session = DB.get_session(call_id) if call_id else None
    return get_account_details(customer_id, call_session=session)


def log_promise_to_pay_tool(customer_id: str, amount: Any, ptp_date: str, call_id: Optional[str] = None) -> Dict[str, Any]:
    session = DB.get_session(call_id) if call_id else None
    return log_promise_to_pay(customer_id, amount, ptp_date, call_session=session)


def send_payment_link_tool(customer_id: str, channel: str = "sms") -> Dict[str, Any]:
    return send_payment_link(customer_id, channel=channel)


def escalate_to_agent_tool(customer_id: str, reason: str, call_id: Optional[str] = None) -> Dict[str, Any]:
    session = DB.get_session(call_id) if call_id else None
    return escalate_and_close(customer_id, reason, call_session=session)


def mark_disposition_tool(customer_id: str, disposition: str, call_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    session = DB.get_session(call_id) if call_id else None
    return mark_disposition(customer_id, disposition, call_session=session, details=details)


def get_state_snapshot() -> Dict[str, Any]:
    return {
        "accounts": [account.authenticated_view() for account in DB.list_accounts()],
        "sessions": [session.to_dict() for session in DB.all_sessions()],
    }


def get_metrics_snapshot() -> Dict[str, Any]:
    return orchestrator.get_metrics()


__all__ = [
    "CollectionsOrchestrator",
    "orchestrator",
    "app",
    "create_call",
    "verify_customer_tool",
    "get_account_details_tool",
    "log_promise_to_pay_tool",
    "send_payment_link_tool",
    "escalate_to_agent_tool",
    "mark_disposition_tool",
    "get_state_snapshot",
    "get_metrics_snapshot",
]
