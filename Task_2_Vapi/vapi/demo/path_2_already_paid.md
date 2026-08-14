# Path 2 — Already Paid

**Customer:** Rahul Sharma | **CUST-1001**
**Verification DOB:** 04/06/2002

---

## Full Conversation

```
MAYA:     Hello, may I speak with Rahul Sharma please?

CUSTOMER: Yes, this is Rahul.

MAYA:     Hi Rahul, this is Maya calling from Kapture Finance.
          Before I proceed, I need to verify your identity.
          Could you please confirm your date of birth?

CUSTOMER: Fourth of June, 2002.

          [Backend: POST /verify → DOB matched → VERIFIED ✅]

MAYA:     Thank you, Rahul. I am calling about an overdue EMI of
          ₹8,499 on your personal loan. The amount has been
          outstanding for 12 days.

CUSTOMER: I already paid that last week.

          [Backend: record_already_paid for CUST-1001 ✅]

MAYA:     Thank you for letting me know, Rahul. I have recorded
          that you have already made the payment. Our team will
          verify this and update your account accordingly.
          Apologies for any inconvenience. Have a good day.

          [Backend: mark_disposition → ALREADY_PAID ✅]

CUSTOMER: Okay, thanks.

MAYA:     You are welcome, Rahul. Take care. Goodbye.
```

---

## What the Reviewer Should See

| Step | Expected Backend Log |
|---|---|
| Customer confirms DOB | `verification: success=True, attempts=1` |
| Customer says already paid | `intent: ALREADY_PAID` |
| Backend records it | `record_already_paid: customer_id=CUST-1001` |
| Call ends | `disposition: ALREADY_PAID` |

---

## Additional Edge-Case Paths to Demo (Optional)

### Wrong Person
```
MAYA:     Hello, may I speak with Rahul Sharma please?
CUSTOMER: Sorry, wrong number. I am not Rahul.
MAYA:     I apologise for the inconvenience. I will end this call now.
          [disposition: WRONG_NUMBER — no financial info disclosed ✅]
```

### Do Not Call
```
CUSTOMER: Stop calling me. Do not contact me again.
MAYA:     I understand. I have noted your request and will
          not contact you again. Goodbye.
          [disposition: DO_NOT_CALL — DNC flag set on account ✅]
```

### Authentication Failure
```
MAYA:     Could you please confirm your date of birth?
CUSTOMER: January 1st 1990.
          [Backend: DOB does not match → FAILED]
MAYA:     I am sorry, I could not verify your identity with
          that date of birth. Could you please try again?
CUSTOMER: [wrong again]
MAYA:     I am unable to verify your identity. I will end this
          call for security reasons. Goodbye.
          [disposition: AUTHENTICATION_FAILED ✅]
```
