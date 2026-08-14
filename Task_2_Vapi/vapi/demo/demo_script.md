# Maya Collections Voicebot — Demo Script
**Agent:** Maya | **Kapture Finance** | Task 2 — Vapi Implementation

## 🎥 Demo Call Recordings
**Recording 1:** https://www.loom.com/share/c52f9dbac73f4e09b6542375d492fae5
**Recording 2:** https://www.loom.com/share/58555bf9f5d2402baf808cc43fcfd284
**Recording 3 (Full 2-3 min):** https://www.loom.com/share/0a40e2ea56344e7281b5c05cd485a7b0

---

## Pre-Demo Checklist
- [ ] Backend server running: `python -m uvicorn backend.server:app --port 8000 --reload`
- [ ] ngrok tunnel active: `ngrok http 8000`
- [ ] Vapi assistant configured with ngrok URL as Server URL
- [ ] Vapi assistant `firstMessage` set to: *"Hello, may I speak with Rahul Sharma please?"*
- [ ] Test account ready: **CUST-1001** | DOB: **04/06/2002**

---

## Demo Paths

| Path | Scenario | Duration | File |
|------|----------|----------|------|
| **Path 1** | Successful PTP (Promise to Pay) | ~1 min | `path_1_successful_ptp.md` |
| **Path 2** | Already Paid + Edge Cases | ~1 min | `path_2_already_paid.md` |
| **Path 3** ⭐ | Full conversation — verification, hardship, payment link, PTP | **~2.5 min** | `path_3_full_2min_conversation.md` |

---

## Key Talking Points for the Reviewer

1. **State-enforced authentication** — the backend blocks all financial data until DOB is verified
2. **DOB-only verification** — no OTP, no password; just date of birth
3. **Tool layer** — every action (verify, PTP log, disposition) hits a real backend endpoint
4. **Low-latency design** — firstMessage, turbo TTS, nova-3 STT, keep-alive Gemini connection
5. **Compliance** — DNC respected, wrong-person handled, hostile caller escalated

---

## Test Credentials

| Customer | ID | DOB | Overdue |
|---|---|---|---|
| Rahul Sharma | CUST-1001 | 04/06/2002 | ₹8,499 (12 days past due) |
| Priya Singh | CUST-1002 | 22/07/1992 | ₹12,840 (4 days past due) |
