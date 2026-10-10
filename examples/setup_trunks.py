"""Print the setup checklist for a carrier, and create India-pinned trunks.

    python examples/setup_trunks.py exotel sip:abc123.sip.livekit.cloud
"""

import sys

from livekit_india import get_carrier

carrier = get_carrier(sys.argv[1] if len(sys.argv) > 1 else "plivo")
project = sys.argv[2] if len(sys.argv) > 2 else None

print(f"{carrier.name}{'' if carrier.verified else '  (generic guidance - confirm with your carrier)'}\n")
for i, step in enumerate(carrier.setup_steps(project), 1):
    print(f"{i}. {step}")
print("\nWatch out for:")
for g in carrier.gotchas:
    print(f"- {g}")

# To create the trunks with the LiveKit API:
#
#   from livekit import api
#   from livekit_india import outbound_trunk, inbound_trunk
#
#   async with api.LiveKitAPI() as lk:
#       await lk.sip.create_outbound_trunk(api.CreateSIPOutboundTrunkRequest(
#           trunk=outbound_trunk("plivo", name="plivo-out", address="<trunk_id>.zt.plivo.com",
#                                numbers=["+91..."], auth_username="...", auth_password="...")))
#       await lk.sip.create_inbound_trunk(api.CreateSIPInboundTrunkRequest(
#           trunk=inbound_trunk(name="plivo-in", numbers=["+91..."])))
