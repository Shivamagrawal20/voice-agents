import json
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
    tokenize,
    function_tool,
    RunContext,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Path to wellness log JSON file (relative to backend directory)
WELLNESS_LOG_PATH = Path(__file__).parent.parent / "wellness_log.json"


class WellnessCompanion(Agent):
    def __init__(self, past_check_ins: list = None) -> None:
        # Initialize check-in state
        self.check_in = {
            "mood": "",
            "energy": "",
            "stress": "",
            "objectives": [],
            "summary": "",
        }
        self.past_check_ins = past_check_ins or []
        
        # Build context from past check-ins for the system prompt
        past_context = ""
        if self.past_check_ins:
            # Get the most recent check-in for reference
            latest = self.past_check_ins[-1]
            past_context = f"\n\nCONTEXT FROM PAST CHECK-INS:\n"
            past_context += f"Last time we talked (on {latest.get('date', 'a previous day')}), "
            if latest.get('mood'):
                past_context += f"you mentioned feeling {latest.get('mood')}. "
            if latest.get('energy'):
                past_context += f"Your energy level was {latest.get('energy')}. "
            if latest.get('objectives'):
                past_context += f"You had these objectives: {', '.join(latest.get('objectives', []))}.\n"
            past_context += "Feel free to reference this naturally in conversation when appropriate, but don't force it."
        
        super().__init__(
            instructions=f"""You are a supportive, grounded health and wellness voice companion. Your role is to conduct brief daily check-ins that help users reflect on their mood, energy, and goals.

CORE PRINCIPLES:
- Be supportive but realistic and grounded. Avoid medical claims or diagnoses.
- Keep conversations concise and natural for voice interaction.
- Be empathetic and understanding, but not overly clinical or formal.
- Offer simple, actionable, non-medical advice when appropriate.

DAILY CHECK-IN STRUCTURE:

1. MOOD AND ENERGY CHECK-IN
   Ask about how they're feeling today. Topics to explore (naturally, not as a checklist):
   - "How are you feeling today?"
   - "What's your energy like?"
   - "Anything stressing you out right now?"
   - Use the update_check_in_field tool to record their responses for mood, energy, and stress.

2. INTENTIONS AND OBJECTIVES
   Ask about what they'd like to accomplish today:
   - "What are 1-3 things you'd like to get done today?"
   - "Is there anything you want to do for yourself today? (rest, exercise, hobbies, etc.)"
   - Use the add_objective tool to record each objective they mention.

3. OFFER SIMPLE, REALISTIC ADVICE (when appropriate)
   Provide grounded suggestions that are:
   - Small and actionable (e.g., "break that into smaller steps", "take a 5-minute walk")
   - Non-medical and non-diagnostic
   - Supportive without being prescriptive
   Examples: suggest breaking large goals into smaller steps, encourage short breaks, offer simple grounding ideas.

4. CLOSE WITH A RECAP
   Before ending, summarize what they shared:
   - Today's mood summary
   - Their main 1-3 objectives
   - Confirm: "Does this sound right?"
   - Use the generate_summary tool to create a brief summary sentence.

5. SAVE THE CHECK-IN
   Once the recap is confirmed, use the save_check_in tool to persist the data to wellness_log.json.

TOOLS AVAILABLE:
- update_check_in_field: Record mood, energy, or stress responses
- add_objective: Add an objective/intention to their list
- get_check_in_status: Check what information you've collected so far
- generate_summary: Create a brief summary sentence of the check-in
- save_check_in: Save the completed check-in to wellness_log.json
- read_past_check_ins: Read previous check-ins (optional, use sparingly)

CONVERSATION STYLE:
- Natural, conversational, and warm
- Don't use emojis, asterisks, or special formatting in your speech
- Ask questions one at a time and wait for responses
- Be genuinely curious and supportive
- Keep responses concise for voice interaction
{past_context}

Remember: This is a daily check-in companion, not a therapist or medical professional. Stay grounded, supportive, and focused on reflection and simple, actionable guidance.""",
        )
        
        # Store session and room references
        self._session = None
        self._room = None

    @function_tool
    async def update_check_in_field(self, context: RunContext, field: str, value: str):
        """Update a specific field in the current check-in.
        
        Use this tool when the user shares information about their mood, energy, or stress.
        
        Args:
            field: The field to update. Must be one of: 'mood', 'energy', or 'stress'
            value: The user's response about this field (as they described it)
        """
        if field not in ["mood", "energy", "stress"]:
            return f"Invalid field: {field}. Must be one of: mood, energy, stress"
        
        self.check_in[field] = value
        logger.info(f"Updated {field} to: {value}")
        return f"Got it, I've noted that your {field} is {value}."

    @function_tool
    async def add_objective(self, context: RunContext, objective: str):
        """Add an objective or intention to the user's list for today.
        
        Use this tool whenever the user mentions something they want to accomplish or do today.
        You can call this multiple times to add multiple objectives.
        
        Args:
            objective: The objective or intention the user mentioned
        """
        if objective not in self.check_in["objectives"]:
            self.check_in["objectives"].append(objective)
            logger.info(f"Added objective: {objective}. Current objectives: {self.check_in['objectives']}")
            return f"Got it! I've added '{objective}' to your objectives for today."
        else:
            return f"'{objective}' is already in your objectives list."

    @function_tool
    async def get_check_in_status(self, context: RunContext):
        """Check the current status of the check-in to see what information has been collected.
        
        Returns a summary of what has been collected so far.
        Use this to know what to ask about next or to prepare the recap.
        """
        collected = []
        
        if self.check_in["mood"]:
            collected.append(f"mood: {self.check_in['mood']}")
        if self.check_in["energy"]:
            collected.append(f"energy: {self.check_in['energy']}")
        if self.check_in["stress"]:
            collected.append(f"stress: {self.check_in['stress']}")
        if self.check_in["objectives"]:
            collected.append(f"objectives: {', '.join(self.check_in['objectives'])}")
        
        status = f"Check-in status - Collected: {', '.join(collected) if collected else 'nothing yet'}"
        
        logger.info(f"Check-in status: {status}")
        return status

    @function_tool
    async def generate_summary(self, context: RunContext, summary: str):
        """Generate a brief summary sentence of today's check-in.
        
        Use this at the end of the check-in, after you've done the recap with the user.
        The summary should be a concise one-sentence summary of the check-in.
        
        Args:
            summary: A brief one-sentence summary of today's check-in
        """
        self.check_in["summary"] = summary
        logger.info(f"Generated summary: {summary}")
        return "Summary generated successfully."

    @function_tool
    async def save_check_in(self, context: RunContext):
        """Save the completed check-in to wellness_log.json.
        
        Call this after you've done the recap with the user and they've confirmed it's correct.
        The check-in should have at least mood, objectives, and a summary.
        """
        # Create check-in entry with timestamp
        check_in_entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "timestamp": datetime.now().isoformat(),
            "mood": self.check_in["mood"],
            "energy": self.check_in["energy"],
            "stress": self.check_in["stress"],
            "objectives": self.check_in["objectives"],
            "summary": self.check_in["summary"],
        }
        
        # Load existing check-ins
        wellness_log = {"check_ins": []}
        if WELLNESS_LOG_PATH.exists():
            try:
                with open(WELLNESS_LOG_PATH, "r") as f:
                    wellness_log = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse {WELLNESS_LOG_PATH}, creating new file")
                wellness_log = {"check_ins": []}
        
        # Add new check-in
        wellness_log["check_ins"].append(check_in_entry)
        
        # Save to JSON file
        with open(WELLNESS_LOG_PATH, "w") as f:
            json.dump(wellness_log, f, indent=2)
        
        logger.info(f"Check-in saved to {WELLNESS_LOG_PATH}")
        
        # Reset check-in for next session
        self.check_in = {
            "mood": "",
            "energy": "",
            "stress": "",
            "objectives": [],
            "summary": "",
        }
        
        return f"Great! I've saved today's check-in. You shared that you're feeling {check_in_entry['mood']} and your objectives are: {', '.join(check_in_entry['objectives']) if check_in_entry['objectives'] else 'none'}."

    @function_tool
    async def read_past_check_ins(self, context: RunContext, days: int = 7):
        """Read past check-ins from the wellness log.
        
        Use this sparingly, mainly if the user asks about their past check-ins or patterns.
        
        Args:
            days: Number of days to look back (default: 7)
        """
        if not WELLNESS_LOG_PATH.exists():
            return "No past check-ins found."
        
        try:
            with open(WELLNESS_LOG_PATH, "r") as f:
                wellness_log = json.load(f)
            
            check_ins = wellness_log.get("check_ins", [])
            
            # Filter by date if needed (simplified - just return recent ones)
            recent_check_ins = check_ins[-days:] if len(check_ins) > days else check_ins
            
            if not recent_check_ins:
                return "No recent check-ins found."
            
            summary = f"Found {len(recent_check_ins)} check-in(s) from the past {days} days:\n"
            for check_in in recent_check_ins:
                summary += f"- {check_in.get('date', 'Unknown date')}: Mood: {check_in.get('mood', 'N/A')}, Objectives: {', '.join(check_in.get('objectives', [])) if check_in.get('objectives') else 'None'}\n"
            
            return summary
        except Exception as e:
            logger.error(f"Error reading past check-ins: {e}")
            return f"Error reading past check-ins: {e}"


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using OpenAI, Cartesia, AssemblyAI, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
                model="gemini-2.5-flash",
            ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
                voice="en-US-matthew", 
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # Metrics collection, to measure pipeline performance
    # For more information, see https://docs.livekit.io/agents/build/metrics/
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Load past check-ins from wellness log
    past_check_ins = []
    if WELLNESS_LOG_PATH.exists():
        try:
            with open(WELLNESS_LOG_PATH, "r") as f:
                wellness_log = json.load(f)
                past_check_ins = wellness_log.get("check_ins", [])
                logger.info(f"Loaded {len(past_check_ins)} past check-ins")
        except json.JSONDecodeError:
            logger.warning(f"Could not parse {WELLNESS_LOG_PATH}, starting fresh")
            past_check_ins = []

    # Create the wellness companion agent with past check-ins context
    wellness_companion = WellnessCompanion(past_check_ins=past_check_ins)
    
    # Store session and room references in agent
    wellness_companion._session = session
    wellness_companion._room = ctx.room

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=wellness_companion,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()
    
    # Send an initial greeting after a short delay to ensure everything is ready
    import asyncio
    await asyncio.sleep(1.0)  # Wait for connection to stabilize
    
    # Build personalized greeting based on past check-ins
    greeting = "Hi! I'm your wellness companion. How are you feeling today?"
    if past_check_ins:
        latest = past_check_ins[-1]
        # Reference the most recent check-in if it's from a previous day
        latest_date = latest.get("date", "")
        today_date = datetime.now().strftime("%Y-%m-%d")
        if latest_date != today_date:
            if latest.get("mood"):
                greeting = f"Hi! Good to see you again. Last time we talked, you mentioned feeling {latest.get('mood')}. How are you feeling today?"
            elif latest.get("energy"):
                greeting = f"Hi! Welcome back. Last time, your energy was {latest.get('energy')}. How are you doing today?"
    
    await session.say(greeting, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
