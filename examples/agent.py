"""A Tamil receptionist agent with India-ready defaults.

    pip install "livekit-india[agents,tamil]" "livekit-agents[sarvam]"
    export SARVAM_API_KEY=...
    python examples/agent.py console      # talk through your mic
    python examples/agent.py dev          # take real calls via LiveKit SIP
"""

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import sarvam, silero

from livekit_india import opening_line, turn_handling, vad_options

LANGUAGE = "ta"
BUSINESS = "Acme Dental"

INSTRUCTIONS = """You are the receptionist at a dental clinic in Chennai.
Speak Tamil; the caller may mix in English words. Book appointments by asking
one short question at a time. Keep every reply under two sentences."""


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    session = AgentSession(
        vad=silero.VAD.load(**vad_options(LANGUAGE)),
        stt=sarvam.STT(language="unknown"),  # auto-detect, so Tanglish works
        llm=sarvam.LLM(model="sarvam-105b"),
        tts=sarvam.TTS(target_language_code="ta-IN"),
        # booking is mostly yes/no and slot picks, so cap the wait on short answers
        turn_handling=turn_handling(LANGUAGE, short_answers=True),
    )
    await session.start(agent=Agent(instructions=INSTRUCTIONS), room=ctx.room)
    # AI disclosure + recording notice before anything else
    await session.say(opening_line(BUSINESS, LANGUAGE))


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
