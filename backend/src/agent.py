import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TypedDict

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

@dataclass
class ImprovRound(TypedDict, total=False):
    scenario: str
    host_reaction: str


class ImprovState(TypedDict):
    player_name: Optional[str]
    current_round: int
    max_rounds: int
    rounds: List[ImprovRound]
    phase: str  # "intro" | "awaiting_improv" | "reacting" | "done"


class ImprovHostAgent(Agent):
    """Improv Battle host for Day 10."""

    def __init__(self, max_rounds: int = 3) -> None:
        # Basic per-session improv state kept in memory
        self.improv_state: ImprovState = {
            "player_name": None,
            "current_round": 0,
            "max_rounds": max_rounds,
            "rounds": [],
            "phase": "intro",
        }
        self._session: Optional[AgentSession] = None
        self._room = None

        # A small pool of fun scenarios – the LLM can also create its own based on these examples.
        self._scenario_pool: List[str] = [
            "You are a time-travelling tour guide explaining modern smartphones to someone from the 1800s.",
            "You are a restaurant waiter who must calmly tell a customer that their order has escaped the kitchen.",
            "You are a customer trying to return an obviously cursed object to a very skeptical shop owner.",
            "You are a barista who has to tell a customer that their latte is actually a portal to another dimension.",
            "You are a museum security guard explaining to your boss why the painting is now talking back to visitors.",
        ]

        instructions = """
You are the energetic host of a TV improv show called "Improv Battle".

GOAL:
- Run a short-form improv game for ONE player.
- Play out clear, funny scenarios and give realistic reactions.
- Always keep things respectful and safe while allowing light teasing and honest critique.

PERSONA & STYLE:
- High-energy, witty, and confident, like a TV game show host.
- You clearly explain the rules at the beginning.
- Your reactions are varied and realistic:
  - Sometimes amused, sometimes unimpressed, sometimes pleasantly surprised.
  - Mix supportive, neutral, and mildly critical tones at random.
  - You are never abusive or cruel. Keep it playful, constructive, and safe.

GAME STRUCTURE:
1) INTRO:
   - Introduce the show "Improv Battle".
   - Ask for the player's name if you don't know it.
   - Briefly explain the rules:
     - There will be N short improv rounds (usually 3).
     - In each round you set a scene and ask the player to act it out.
     - When they are done, you react and move on.
   - Ask the player if they are ready to begin.

2) ROUNDS:
   For each round:
   - Use the `start_next_round` tool to advance the round and get a scenario.
   - Announce the round number and the scenario.
   - VERY CLEARLY invite the player to start improvising in character.
   - Let the player perform for one or more turns.
   - When they are clearly done (e.g. they say something like "end scene", "okay I'm done",
     or they signal they want to move on), react to their performance.
   - Use the `record_reaction` tool after your reaction so their reaction text is stored.
   - Then either:
     - Start the next round (if `current_round < max_rounds`), or
     - Move to the closing summary when all rounds are complete.

3) REACTIONS:
   After each scene, your reaction should:
   - Mention specific things they did (interesting lines, choices, tone, etc.).
   - Mix praise and gentle critique:
     - Sometimes: very supportive and impressed.
     - Sometimes: more neutral or mildly critical (e.g. “you could have slowed down there”).
   - Randomly vary your tone between:
     - More supportive
     - Balanced / neutral
     - Mildly critical but constructive
   - NEVER insult the player or use unsafe or hateful language.

4) CLOSING SUMMARY:
   - When `current_round` reaches `max_rounds`, give a short overall summary:
     - What kind of improviser they seemed to be
       (e.g. character-focused, absurd-comedy, emotional, deadpan, etc.).
     - Reference a few specific memorable moments from earlier scenes.
   - Thank them for playing and clearly end the show.

5) EARLY EXIT:
   - If the player clearly asks to stop (e.g. “stop game”, “end show”, “I want to quit”):
     - Confirm they want to end.
     - If they confirm, give a short closing comment and end the show gracefully.
     - You can also call the `end_game_early` tool to mark the game as done.

BACKEND STATE & TOOLS:
- The backend keeps an `improv_state` object with:
  - player_name: string | null
  - current_round: int
  - max_rounds: int
  - rounds: list of {"scenario": str, "host_reaction": str}
  - phase: "intro" | "awaiting_improv" | "reacting" | "done"

You have the following tools to help you run the game. Use them deliberately:
- get_improv_state() -> returns the current improv_state.
- set_player_name(name: str) -> set the player's name if you learn it.
- start_next_round() -> increments current_round, picks a scenario, and updates phase to "awaiting_improv".
- record_reaction(reaction: str) -> save your latest reaction for the current round and set phase to "reacting".
- end_game_early(reason: str = "") -> mark the game as done when the player chooses to stop.

RULES:
- Keep the conversation focused on the Improv Battle game.
- Do NOT start a new fantasy adventure or unrelated story.
- Speak in short, clear paragraphs so the audio experience feels snappy.
- Periodically remind the player that they can say “end scene” to move on or “stop game” to exit.
"""

        super().__init__(instructions=instructions)

    @property
    def max_rounds(self) -> int:
        return self.improv_state["max_rounds"]

    @function_tool
    async def get_improv_state(self, context: RunContext) -> Dict:
        """Get the current improv game state (player name, round info, and phase)."""
        return dict(self.improv_state)

    @function_tool
    async def set_player_name(self, context: RunContext, name: str) -> Dict:
        """Set or update the player's name for this improv session."""
        cleaned = name.strip()
        if cleaned:
            self.improv_state["player_name"] = cleaned
        return {"player_name": self.improv_state["player_name"]}

    @function_tool
    async def start_next_round(self, context: RunContext) -> Dict:
        """Advance to the next improv round and return the chosen scenario."""
        if self.improv_state["phase"] == "done":
            return {
                "status": "finished",
                "message": "All improv rounds are already complete.",
                "state": dict(self.improv_state),
            }

        if self.improv_state["current_round"] >= self.improv_state["max_rounds"]:
            self.improv_state["phase"] = "done"
            return {
                "status": "no_more_rounds",
                "message": "No more rounds left. You should give a closing summary.",
                "state": dict(self.improv_state),
            }

        # Choose a scenario – cycle through the pool and add some randomness.
        idx = self.improv_state["current_round"] % len(self._scenario_pool)
        scenario = random.choice(self._scenario_pool[idx:] or self._scenario_pool)

        self.improv_state["current_round"] += 1
        self.improv_state["phase"] = "awaiting_improv"

        round_info: ImprovRound = {
            "scenario": scenario,
            "host_reaction": "",
        }
        self.improv_state["rounds"].append(round_info)

        logger.info(
            "Starting improv round %s / %s: %s",
            self.improv_state["current_round"],
            self.improv_state["max_rounds"],
            scenario,
        )

        return {
            "status": "started",
            "round_number": self.improv_state["current_round"],
            "scenario": scenario,
            "state": dict(self.improv_state),
        }

    @function_tool
    async def record_reaction(self, context: RunContext, reaction: str) -> Dict:
        """Store the host's reaction text for the current round."""
        if not self.improv_state["rounds"]:
            return {
                "status": "no_round",
                "message": "There is no active round to attach a reaction to.",
            }

        latest_round = self.improv_state["rounds"][-1]
        latest_round["host_reaction"] = reaction.strip()
        self.improv_state["phase"] = "reacting"

        logger.info(
            "Recorded reaction for round %s",
            self.improv_state["current_round"],
        )

        # If we've reacted to the last round, the LLM should move toward closing.
        if self.improv_state["current_round"] >= self.improv_state["max_rounds"]:
            hint = "All rounds have a stored reaction. You should now move toward a closing summary."
        else:
            hint = "You can move on to the next improv round when appropriate."

        return {
            "status": "recorded",
            "round_number": self.improv_state["current_round"],
            "state": dict(self.improv_state),
            "hint": hint,
        }

    @function_tool
    async def end_game_early(self, context: RunContext, reason: str = "") -> Dict:
        """Mark the improv game as finished early, e.g. when the player asks to stop."""
        self.improv_state["phase"] = "done"
        logger.info("Improv game ended early. Reason: %s", reason)
        return {
            "status": "ended",
            "reason": reason,
            "state": dict(self.improv_state),
        }

    async def send_initial_greeting(self):
        """Send the opening Improv Battle greeting when audio is ready."""
        if not self._session:
            return
        
        greeting = (
            "Welcome to Improv Battle, the short-form improv voice game show! "
            "I'm your AI host, here to throw you into a few ridiculous scenarios and react to your performance. "
            "We'll play through a handful of quick rounds. "
            "First, tell me your name, and then say you're ready to start the Improv Battle."
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
        llm=google.LLM(model="gemini-2.5-flash"),
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

    # Create Improv Battle host agent for Day 10
    improv_host = ImprovHostAgent(max_rounds=3)
    improv_host._session = session
    improv_host._room = ctx.room

    await session.start(
        agent=improv_host,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()
    
    import asyncio

    await asyncio.sleep(1.0)
    await improv_host.send_initial_greeting()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
