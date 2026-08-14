# Execution Steps

## Local backend

1. Open PowerShell in `Task_2_Vapi/vapi`.
2. Set the Gemini key in your environment.
3. Run:

```powershell
.\submission\run_backend.ps1
```

## Smoke test

In a second terminal:

```powershell
.\submission\smoke_test.ps1
```

## Public exposure

Use ngrok or a similar tunnel to expose port 8000:

```powershell
ngrok http 8000
```

## Vapi dashboard

Use the public HTTPS URL from ngrok and configure:

- Assistant name: `Maya`
- Model: `gemini-2.5-flash`
- Transcriber: `Deepgram nova-2`
- Voice: `ElevenLabs` or `Cartesia`
- Webhooks:
  - `/webhooks/conversation`
  - `/webhooks/agent-handoff`
  - `/health`

## Demo scenarios

- Happy path: verify -> disclose -> PTP -> payment link -> end
- Already paid: verify -> already paid -> disposition
- DNC: request DNC -> stop immediately
- Hostile: warning -> escalate

