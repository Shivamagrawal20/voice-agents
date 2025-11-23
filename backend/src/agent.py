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

# Directory to save orders (relative to backend directory)
ORDERS_DIR = Path(__file__).parent.parent / "orders"
ORDERS_DIR.mkdir(exist_ok=True)


class Barista(Agent):
    def __init__(self) -> None:
        # Initialize order state
        self.order = {
            "drinkType": "",
            "size": "",
            "milk": "",
            "extras": [],
            "name": "",
        }
        
        super().__init__(
            instructions="""You are a friendly and enthusiastic barista at a coffee shop. You're taking orders from customers via voice.

Your job is to:
1. Greet the customer warmly and ask what they'd like to order
2. Collect the following information by asking one question at a time:
   - drinkType: What type of drink (e.g., latte, cappuccino, espresso, americano, mocha, etc.)
   - size: What size (small, medium, large, or tall, grande, venti)
   - milk: What type of milk (whole milk, 2%, skim, almond, oat, soy, coconut, none)
   - extras: Any extras or add-ons (e.g., extra shot, whipped cream, caramel, vanilla, cinnamon, etc.) - this can be multiple items
   - name: The customer's name for the order

3. Ask one question at a time, wait for the answer, then move to the next field
4. IMPORTANT: Do NOT repeat the same question. Only ask each question once. If you've already asked a question, wait for the customer's response.
5. When asking questions, use the send_message_with_options tool to provide clickable options to make it easier for customers
6. Use the update_order_field tool to save each piece of information as the customer provides it
7. Use the get_order_status tool to check what information you still need
8. Once all fields are filled (drinkType, size, milk, extras, and name), use the save_order tool to complete the order
9. After saving, confirm the order back to the customer in a friendly way

Be conversational, friendly, and helpful. If a customer seems unsure, offer suggestions. Keep your responses concise and natural for voice interaction. Don't use emojis, asterisks, or special formatting in your speech. Never repeat the same question - wait for the customer's response.""",
        )
        
        # Store session and room references for sending messages with options
        self._session = None
        self._room = None
        # Track last message to prevent duplicates
        self._last_message = None
        self._last_message_time = 0

    @function_tool
    async def update_order_field(self, context: RunContext, field: str, value: str):
        """Update a specific field in the current order.
        
        Use this tool whenever the customer provides information about their order.
        For the 'extras' field, you can call this multiple times to add multiple extras.
        
        Args:
            field: The field to update. Must be one of: 'drinkType', 'size', 'milk', 'extras', or 'name'
            value: The value to set for this field. For 'extras', this will add to the list.
        """
        if field not in ["drinkType", "size", "milk", "extras", "name"]:
            return f"Invalid field: {field}. Must be one of: drinkType, size, milk, extras, name"
        
        if field == "extras":
            if value not in self.order["extras"]:
                self.order["extras"].append(value)
                logger.info(f"Added extra: {value}. Current extras: {self.order['extras']}")
                return f"Added {value} to your order extras. Current extras: {', '.join(self.order['extras']) if self.order['extras'] else 'none'}"
            else:
                return f"{value} is already in your extras."
        else:
            self.order[field] = value
            logger.info(f"Updated {field} to: {value}")
            return f"Got it! {field} set to {value}."

    @function_tool
    async def get_order_status(self, context: RunContext):
        """Check the current status of the order to see what information is still needed.
        
        Returns a summary of what has been collected and what is still missing.
        Use this to know what question to ask next.
        """
        missing = []
        collected = []
        
        if not self.order["drinkType"]:
            missing.append("drinkType")
        else:
            collected.append(f"drinkType: {self.order['drinkType']}")
            
        if not self.order["size"]:
            missing.append("size")
        else:
            collected.append(f"size: {self.order['size']}")
            
        if not self.order["milk"]:
            missing.append("milk")
        else:
            collected.append(f"milk: {self.order['milk']}")
            
        if not self.order["name"]:
            missing.append("name")
        else:
            collected.append(f"name: {self.order['name']}")
        
        # Extras can be empty, so we don't require it, but we'll note if it's set
        if self.order["extras"]:
            collected.append(f"extras: {', '.join(self.order['extras'])}")
        
        status = f"Order status - Collected: {', '.join(collected) if collected else 'nothing yet'}"
        if missing:
            status += f" | Still need: {', '.join(missing)}"
        else:
            status += " | Order is complete!"
        
        logger.info(f"Order status: {status}")
        return status

    @function_tool
    async def send_message_with_options(self, context: RunContext, message: str, options: str):
        """Send a message to the customer with clickable options displayed in the chat.
        
        Use this when asking questions to make it easier for customers to respond.
        The options will appear as clickable buttons in the chat interface.
        
        IMPORTANT: Only call this once per question. Do not repeat the same question.
        Check if you've already asked this question before calling this tool.
        
        Args:
            message: The message/question to send to the customer (this will be spoken)
            options: A JSON string array of options, e.g., '["Latte", "Cappuccino", "Espresso", "Mocha"]'
                    or a comma-separated string like "small, medium, large"
        """
        try:
            import time
            current_time = time.time()
            
            # Prevent duplicate messages within 3 seconds
            if (self._last_message == message and 
                current_time - self._last_message_time < 3.0):
                logger.info(f"Skipping duplicate message: {message}")
                return f"Message already sent recently. Skipping duplicate."
            
            # Parse options - handle both JSON array and comma-separated strings
            import json
            if options.startswith('['):
                options_list = json.loads(options)
            else:
                # Split by comma and clean up
                options_list = [opt.strip() for opt in options.split(',')]
            
            # Format options as JSON for frontend parsing
            options_json = json.dumps([{"label": opt, "value": opt} for opt in options_list])
            
            if self._session and self._room:
                # Send the clean message to TTS (this will be spoken)
                await self._session.say(message, allow_interruptions=True)
                
                # Small delay to ensure message is processed
                import asyncio
                await asyncio.sleep(0.1)
                
                # Send options via data channel AND embed in text stream as fallback
                options_data = {
                    "type": "chat_options",
                    "options": json.loads(options_json),
                    "message_id": f"msg_{int(datetime.now().timestamp() * 1000)}",
                    "message_text": message  # Include message text for matching
                }
                
                # Send via room data channel
                data = json.dumps(options_data).encode('utf-8')
                await self._room.local_participant.publish_data(data, reliable=True)
                
                # Also send as text stream with options embedded (fallback for frontend)
                # This ensures options are always available even if data channel fails
                message_with_options = f"{message} __OPTIONS__{options_json}"
                await self._session.say(message_with_options, allow_interruptions=False)
            else:
                logger.warning("Session or room not available for sending message with options")
                # Fallback: send message with options embedded (frontend will parse)
                if self._session:
                    message_with_options = f"{message} __OPTIONS__{options_json}"
                    await self._session.say(message_with_options, allow_interruptions=True)
            
            # Update last message tracking
            self._last_message = message
            self._last_message_time = current_time
            
            return f"Sent message with {len(options_list)} options"
        except Exception as e:
            logger.error(f"Error sending message with options: {e}")
            # Fallback to regular message
            if self._session:
                await self._session.say(message, allow_interruptions=True)
            return f"Sent message without options due to error: {e}"

    @function_tool
    async def save_order(self, context: RunContext):
        """Save the completed order to a JSON file.
        
        Only call this when all required fields are filled: drinkType, size, milk, and name.
        Extras can be empty.
        """
        # Validate that required fields are filled
        if not self.order["drinkType"] or not self.order["size"] or not self.order["milk"] or not self.order["name"]:
            missing = []
            if not self.order["drinkType"]:
                missing.append("drinkType")
            if not self.order["size"]:
                missing.append("size")
            if not self.order["milk"]:
                missing.append("milk")
            if not self.order["name"]:
                missing.append("name")
            return f"Cannot save order. Missing required fields: {', '.join(missing)}"
        
        # Create order summary with timestamp
        order_summary = {
            **self.order,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Save to JSON file
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"order_{timestamp_str}_{self.order['name'].replace(' ', '_')}.json"
        filepath = ORDERS_DIR / filename
        
        with open(filepath, "w") as f:
            json.dump(order_summary, f, indent=2)
        
        logger.info(f"Order saved to {filepath}")
        
        # Reset order for next customer
        self.order = {
            "drinkType": "",
            "size": "",
            "milk": "",
            "extras": [],
            "name": "",
        }
        
        return f"Order saved successfully to {filename}! Order summary: {order_summary['drinkType']} ({order_summary['size']}) with {order_summary['milk']} milk" + (f" and {', '.join(order_summary['extras'])}" if order_summary['extras'] else "") + f" for {order_summary['name']}."


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

    # Create the barista agent
    barista = Barista()
    
    # Store session and room references in agent for sending messages with options
    barista._session = session
    barista._room = ctx.room

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=barista,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()
    
    # Send an initial greeting with options after a short delay to ensure everything is ready
    import asyncio
    await asyncio.sleep(1.0)  # Wait for connection to stabilize
    
    # Send clean greeting (will be spoken)
    await session.say("Hi! Welcome to our coffee shop! What can I get for you today?", allow_interruptions=True)
    
    # Send options via data channel (won't be spoken)
    drink_options_data = {
        "type": "chat_options",
        "options": [
            {"label": "Latte", "value": "latte"},
            {"label": "Cappuccino", "value": "cappuccino"},
            {"label": "Espresso", "value": "espresso"},
            {"label": "Americano", "value": "americano"},
            {"label": "Mocha", "value": "mocha"}
        ],
        "message_id": f"greeting_{int(datetime.now().timestamp() * 1000)}"
    }
    data = json.dumps(drink_options_data).encode('utf-8')
    await ctx.room.local_participant.publish_data(data, reliable=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
