# Path 1 — Successful Promise to Pay (PTP)

**Customer:** Rahul Sharma | **CUST-1001** | Overdue: ₹8,499 | 12 days past due
**Verification DOB:** 04/06/2002 (say: "4th June 2002" or "4 June 2002")

---

## Full Conversation

```
MAYA:     Hello, may I speak with Rahul Sharma please?

CUSTOMER: Yes, speaking.

MAYA:     Hi Rahul, this is Maya calling from Kapture Finance.
          Before I proceed, I need to verify your identity.
          Could you please confirm your date of birth?

CUSTOMER: 4th June 2002.

          [Backend: POST /verify → DOB matched → VERIFIED ✅]

MAYA:     Thank you for confirming, Rahul. I am calling regarding
          your personal loan account. There is an overdue EMI of
          ₹8,499 that is 12 days past due. How would you like to
          proceed?

CUSTOMER: I will pay tomorrow.

          [Backend: log_promise_to_pay → amount=8499, date=tomorrow ✅]

MAYA:     That is great, Rahul. I have recorded your commitment to
          pay ₹8,499 by tomorrow. You will receive a payment link
          shortly. Thank you, and have a good day.

          [Backend: mark_disposition → PROMISE_TO_PAY ✅]

CUSTOMER: Thank you. Bye.

MAYA:     Goodbye, Rahul. Take care.
```

---

## What the Reviewer Should See

| Step | Expected Backend Log |
|---|---|
| Customer confirms identity | `verification: success=True, attempts=1` |
| Maya discloses amount | `get_account_details called for CUST-1001` |
| Customer says will pay | `ptp_logged: amount=8499, date=tomorrow` |
| Call ends | `disposition: PROMISE_TO_PAY` |

---

## Security Test (Bonus — show this)

> Before verifying DOB, ask: *"How much do I owe?"*

```
CUSTOMER: How much do I owe?

MAYA:     Before I can share any account details, I need to verify
          your identity first. Could you please confirm your date
          of birth?
```

**This proves the state-enforcement works — the amount is NEVER disclosed before verification.**
