# SMS delivery: what it would actually take

Today LIFELINE generates the message and refuses to pretend it left the building.
`escalation.notifications()` builds every tier-2 and tier-4 payload for three
channels (SMS, WhatsApp, voice call), model-drafted where possible, validated in
code, and every row carries:

```json
"status": "PENDING_CREDENTIALS",
"note": "no SMS/WhatsApp/voice gateway configured - payload generated and logged only"
```

That is deliberate. There is no gateway on this machine, no sender ID, and no
credential in the repo. Turning `PENDING_CREDENTIALS` into `SENT` is a carrier
onboarding problem, not a coding problem. This note records what each route
costs in time and money, so the decision is explicit rather than accidental.

## What a send needs

1. **An account** with a provider (or a SIM).
2. **A sender identity** the carrier accepts: a Twilio number, a WhatsApp
   business number, or an alphanumeric header.
3. **A recipient that consented**, for anything but a trial sandbox.
4. **For Indian mobile numbers: DLT registration.** This is the blocker people
   discover late.

## The routes, honestly compared

| Route | Setup time | Real cost | Works for Tamil Nadu numbers | Notes |
| --- | --- | --- | --- | --- |
| **Meta WhatsApp Cloud API** | ~1 hour to a working test number | Free sandbox; per-message pricing once live | Yes, no DLT needed | Closest fit: Meta-owned, already a `whatsapp` channel in the ladder, template messages are pre-approved by Meta rather than TRAI. Sandbox sends only to numbers you verify. |
| **Twilio (SMS)** | ~1 hour to trial | Trial credit, then per-segment | Yes, **but** India needs DLT | Best-documented API, worst India paperwork. Trial messages are prefixed "Sent from your Twilio trial account". |
| **Vonage / Infobip / Karix** | 1-3 days (KYC) | Per-message + monthly | Yes, with DLT | Enterprise route. Karix and Gupshup handle DLT on your behalf; that is what the fee buys. |
| **Fast2SMS / MSG91** | Hours, if DLT entity already exists | Cheapest per SMS in India | Yes, DLT required | Indian aggregators. They will reject traffic without an approved template. |
| **Africa's Talking** | ~1 day | Per-message | Not for India | Good if the pilot moves to Kenya/Tanzania, where the Swahili locale matters. Shortcodes need local KYC. |
| **Local Android gateway** (e.g. an SMS gateway app on a spare phone) | ~30 minutes | The SIM's plan | Yes | No DLT, because it is person-to-person SMS. Not auditable, not a service, phone must stay awake. Fine for a field pilot, not for a product claim. |
| **GSM modem / SIM800** | ~1 day of hardware | The SIM's plan | Yes | Same P2P loophole, worse reliability. |
| **Email-to-SMS gateways** | Minutes | Free | Mostly dead | Carriers have retired them. Do not build on this. |

## The India DLT constraint, in one paragraph

A2P SMS to Indian numbers requires registering the **entity** (your
organisation), a **header** (the 6-character sender ID), and each **template**
(the exact wording, with `{#var#}` placeholders). Unregistered traffic is
dropped by the operator, usually silently. Templates are reviewed, so a message
that changes wording at runtime - which is exactly what a model-drafted alert
does - must be reduced to a fixed template with variables. That is a
one-to-three-day loop on a good day. It cannot be done during a hackathon
weekend, and it cannot be faked.

WhatsApp Cloud API sidesteps DLT because Meta approves the template, not TRAI.
That is why it is the recommended route for this project.

## What I would wire, and what I would not claim

The adapter should live behind one function so nothing else changes:

```python
# delivery.py (not committed - needs credentials)
def send(payload: dict) -> dict:
    """Return {'status': ..., 'provider_id': ..., 'note': ...}.

    PENDING_CREDENTIALS  no token in the environment - nothing was dialled
    QUEUED               provider accepted the request
    SENT                 provider returned a message id
    FAILED               provider returned an error; the error is kept verbatim
    """
```

Rules the adapter must obey, matching how the rest of this repo behaves:

- **`SENT` only with a provider message id.** A 200 with no id is `QUEUED`.
- **No token in the repo, ever.** `META_WHATSAPP_TOKEN`, `TWILIO_AUTH_TOKEN`,
  and friends go in `.env`, which is already git-ignored.
- **Delivery never blocks the decision.** The allocator seals the hash-chained
  ledger entry first; the send is a side effect with its own status field.
- **Offline is still the demo.** With `LIFELINE_OFFLINE=1` the adapter must
  short-circuit to `PENDING_CREDENTIALS` and the UI must still show the drafted
  message. The `runs offline` badge stays true.
- **The artefact tells the truth.** `artifacts/escalation.json` keeps one row per
  recipient with the status actually returned.

## Recommendation for the remaining days

1. **Do not chase DLT before the deadline.** It is a paperwork loop with an
   unknown finish line, and the judges see the video, not a phone.
2. **If a live send is wanted for the video**, use the WhatsApp Cloud API test
   number to one verified phone you own. That is one hour, free, and produces a
   genuinely delivered message with a real timestamp. Record it as "WhatsApp
   Cloud API test number", not "SMS to the panchayat".
3. **Keep the offline path as the headline.** The product's claim is that the
   decision and the message are computed with no network; delivery is a
   transport detail that queues when the link returns.
4. **Say the limitation in the README** - `PENDING_CREDENTIALS` is already
   visible in the artefact and the UI, which is the honest version of "not
   wired yet".

## What is already true in the repo

- `escalation.notifications(tier, town, locale)` returns one payload per
  channel per recipient, in the reader's language and direction (`dir`).
- Model-drafted SMS bodies are validated in `multilingual.validate_body`:
  at most 160 characters, must contain the required numbers, reviewed by a
  second model pass.
- The tier-2 spoken script is rendered locally by MMS-TTS and referenced only
  when the `.wav` exists on disk.
- `artifacts/multilingual_payloads.json` holds 8 locales × 3 payload kinds, so
  the adapter has real bodies to send the day credentials exist.
