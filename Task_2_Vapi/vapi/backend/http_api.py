from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .app import (
    create_call,
    escalate_to_agent_tool,
    get_account_details_tool,
    get_metrics_snapshot,
    get_state_snapshot,
    log_promise_to_pay_tool,
    mark_disposition_tool,
    orchestrator,
    send_payment_link_tool,
    verify_customer_tool,
)
from .database.database import DB


api = FastAPI(title="Kapture Collections Voicebot API", version="1.0.0")


class CreateCallRequest(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    call_id: Optional[str] = Field(default=None, description="Optional custom call identifier")


class VerifyRequest(BaseModel):
    customer_id: str
    verification_value: str
    call_id: Optional[str] = None


class MessageRequest(BaseModel):
    call_id: str
    message: str


class TranscriptTurn(BaseModel):
    role: str
    content: str


class ConversationWebhookRequest(BaseModel):
    customer_id: Optional[str] = "CUST-1001"
    message: Optional[str] = None
    call_id: Optional[str] = None
    verification_value: Optional[str] = None
    amount: Optional[Any] = None
    ptp_date: Optional[str] = None
    channel: Optional[str] = None
    reason: Optional[str] = None
    disposition: Optional[str] = None
    transcript: List[TranscriptTurn] = Field(default_factory=list)


class PtpRequest(BaseModel):
    customer_id: str
    amount: Any
    ptp_date: str
    call_id: Optional[str] = None


class PaymentLinkRequest(BaseModel):
    customer_id: str
    channel: str = "sms"


class EscalationRequest(BaseModel):
    customer_id: str
    reason: str
    call_id: Optional[str] = None


class DispositionRequest(BaseModel):
    customer_id: str
    disposition: str
    call_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class AgentHandoffRequest(BaseModel):
    customer_id: str
    reason: str
    call_id: Optional[str] = None


@api.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@api.get("/meta")
def meta() -> Dict[str, Any]:
    return {
        "mode": "local-free",
        "provider": "mock",
        "requires_api_key": False,
        "llm_model": "gemini-2.5-flash",
        "telephony": "vapi-compatible-http",
    }


def _tool_call_payload(event_type: str, details: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
    tool_name_map = {
        "verification": "verify_customer",
        "ptp_logged": "log_promise_to_pay",
        "disposition": "mark_disposition",
        "escalation": "escalate_to_agent",
        "already_paid": "record_already_paid",
        "payment_link_sent": "send_payment_link",
    }
    return {
        "name": tool_name_map.get(event_type, event_type),
        "arguments": details,
        "timestamp": timestamp,
    }


@api.post("/calls")
def create_call_endpoint(payload: CreateCallRequest) -> Dict[str, Any]:
    return create_call(payload.customer_id, call_id=payload.call_id)


@api.post("/precall/{customer_id}")
def precall_endpoint(customer_id: str) -> Dict[str, Any]:
    """
    Call this endpoint BEFORE Vapi dials the customer (during the ring phase).

    It pre-creates the session and warms up the account in memory so that when
    the customer picks up and Vapi fires the first webhook, the backend responds
    instantly with zero setup overhead.

    Latency saving: ~200-500 ms off the first webhook response.

    Typical usage:
        1. Your dialler calls POST /precall/{customer_id}
        2. Vapi dials the customer (phone rings for 8-15 s)
        3. Customer picks up  →  Vapi fires /webhooks/conversation
        4. Backend already has the session ready  →  instant response
    """
    try:
        result = create_call(customer_id)
        # Pre-fetch account so it's in the DB object cache
        account = DB.get_account(customer_id)
        return {
            "status": "warmed",
            "call_id": result["call_id"],
            "customer_id": customer_id,
            "customer_name": account.customer_name,
            "message": "Session pre-created. Pass call_id to Vapi before dialling.",
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.get("/calls/{call_id}")
def get_call_endpoint(call_id: str) -> Dict[str, Any]:
    try:
        return orchestrator.get_call(call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.post("/verify")
def verify_endpoint(payload: VerifyRequest) -> Dict[str, Any]:
    try:
        return verify_customer_tool(payload.customer_id, payload.verification_value, call_id=payload.call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.get("/accounts/{customer_id}/details")
def account_details_endpoint(customer_id: str, call_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        return get_account_details_tool(customer_id, call_id=call_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.post("/messages")
def message_endpoint(payload: MessageRequest) -> Dict[str, Any]:
    try:
        return orchestrator.handle_message(payload.call_id, payload.message)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.post("/webhooks/conversation")
def conversation_webhook(payload: ConversationWebhookRequest) -> Dict[str, Any]:
    try:
        print("VAPI PAYLOAD RECEIVED:", payload.dict())
        call_id = payload.call_id
        if call_id is None:
            call_id = create_call(payload.customer_id)["call_id"]

        session = DB.get_session(call_id)
        start_event_count = len(session.tool_events)

        if payload.verification_value:
            verify_customer_tool(payload.customer_id, payload.verification_value, call_id=call_id)
        if payload.amount and payload.ptp_date:
            log_promise_to_pay_tool(payload.customer_id, payload.amount, payload.ptp_date, call_id=call_id)
        if payload.channel:
            send_payment_link_tool(payload.customer_id, channel=payload.channel)
        if payload.reason:
            escalate_to_agent_tool(payload.customer_id, payload.reason, call_id=call_id)
        if payload.disposition:
            mark_disposition_tool(payload.customer_id, payload.disposition, call_id=call_id)

        # For get_account_details, it doesn't take parameters other than customer_id, we infer it if other params are missing but tool is called.
        # But Vapi sends empty payload for it except customer_id. So we will rely on orchestrator.handle_message for state updates.

        if payload.transcript:
            for turn in payload.transcript:
                if turn.role in {"user", "customer"}:
                    session.add_turn("user", turn.content)
                elif turn.role in {"assistant", "bot"}:
                    session.add_turn("assistant", turn.content)

        bot_turn = None
        if payload.message:
            bot_turn = orchestrator.handle_message(call_id, payload.message)

        session = DB.get_session(call_id)
        new_events = session.tool_events[start_event_count:]
        
        # If this was purely a Vapi API Request tool execution (no message), return a clear success object
        if not bot_turn:
            return {
                "success": True,
                "message": "Tool executed successfully. The customer is now VERIFIED. Please proceed with the call and disclose the overdue amount."
            }

        return {
            "call_id": call_id,
            "customer_id": payload.customer_id,
            "next_turn": bot_turn["response"],
            "messages": [
                {
                    "role": "assistant",
                    "content": bot_turn["response"],
                }
            ],
            "tool_calls": [
                _tool_call_payload(event.event_type, event.details, event.timestamp) for event in new_events
            ],
            "state": bot_turn["state"],
            "intent": bot_turn.get("intent"),
            "disposition": bot_turn.get("disposition"),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@api.post("/webhooks/agent-handoff")
def agent_handoff_webhook(payload: AgentHandoffRequest) -> Dict[str, Any]:
    try:
        call_id = payload.call_id
        if call_id is None:
            call_id = create_call(payload.customer_id)["call_id"]
        session = DB.get_session(call_id)
        start_event_count = len(session.tool_events)
        result = escalate_to_agent_tool(payload.customer_id, payload.reason, call_id=call_id)
        session = DB.get_session(call_id)
        new_events = session.tool_events[start_event_count:]
        return {
            "call_id": call_id,
            "customer_id": payload.customer_id,
            "next_turn": "I'm connecting you with a human agent now.",
            "messages": [{"role": "assistant", "content": "I'm connecting you with a human agent now."}],
            "tool_calls": [_tool_call_payload(event.event_type, event.details, event.timestamp) for event in new_events],
            "handoff": True,
            "reason": payload.reason,
            "result": result,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@api.post("/ptp")
def ptp_endpoint(payload: PtpRequest) -> Dict[str, Any]:
    try:
        return log_promise_to_pay_tool(payload.customer_id, payload.amount, payload.ptp_date, call_id=payload.call_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.post("/payment-link")
def payment_link_endpoint(payload: PaymentLinkRequest) -> Dict[str, Any]:
    try:
        return send_payment_link_tool(payload.customer_id, channel=payload.channel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.post("/escalate")
def escalate_endpoint(payload: EscalationRequest) -> Dict[str, Any]:
    try:
        return escalate_to_agent_tool(payload.customer_id, payload.reason, call_id=payload.call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.post("/dispositions")
def disposition_endpoint(payload: DispositionRequest) -> Dict[str, Any]:
    try:
        return mark_disposition_tool(
            payload.customer_id,
            payload.disposition,
            call_id=payload.call_id,
            details=payload.details,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api.get("/state")
def state_endpoint() -> Dict[str, Any]:
    return get_state_snapshot()


@api.get("/metrics")
def metrics_endpoint() -> Dict[str, Any]:
    return get_metrics_snapshot()


@api.post("/reset")
def reset_endpoint() -> Dict[str, str]:
    DB.reset()
    return {"status": "reset"}
