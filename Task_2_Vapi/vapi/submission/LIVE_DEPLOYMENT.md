# Live Deployment Guide

This repo is now code-ready for a live voice stack. The last steps require your Vapi account, a public tunnel, and your own dashboard access.

## 1. Environment Variables

Create a local `.env` for the backend:

```bash
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash
HOST=127.0.0.1
PORT=8000
```

## 2. Start the backend

```bash
uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload
```

## 3. Expose the webhook publicly

Use ngrok or a similar tunnel:

```bash
ngrok http 8000
```

Copy the public HTTPS URL and append the webhook paths from this project:

- `/webhooks/conversation`
- `/webhooks/agent-handoff`
- `/health`

## 4. Configure Vapi

In the Vapi dashboard:

- Create a blank assistant named `Maya`
- Set the assistant to use your public webhook URL
- Configure the assistant tools to call this backend
- Use the same tool names as in `assistant_config.json`

Recommended voice pipeline:

- Transcriber: Deepgram Nova-2
- Voice: ElevenLabs or Cartesia
- Model: Gemini 2.5 Flash for planning/response generation

## 5. Tool mapping

Map Vapi tool calls to these endpoints:

- `verify_customer` -> verification step
- `log_promise_to_pay` -> PTP capture
- `send_payment_link` -> payment link dispatch
- `escalate_to_agent` -> human handoff
- `mark_disposition` -> final disposition

## 6. Demo flow

Use these scenarios in the live call:

1. Happy path
   - Verify identity
   - Reveal debt only after auth
   - Capture promise to pay
   - Send payment link
   - End with `PROMISE_TO_PAY`

2. Already paid
   - Verify identity
   - Customer says they already paid
   - Mark disposition `ALREADY_PAID`
   - Close politely

3. DNC
   - Customer requests no more calls
   - Mark disposition `DO_NOT_CALL`
   - End immediately

## 7. Recording

Record the call with Loom, OBS, or Zoom once the Vapi assistant is connected to the public webhook.

## 8. Why this repo is ready

The backend already provides:

- verification gating
- stateful conversation handling
- PTP logging
- payment-link dispatch
- disposition logging
- escalation
- metrics
- redacted event logging
- live webhook payloads

