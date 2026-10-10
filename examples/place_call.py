"""Place an outbound call only if it passes the India pre-call checks.

    export LIVEKIT_URL=... LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=...
    export OUTBOUND_TRUNK_ID=ST_... CALLER_ID=+911600XXXXXX
    python examples/place_call.py 9876543210
"""

import asyncio
import os
import sys

from livekit import api

from livekit_india import CallPurpose, check_call

# Replace with your real DND / NCPR lookup (your DLT operator or telephony
# provider offers one). Return True if the number must not be called.
def is_on_dnd(number: str) -> bool:
    return False


async def main(to_number: str) -> None:
    decision = check_call(
        to_number,
        CallPurpose.SERVICE,  # an appointment reminder to an existing patient
        caller_id=os.environ["CALLER_ID"],
        dnd_check=is_on_dnd,
    )
    for w in decision.warnings:
        print("warning:", w)
    if not decision:
        print("not calling:", "; ".join(decision.reasons))
        return

    async with api.LiveKitAPI() as lk:
        await lk.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=os.environ["OUTBOUND_TRUNK_ID"],
                sip_call_to=decision.destination,
                room_name=f"call-{decision.destination[3:]}",
                participant_identity="callee",
                wait_until_answered=True,
            )
        )
    print("call answered:", decision.destination)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
