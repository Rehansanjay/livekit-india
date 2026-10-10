# Taking an AI voice agent live in India: compliance checklist

Plain-English notes for developers. Not legal advice: rules change, and your
DLT operator and telephony provider have the final word.

## 1. Decide what kind of call it is

| Purpose | Examples | Time limits | DND applies? | Caller ID series |
|---|---|---|---|---|
| Promotional | Sales, offers, lead follow-up | 09:00–21:00 IST only | Yes, scrub every campaign | 140 |
| Transactional | OTPs, delivery and order updates | None | No | 1600 |
| Service | Reminders and updates to existing customers | None | Partly, depending on consent | 1600 |

`check_call()` enforces the time window, the DND requirement and the Indian
mobile format, and warns when the caller ID series doesn't match the purpose.

## 2. Register before you dial

- [ ] Register your business as a **Principal Entity** on a DLT platform.
- [ ] Your telephony provider (or AI calling platform) must be registered as
      your **telemarketer** and linked to your Principal Entity.
- [ ] Get **140-series** numbers for promotional calls and **1600-series**
      numbers for transactional and service calls from your provider.

## 3. Consent and DND

- [ ] Record consent with a timestamp and purpose. Broad terms-and-conditions
      consent does not automatically cover a promotional campaign (DPDP Act 2023).
- [ ] Scrub promotional lists against the DND / NCPR registry **close to dialling
      time**. A scrub done weeks before the campaign doesn't count.
- [ ] Honour opt-outs within 7 days.

## 4. What the agent says first

- [ ] Say that it's an AI calling on behalf of your business. A 2026 TRAI draft
      amendment proposes making this mandatory; `opening_line()` does it in
      English, Hindi and Tamil.
- [ ] If you record calls, say so up front. `opening_line(recorded=True)` adds it.

## 5. Keep the call in India

- [ ] Point inbound trunks at LiveKit's India endpoint (`india_sip_uri()`).
- [ ] Set `destination_country="in"` on outbound trunks (`outbound_trunk()` does it).
- [ ] On Plivo, create the organization in the India data region (hangup code
      4590 means media left India).
- [ ] Ask your carrier to allow-list LiveKit's India egress ranges
      (`LIVEKIT_INDIA_EGRESS_CIDRS`). Outbound calls that time out with no SIP
      response usually mean this step is missing.

## Penalties to know about

- Calling DND-registered numbers with unsolicited promotional calls: up to
  ₹1,000 per call per day.
- Seven or more complaints in a month: telecom resources can be disconnected
  for up to two years.
- Repeated violations can get your Principal Entity deregistered, which blocks
  your numbers across every operator.

## Sources

- TCCCPR 2018 summary, Exotel developer docs: https://developer.exotel.com/docs/faqs/tcccpr-2018
- TRAI regulation (Feb 2025 amendment): https://www.trai.gov.in/sites/default/files/2025-02/Regulation_12022025.pdf
- AI outbound rules overview: https://www.squadstack.ai/en/blog/is-ai-voice-calling-trai-compliant-outbound-rules-in-india
- DLT and AI calling: https://caller.digital/blog/trai-dlt-compliance-ai-outbound-calling-india-2026
- LiveKit region pinning: https://docs.livekit.io/telephony/features/region-pinning/
- Plivo calling in India: https://www.plivo.com/docs/voice-agents/sip-trunking/deploy/calling-in-india
