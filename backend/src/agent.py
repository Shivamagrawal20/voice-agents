import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
    metrics,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

CONTENT_PATH = Path(__file__).resolve().parents[2] / "shared-data" / "day4_tutor_content.json"

DEFAULT_CONTENT = [
    {
        "id": "variables",
        "title": "Variables",
        "summary": "Variables store values so you can reuse them later. They act like labeled boxes so your program can retrieve or change the value whenever needed.",
        "sample_question": "What is a variable and why is it useful?",
    },
    {
        "id": "loops",
        "title": "Loops",
        "summary": "Loops let you repeat an action multiple times without rewriting code. They are great for iterating over lists or repeating a task until a condition changes.",
        "sample_question": "Explain the difference between a for loop and a while loop.",
    },
    {
        "id": "functions",
        "title": "Functions",
        "summary": "Functions group reusable logic under a single name. They accept inputs, perform work, and optionally return a value so you can keep code organized.",
        "sample_question": "Why would you wrap code in a function instead of leaving it inline?",
    },
]

MODE_PROFILES = {
    "learn": {"voice": "en-US-matthew", "display_name": "Matthew"},
    "quiz": {"voice": "en-US-alicia", "display_name": "Alicia"},
    "teach_back": {"voice": "en-US-ken", "display_name": "Ken"},
}

MODE_ACTIVITY_FIELDS = {
    "learn": "times_explained",
    "quiz": "times_quizzed",
    "teach_back": "times_taught_back",
}


def load_tutor_content() -> List[Dict[str, str]]:
    if CONTENT_PATH.exists():
        try:
            with open(CONTENT_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)
                if isinstance(data, list) and data:
                    return data
        except json.JSONDecodeError as exc:
            logger.warning("Unable to parse tutor content at %s: %s", CONTENT_PATH, exc)
    logger.info("Falling back to default tutor content.")
    return DEFAULT_CONTENT


def build_catalog_text(concepts: List[Dict[str, str]]) -> str:
    lines = []
    for concept in concepts:
        lines.append(
            f"- {concept['id']} ({concept['title']}): Summary -> {concept['summary']} | Prompt -> {concept['sample_question']}"
        )
    return "\n".join(lines)


class TeachTheTutorCoach(Agent):
    def __init__(self, content: Optional[List[Dict[str, str]]] = None) -> None:
        self.content = content or load_tutor_content()
        self.concepts_by_id = {concept["id"]: concept for concept in self.content}
        default_concept_id = self.content[0]["id"]
        self.session_state: Dict[str, Dict] = {
            "current_mode": None,
            "current_concept": default_concept_id,
            "mastery": {
                concept_id: {
                    "times_explained": 0,
                    "times_quizzed": 0,
                    "times_taught_back": 0,
                    "last_score": None,
                    "avg_score": 0.0,
                    "feedback": "",
                }
                for concept_id in self.concepts_by_id
            },
        }

        instructions = f"""
You are Teach-the-Tutor, an active recall coach. You help learners cycle through three lightweight modes that keep them engaged and talking:

LEARNING MODES (always invite the user to choose one and allow switching at any moment by calling the tools provided):
- learn (voice: Murf Falcon Matthew): deliver a concise explanation that references the concept summary and highlights 1 actionable example.
- quiz (voice: Murf Falcon Alicia): ask 1-2 questions based on the sample question, confirm/clarify the user's response, and note follow-up tips.
- teach_back (voice: Murf Falcon Ken): prompt the user to explain the concept back, listen, then provide qualitative feedback and a 0-100 confidence estimate.

CONTENT LIBRARY (always ground your responses in this data, do not invent new summaries or prompts):
{build_catalog_text(self.content)}

TOOLS YOU MUST USE:
1. switch_mode(mode:str) -> sets the learning mode and routes audio through the correct Murf Falcon voice. Call this right after the user picks a mode or asks to switch.
2. set_active_concept(concept_id:str) -> pick which concept we're focusing on. Use it when the user requests a new topic or after cycling through one concept.
3. record_teach_back_feedback(concept_id:str, score:int, feedback:str) -> after giving teach-back feedback, log the user's mastery details so you can reference them later.
4. get_state_snapshot() -> view current mode, concept, and per-concept mastery. Use it whenever you need to recall progress or recommend the next step.
5. list_concepts() -> quick refresher on available concepts if the user asks "what can we cover?".

CONVERSATION FLOW:
1. Greet the user, explain the three modes, and ask where they'd like to start. Wait for their choice before deep-diving.
2. After every mode request, call switch_mode so voice + tone match the mode.
3. Use set_active_concept before delivering content so you're always synced with the user’s choice.
4. Keep responses focused on the selected mode:
   - learn: rely on the summary, add one motivating example, and invite the user to try quiz or teach-back next.
   - quiz: start with the sample question, evaluate their answer, and optionally add one follow-up question for clarity.
   - teach_back: prompt them to explain, listen, summarize their strengths/gaps, then call record_teach_back_feedback with a 0-100 score and 1-2 sentence feedback.
5. Encourage switching modes anytime ("Want to quiz yourself on loops instead?").
6. When unsure what to cover next, call get_state_snapshot and suggest the concept with the lowest mastery or that hasn't been visited.

STYLE:
- Friendly, coach-like, concise sentences suited for audio.
- Use positive reinforcement but stay honest.
- Do not use emojis or special formatting.
"""

        super().__init__(instructions=instructions)
        self._session: Optional[AgentSession] = None
        self._room = None

    def _apply_voice(self, mode: str) -> None:
        profile = MODE_PROFILES.get(mode)
        if not profile or not self._session:
            return
        voice = profile["voice"]
        try:
            if hasattr(self._session, "tts"):
                self._session.tts.voice = voice
        except AttributeError:
            logger.warning("Unable to update TTS voice to %s", voice)

    def _ensure_concept(self, concept_id: Optional[str]) -> Dict[str, str]:
        concept = self.concepts_by_id.get(concept_id or "")
        if concept:
            return concept
        fallback = self.concepts_by_id[self.session_state["current_concept"]]
        return fallback

    def _increment_mastery(self, mode: str, concept_id: str) -> None:
        field = MODE_ACTIVITY_FIELDS.get(mode)
        if not field:
            return
        mastery = self.session_state["mastery"][concept_id]
        mastery[field] += 1

    @function_tool
    async def list_concepts(self, context: RunContext):
        """Return the available concepts for quick reference."""
        return self.content

    @function_tool
    async def set_active_concept(self, context: RunContext, concept_id: str):
        """Select the concept (by id) that the conversation should focus on."""
        if concept_id not in self.concepts_by_id:
            return {
                "error": f"{concept_id} is not in the content library.",
                "available_ids": list(self.concepts_by_id.keys()),
            }
        self.session_state["current_concept"] = concept_id
        concept = self.concepts_by_id[concept_id]
        logger.info("Active concept set to %s", concept_id)
        return concept

    @function_tool
    async def switch_mode(self, context: RunContext, mode: str):
        """Change between learn, quiz, and teach_back modes and activate the matching Murf voice."""
        if mode not in MODE_PROFILES:
            return {
                "error": f"{mode} is invalid. Choose from: {', '.join(MODE_PROFILES.keys())}."
            }
        self.session_state["current_mode"] = mode
        active_concept = self.session_state["current_concept"]
        self._apply_voice(mode)
        self._increment_mastery(mode, active_concept)
        voice_name = MODE_PROFILES[mode]["display_name"]
        logger.info("Switched to %s mode with voice %s", mode, voice_name)
        return {
            "mode": mode,
            "voice": voice_name,
            "concept": self.concepts_by_id[active_concept],
        }

    @function_tool
    async def get_state_snapshot(self, context: RunContext):
        """Return the internal tutor state including mastery counters per concept."""
        return self.session_state

    @function_tool
    async def record_teach_back_feedback(
        self, context: RunContext, concept_id: Optional[str], score: int, feedback: str
    ):
        """Store teach-back feedback so future coaching can reference mastery."""
        concept = self._ensure_concept(concept_id)
        mastery = self.session_state["mastery"][concept["id"]]
        bounded = max(0, min(100, score))
        prev_avg = mastery["avg_score"]
        total_attempts = max(1, mastery["times_taught_back"])
        mastery["avg_score"] = round(
            ((prev_avg * (total_attempts - 1)) + bounded) / total_attempts, 1
        )
        mastery["last_score"] = bounded
        mastery["feedback"] = feedback
        logger.info(
            "Teach-back feedback recorded for %s -> score=%s, feedback=%s",
            concept["id"],
            bounded,
            feedback,
        )
        return {
            "concept": concept,
            "last_score": mastery["last_score"],
            "avg_score": mastery["avg_score"],
            "feedback": mastery["feedback"],
        }

    async def send_initial_greeting(self):
        """Send the opening prompt once the audio pipeline is ready."""
        if not self._session:
            return
        self._apply_voice("learn")
        greeting = (
            "Hey there! I'm your Teach-the-Tutor coach. "
            "We can learn, quiz, or teach-back concepts like variables, loops, or functions. "
            "Which mode would you like to start with?"
        )
        await self._session.say(greeting, allow_interruptions=True)


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(
                model="gemini-2.5-flash",
            ),
        tts=murf.TTS(
                voice="en-US-matthew", 
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
            ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info("Usage: %s", summary)

    ctx.add_shutdown_callback(log_usage)

    tutor_agent = TeachTheTutorCoach()
    tutor_agent._session = session
    tutor_agent._room = ctx.room

    await session.start(
        agent=tutor_agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()
    
    import asyncio

    await asyncio.sleep(1.0)
    await tutor_agent.send_initial_greeting()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))

