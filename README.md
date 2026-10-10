# livekit-india

**Your LiveKit voice agent works in the demo. These are the parts that break
when it meets real Indian phone lines.**

`livekit-india` is a small, tested library for [LiveKit Agents](https://github.com/livekit/agents)
projects that call Indian numbers:

- **Compliance checks before every outbound call:** the 09:00–21:00 IST window for
  promotional calls, DND scrubbing, Indian mobile validation, 140/1600 caller ID
  series, plus an AI-disclosure and recording opening line in English, Hindi and Tamil.
- **Trunk presets for Exotel and Plivo** (and generic guidance for other Indian
  carriers), pinned to LiveKit's India region, with the steps that usually go wrong.
- **Turn-taking defaults for Indian languages:** a Tamil turn model that stays on
  for Tanglish, LiveKit's multilingual model for Hindi, and a shorter wait for
  yes/no answers.

It complements starter kits rather than replacing them. Drop it into the agent
you already have.

## Install

```bash
pip install livekit-india                      # compliance + trunk helpers
pip install "livekit-india[agents,tamil]"      # + turn-taking for Tamil/Hindi
```

## Compliance: check before you dial

```python
from livekit_india import CallPurpose, check_call

decision = check_call(
    "98765 43210",
    CallPurpose.PROMOTIONAL,
    caller_id="+91 140 123 4567",
    dnd_check=my_dnd_lookup,   # your DND/NCPR lookup: number -> True if blocked
)
if not decision:
    print(decision.reasons)    # e.g. "promotional calls are only allowed 09:00-21:00 IST; next window opens ..."
    print(decision.retry_at)   # when you may try again
```

The agent's first words:

```python
from livekit_india import opening_line

await session.say(opening_line("Acme Dental", "ta"))
# வணக்கம், இது Acme Dental சார்பாக அழைக்கும் ஒரு AI உதவியாளர். தரம் மற்றும் பயிற்சிக்காக இந்த அழைப்பு பதிவு செய்யப்படலாம்.
```

## Trunks: keep the call in India

```python
from livekit import api
from livekit_india import outbound_trunk, inbound_trunk, india_sip_uri

india_sip_uri("sip:abc123.sip.livekit.cloud")
# 'sip:abc123.india.sip.livekit.cloud;transport=tcp'  <- give this to your carrier

trunk = outbound_trunk("plivo", name="plivo-out", address="<trunk_id>.zt.plivo.com",
                       numbers=["+918000000000"], auth_username="...", auth_password="...")
# destination_country="in" and TCP are set for you
```

Print a carrier's setup checklist with your URI filled in:

```bash
python examples/setup_trunks.py exotel sip:abc123.sip.livekit.cloud
```

`check_outbound_trunk(trunk)` flags existing trunks that will fail for Indian
calls (missing `destination_country`, non-Indian numbers, and so on).

## Turn-taking: Tamil, Hindi and short answers

```python
from livekit.plugins import silero
from livekit_india import turn_handling, vad_options

session = AgentSession(
    vad=silero.VAD.load(**vad_options("ta")),
    turn_handling=turn_handling("ta", short_answers=True),
    ...
)
```

| Language | Turn detection |
|---|---|
| Tamil | [TamilEOT](https://github.com/santhosh-005/tamil-eot) smart-turn model, kept on when Tanglish is reported as `en-IN` |
| Hindi, English | LiveKit `MultilingualModel` |
| Others | VAD timing (no tested model yet; PRs welcome) |

`short_answers=True` caps the wait after a low-confidence turn at 1.2 s instead
of 2.5 s. Use it for yes/no and slot-picking phases
([background](https://github.com/livekit/agents/issues/6415)).

## The compliance checklist

[docs/DLT_CHECKLIST.md](docs/DLT_CHECKLIST.md) covers DLT registration, consent,
DND, number series and data residency in plain English, with sources.

## Status

Alpha (0.1.0). Tested against `livekit-agents` 1.8.6 and `smart-turn-livekit` 0.4.0:
70 tests, no API keys needed (`pytest`). Rules and carrier details carry their
sources in the code. If you find one out of date, please open an issue.

## Work with me

I'm [Rehan](https://github.com/Rehansanjay), a LiveKit Agents contributor
(12 merged fixes, including the core connection-pool fix
[#7139](https://github.com/livekit/agents/pull/7139)) based in Chennai.

**If your voice agent works in testing but struggles on Indian phone lines**
(carrier setup, compliance, Tamil/Hindi accuracy, turn-taking, latency),
I can help you take it to production.

- Email: rehansanjay28@gmail.com
- LinkedIn: [rehansanjay-venkatesan](https://www.linkedin.com/in/rehansanjay-venkatesan-449925285/)

## License

MIT
