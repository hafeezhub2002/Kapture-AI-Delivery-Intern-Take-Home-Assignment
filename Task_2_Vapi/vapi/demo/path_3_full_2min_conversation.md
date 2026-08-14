# Path 3 — Full 2-3 Minute Conversation (Complete Demo Path)

**Customer:** Rahul Sharma | **CUST-1001** | Overdue: ₹8,499 | 12 days past due
**Verification DOB:** 04/06/2002
**Estimated duration:** ~2.5 minutes when spoken at natural pace

---

## Full Conversation Script

```
────────────────────────────────────────────────
 CALL CONNECTS
────────────────────────────────────────────────

MAYA:     Hello, may I speak with Rahul Sharma please?

CUSTOMER: Yes, who is this?

MAYA:     Hi Rahul, this is Maya calling from Kapture Finance.
          I hope I am not disturbing you. I am calling regarding
          your loan account. Before I share any details, I need
          to quickly verify your identity. Could you please
          confirm your date of birth?

CUSTOMER: Why do you need my date of birth?

MAYA:     It is just a quick security check to make sure I am
          speaking with the right person, Rahul. We do this to
          protect your account information. Could you please
          confirm your date of birth?

CUSTOMER: Fine. It is 4th June 2002.

          [Backend: verify_customer → DOB matched → VERIFIED ✅]
          [State: AUTH_PENDING → AUTHENTICATED]

MAYA:     Thank you, Rahul. I have verified your identity.
          I am calling about your personal loan account.
          There is an overdue EMI of ₹8,499 which is now
          12 days past its due date. I wanted to check in
          and see how we can help you clear this.

────────────────────────────────────────────────
 NEGOTIATION PHASE
────────────────────────────────────────────────

CUSTOMER: ₹8,499? I did not realise it had been that long.
          I have been very busy with work lately.

MAYA:     I completely understand, Rahul. Things get busy
          and these things can slip through. The important
          thing is we sort it out now to avoid any impact
          on your credit score. Is there a date that works
          for you to make the payment?

CUSTOMER: Honestly, things are a bit tight right now
          financially. I am not sure I can pay the full
          amount immediately.

          [Intent detected: HARDSHIP]

MAYA:     I hear you, Rahul, and I appreciate your honesty.
          Would you be able to make even a partial payment
          now and clear the rest by the end of the week?
          Or if you would prefer, I can share a payment
          link directly to your phone so it is easy to
          pay whenever you are ready.

CUSTOMER: A payment link would actually be helpful.
          Can you send it to my phone?

          [Backend: send_payment_link → channel=sms ✅]

MAYA:     Of course. I have just sent a secure payment link
          to your registered mobile number. You will receive
          it in a moment. The link is valid for 48 hours.

────────────────────────────────────────────────
 COMMITMENT PHASE
────────────────────────────────────────────────

CUSTOMER: Okay, good. I think I can pay by Friday.

          [Intent detected: WILL_PAY]
          [Backend: log_promise_to_pay → amount=8499, date=Friday ✅]

MAYA:     That is great, Rahul. I have recorded your commitment
          to pay ₹8,499 by Friday. You can use the payment
          link I just sent, or pay directly through the
          Kapture Finance app. Is there anything else I
          can help you with today?

CUSTOMER: No, that should be fine. Thanks for being
          understanding about it.

MAYA:     Absolutely, Rahul. Thank you for taking the time
          to speak with me today. We will follow up if
          the payment is not received by Friday.
          I hope the rest of your day goes well. Goodbye.

          [Backend: mark_disposition → PROMISE_TO_PAY ✅]

CUSTOMER: Thanks. Bye.

────────────────────────────────────────────────
 CALL ENDS
────────────────────────────────────────────────
```

---

## Timeline Breakdown (~2.5 minutes)

| Time | Phase | What happens |
|---|---|---|
| 0:00 – 0:20 | **Greeting** | Maya introduces, asks to speak with Rahul |
| 0:20 – 0:50 | **Verification** | Customer pushes back, then provides DOB |
| 0:50 – 1:15 | **Disclosure** | Maya reveals overdue amount after verification |
| 1:15 – 1:45 | **Negotiation** | Customer mentions hardship, Maya empathises |
| 1:45 – 2:10 | **Payment link** | Customer asks for SMS link, Maya sends it |
| 2:10 – 2:30 | **PTP commitment** | Customer commits to Friday payment |
| 2:30 – 2:45 | **Closing** | Warm close, disposition logged |

---

## Backend Events Triggered (show in logs)

```
✅ verify_customer       → success=True, matched_token="4 june 2002"
✅ get_account_details   → overdue=8499, days_past_due=12
✅ send_payment_link     → channel=sms, customer_id=CUST-1001
✅ log_promise_to_pay   → amount=8499.0, ptp_date=Friday
✅ mark_disposition      → PROMISE_TO_PAY
```

---

## Tips for Recording This Demo

1. **Pause naturally** between each line — Maya needs ~1-2s to process and respond
2. **Push back on the DOB question** — this shows Mayas handling of hesitation
3. **Mention hardship** — this shows the empathetic negotiation path
4. **Ask for a payment link** — this triggers the send_payment_link tool
5. **Commit to Friday** — this triggers log_promise_to_pay + disposition
6. Keep your tone natural and conversational — it makes the demo more realistic
