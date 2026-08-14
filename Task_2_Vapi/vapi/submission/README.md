# Task 2 Submission: Kapture Collections Voicebot (Vapi)

This is the completed Task 2 implementation for the Maya Collections Voicebot using Vapi.

## 🎥 Demo Call Recordings
- **Recording 1:** https://www.loom.com/share/c52f9dbac73f4e09b6542375d492fae5
- **Recording 2:** https://www.loom.com/share/58555bf9f5d2402baf808cc43fcfd284
- **Recording 3 (Full 2.5 min conversation):** https://www.loom.com/share/0a40e2ea56344e7281b5c05cd485a7b0

## 📝 Required Files Included
- **System Prompt:** `final_system_prompt.txt`
- **Tool Schemas:** `final_tool_schemas.json`
- **Full Backend Code:** Located in `../backend/` directory

---

## 1. Setup & Running the Code

The backend is built with FastAPI and runs completely locally without requiring external API keys for core state-machine functionality (it mocks LLM orchestration if Gemini is unavailable).

**Steps:**
1. Open the `vapi` directory in your terminal.
2. Install requirements: `pip install -r backend/requirements.txt`
3. Run the server: `python -m uvicorn backend.server:app --port 8000 --reload`
4. Expose via ngrok: `ngrok http 8000`
5. Configure your Vapi assistant to point to: `https://<your-ngrok-url>/webhooks/conversation`

---

## 2. Design Choices & Implementation Details

1. **State-Enforced Authentication (DOB-only)**
   The system prompt explicitly instructs Maya to *only* ask for the Date of Birth (no OTPs). The backend absolutely blocks any financial disclosure until `verify_customer` is successfully executed.
2. **First-Message Latency Optimisation**
   I used `firstMessageMode: "assistant-speaks-first"` with a hardcoded `firstMessage` ("Hello, may I speak with Rahul Sharma please?"). This completely bypasses the 2-3 second latency of a first-turn LLM generation.
3. **Backend-Driven Dispositions**
   The conversation does not rely entirely on the LLM to decide when the call is over. It uses strict server-side state enforcement (e.g., `WILL_PAY` logs a Promise-To-Pay and instantly flags the disposition as `PROMISE_TO_PAY`).
4. **Fast Tooling & Warm Starts**
   I added a `lifespan` handler to `server.py` to pre-seed the database and open persistent HTTP/TLS connections so the very first webhook from Vapi responds instantly.

---

## 3. What Broke & How I Debugged It

1. **Initial 20-30s Connect Latency:**
   - **Issue:** Vapi took almost 30 seconds to start talking to the customer.
   - **Debugging:** I profiled the connection flow and realised the delay was a mix of PSTN dial-out time (unavoidable ringing), cold-start Python server latency, and Vapi's first-turn LLM latency.
   - **Fix:** Added `firstMessage` to the Vapi config, switched STT to `nova-3`, TTS to `eleven_turbo_v2`, and added a `/precall/{customer_id}` endpoint to pre-warm the Python backend before the phone even finishes ringing. This reduced our control-side latency to under 1-2s.

2. **Authentication Override Bypass:**
   - **Issue:** The initial mock backend had `success = True` hardcoded, meaning any random string provided as DOB would verify the user.
   - **Fix:** Implemented full token matching in `database.py` mapping multiple variations of DOB ("4 June 2002", "04/06/2002", "2002") to Rahul's profile.

---

## 4. What I’d Improve with More Time

1. **Bilingual Hindi/English Switching:**
   I'd add a robust language detection middleware that updates the STT model dynamically via Vapi's `update` messages if the user starts speaking Hindi.
2. **Persistent Datastore (Postgres):**
   Right now, the session and customer data live in memory (`temp_store.py`). I'd migrate this to a real relational database for persistence and robust concurrency.
3. **Automated Evals Framework:**
   I'd write a Playwright/Pytest script to simulate thousands of call trajectories programmatically against the `/webhooks/conversation` endpoint to measure the exact containment, verification failure, and PTP success rates.
