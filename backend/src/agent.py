import json
import logging
import random
import uuid
from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime
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

# Game state persistence path
GAME_STATE_PATH = (
    Path(__file__).resolve().parents[2] / "shared-data" / "game_state.json"
)


@dataclass
class Character:
    """Player character or NPC"""
    name: str
    role: str = ""  # "player", "npc", "enemy"
    hp: int = 100
    max_hp: int = 100
    attributes: Dict[str, int] = field(default_factory=lambda: {
        "strength": 10,
        "intelligence": 10,
        "dexterity": 10,
        "luck": 10
    })
    inventory: List[str] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)
    attitude: str = "neutral"  # For NPCs: "friendly", "neutral", "hostile"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Character":
        return cls(**data)


@dataclass
class Location:
    """Game location"""
    name: str
    description: str
    paths: List[str] = field(default_factory=list)  # Connected locations
    visited: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Location":
        return cls(**data)


@dataclass
class WorldState:
    """Complete game world state"""
    player: Character
    npcs: Dict[str, Character] = field(default_factory=dict)
    current_location: str = "The Starting Point"
    locations: Dict[str, Location] = field(default_factory=dict)
    events: List[Dict] = field(default_factory=list)
    quests: List[Dict] = field(default_factory=list)
    session_id: str = ""
    turn_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "player": self.player.to_dict(),
            "npcs": {k: v.to_dict() for k, v in self.npcs.items()},
            "current_location": self.current_location,
            "locations": {k: v.to_dict() for k, v in self.locations.items()},
            "events": self.events,
            "quests": self.quests,
            "session_id": self.session_id,
            "turn_count": self.turn_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "WorldState":
        player = Character.from_dict(data.get("player", {}))
        npcs = {
            k: Character.from_dict(v) 
            for k, v in data.get("npcs", {}).items()
        }
        locations = {
            k: Location.from_dict(v)
            for k, v in data.get("locations", {}).items()
        }
        return cls(
            player=player,
            npcs=npcs,
            current_location=data.get("current_location", "The Starting Point"),
            locations=locations,
            events=data.get("events", []),
            quests=data.get("quests", []),
            session_id=data.get("session_id", ""),
            turn_count=data.get("turn_count", 0),
        )
    
    def add_event(self, event_type: str, description: str, metadata: Dict = None):
        """Add an event to the history"""
        self.events.append({
            "type": event_type,
            "description": description,
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
        })
    
    def add_quest(self, title: str, description: str, status: str = "active"):
        """Add or update a quest"""
        # Check if quest already exists
        for quest in self.quests:
            if quest.get("title") == title:
                quest["status"] = status
                quest["description"] = description
                return
        # Add new quest
        self.quests.append({
            "title": title,
            "description": description,
            "status": status,
        })


# Universe presets
UNIVERSES = {
    "fantasy": {
        "name": "Classic Fantasy",
        "system_prompt": """You are a Game Master running a classic fantasy adventure in a world of dragons, magic, and ancient kingdoms.

UNIVERSE: A medieval fantasy realm with:
- Magic exists and can be learned or found in artifacts
- Various races: humans, elves, dwarves, orcs
- Dangerous creatures: dragons, goblins, trolls, undead
- Ancient ruins, dungeons, and mystical forests
- Multiple kingdoms and factions

YOUR ROLE:
- Describe scenes vividly with sensory details (sights, sounds, smells)
- Present choices and challenges that fit the fantasy setting
- Use the world state to maintain consistency (NPCs, locations, events)
- End each message with a clear prompt: "What do you do?" or "How do you proceed?"
- Make the story engaging with 8-15 meaningful exchanges per session

STORY STRUCTURE:
- Start with the player awakening or arriving at an interesting location
- Introduce a clear goal or quest early (find treasure, rescue someone, solve a mystery)
- Create obstacles that require player decisions
- Build to a climactic moment (battle, puzzle, discovery)
- End with a satisfying conclusion or cliffhanger

MECHANICS:
- Use dice_roll for skill checks when the player attempts risky actions
- Update world state when important things happen (meeting NPCs, finding items, changing locations)
- Track player HP and inventory - use them to affect outcomes
- Make combat and challenges feel dangerous but fair

TONE: Epic, adventurous, with moments of tension and wonder.""",
        "initial_location": "A Mysterious Forest Clearing",
        "initial_location_desc": "You find yourself in a misty forest clearing. Ancient trees tower overhead, and strange sounds echo from the shadows. A worn path leads deeper into the woods, while another trail seems to head toward distant mountains.",
    },
    "sci_fi": {
        "name": "Space Opera",
        "system_prompt": """You are a Game Master running a space opera adventure in a futuristic galaxy.

UNIVERSE: A vast galaxy with:
- Multiple alien species and space stations
- Advanced technology: starships, AI, cybernetics, energy weapons
- Corporate empires, rebel factions, and mysterious entities
- Dangerous planets, asteroid fields, and space anomalies
- Cyberpunk elements: hacking, corporate espionage, underground markets

YOUR ROLE:
- Describe scenes with sci-fi flair (holograms, neon lights, alien architecture)
- Present choices involving technology, diplomacy, or action
- Use the world state to track NPCs, locations, and events
- End each message with: "What do you do?" or "How do you proceed?"
- Create engaging 8-15 exchange adventures

STORY STRUCTURE:
- Start with the player on a space station, ship, or planet
- Introduce a mission or problem (smuggling run, rescue mission, corporate intrigue)
- Create obstacles: security systems, hostile aliens, rival factions
- Build to a climax: space battle, hacking sequence, or confrontation
- End with resolution or setup for next adventure

MECHANICS:
- Use dice_roll for skill checks (hacking, piloting, combat)
- Track technology, credits, and ship status
- Update world state for NPCs, locations, and events
- Make technology feel powerful but with consequences

TONE: Fast-paced, high-tech, with a mix of action and intrigue.""",
        "initial_location": "Deep Space Station Alpha",
        "initial_location_desc": "You're on the bustling space station Alpha, a hub of trade and intrigue. Holographic displays flicker around you, and various alien species move through the corridors. Your ship is docked at Bay 7, and you have a message waiting on your datapad.",
    },
    "post_apocalypse": {
        "name": "Post-Apocalypse",
        "system_prompt": """You are a Game Master running a post-apocalyptic survival adventure.

UNIVERSE: A world after the collapse:
- Ruined cities and wastelands
- Scavenging for resources: food, water, medicine, ammo
- Hostile survivors, mutated creatures, and raider gangs
- Settlements and safe zones are rare and valuable
- Technology is scarce but valuable when found

YOUR ROLE:
- Describe the harsh, desolate world with gritty realism
- Emphasize survival challenges: hunger, thirst, danger
- Present moral choices in a world where resources are scarce
- Use world state to track NPCs, locations, and resources
- End each message with: "What do you do?" or "How do you proceed?"
- Create tense 8-15 exchange survival stories

STORY STRUCTURE:
- Start with the player in a dangerous situation or at a settlement
- Introduce a survival goal (find supplies, reach safety, rescue someone)
- Create obstacles: raiders, mutants, resource scarcity, environmental hazards
- Build to a climax: escape, confrontation, or discovery
- End with survival or a new challenge

MECHANICS:
- Use dice_roll for survival checks, combat, and resource gathering
- Track supplies, health, and relationships with settlements
- Update world state for NPCs, locations, and events
- Make survival feel challenging but not impossible

TONE: Gritty, tense, with moments of hope and desperation.""",
        "initial_location": "The Wasteland Outpost",
        "initial_location_desc": "You're at a small outpost on the edge of the wasteland. Rusted vehicles and makeshift shelters surround you. The air is thick with dust, and you can hear the distant howl of something unnatural. Your supplies are running low, and you need to make a decision about where to go next.",
    },
}


class GameMasterAgent(Agent):
    """D&D-style Game Master that runs interactive voice adventures."""

    def __init__(self, universe: str = "fantasy") -> None:
        self.universe = universe
        self.universe_config = UNIVERSES.get(universe, UNIVERSES["fantasy"])
        self.world_state: Optional[WorldState] = None
        self._session: Optional[AgentSession] = None
        self._room = None

        # Build system instructions
        instructions = self.universe_config["system_prompt"] + """

AVAILABLE TOOLS:
- get_world_state() -> Get the current world state (player stats, location, NPCs, events, quests)
- update_player_stats(hp_change: int, attribute: str = "", value: int = 0) -> Modify player HP or attributes
- add_to_inventory(item: str) -> Add an item to player inventory
- remove_from_inventory(item: str) -> Remove an item from player inventory
- update_location(location_name: str, description: str, paths: List[str]) -> Change or add a location
- add_npc(name: str, role: str, attitude: str = "neutral", hp: int = 100) -> Add or update an NPC
- add_event(event_type: str, description: str) -> Record an important event
- add_quest(title: str, description: str, status: str = "active") -> Add or update a quest
- dice_roll(sides: int = 20, modifier: int = 0, reason: str = "") -> Roll dice for skill checks
- restart_game() -> Start a fresh adventure (use when player explicitly requests it)

IMPORTANT RULES:
1. Always end your messages with a question prompting player action: "What do you do?" or "How do you proceed?"
2. Use dice_roll when the player attempts something risky or uncertain
3. Update world state when important things happen (meeting NPCs, finding items, changing locations)
4. Keep track of player HP - if it reaches 0, the adventure ends (but you can offer a dramatic recovery)
5. Reference past events and NPCs to maintain continuity
6. Make each session feel like a complete mini-adventure (8-15 exchanges)
7. Be descriptive and immersive - paint vivid scenes with your words
8. When the player asks about their stats, inventory, or the world, use get_world_state to provide accurate information

STORY PACE:
- Turn 1-3: Introduction and scene setting
- Turn 4-8: Rising action, obstacles, choices
- Turn 9-12: Climax, major challenge or discovery
- Turn 13-15: Resolution or cliffhanger ending

Remember: You are the Game Master. Your job is to create an engaging, interactive story that responds to the player's choices while maintaining consistency through the world state.
"""

        super().__init__(instructions=instructions)
        self._initialize_world()

    def _initialize_world(self):
        """Initialize a fresh world state"""
        self.world_state = WorldState(
            player=Character(
                name="Adventurer",
                role="player",
                hp=100,
                max_hp=100,
                attributes={
                    "strength": random.randint(8, 15),
                    "intelligence": random.randint(8, 15),
                    "dexterity": random.randint(8, 15),
                    "luck": random.randint(8, 15),
                },
                inventory=[],
                traits=[],
            ),
            current_location=self.universe_config["initial_location"],
            session_id=str(uuid.uuid4()),
            turn_count=0,
        )
        
        # Add initial location
        self.world_state.locations[self.world_state.current_location] = Location(
            name=self.world_state.current_location,
            description=self.universe_config["initial_location_desc"],
            paths=[],
            visited=True,
        )
        
        logger.info(f"Initialized new game world: {self.world_state.session_id}")

    def _save_world_state(self):
        """Save world state to file"""
        try:
            state_dict = self.world_state.to_dict()
            GAME_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(GAME_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(state_dict, f, indent=2, ensure_ascii=False)
            logger.info("World state saved")
        except Exception as exc:
            logger.error(f"Failed to save world state: {exc}")

    def _load_world_state(self) -> bool:
        """Load world state from file"""
        try:
            if GAME_STATE_PATH.exists():
                with open(GAME_STATE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.world_state = WorldState.from_dict(data)
                logger.info(f"Loaded world state: {self.world_state.session_id}")
                return True
        except Exception as exc:
            logger.error(f"Failed to load world state: {exc}")
        return False

    @function_tool
    async def get_world_state(self, context: RunContext) -> Dict:
        """Get the current world state including player stats, location, NPCs, events, and quests."""
        if not self.world_state:
            self._initialize_world()
        
        self.world_state.turn_count += 1
        state_dict = self.world_state.to_dict()
        logger.info(f"World state retrieved - Turn {self.world_state.turn_count}")
        return state_dict

    @function_tool
    async def update_player_stats(
        self, 
        context: RunContext, 
        hp_change: int = 0,
        attribute: str = "",
        value: int = 0
    ) -> Dict:
        """Update player HP (hp_change can be negative for damage) or modify an attribute."""
        if not self.world_state:
            self._initialize_world()
        
        player = self.world_state.player
        
        if hp_change != 0:
            player.hp = max(0, min(player.max_hp, player.hp + hp_change))
        
        if attribute and value != 0:
            if attribute in player.attributes:
                player.attributes[attribute] = max(1, player.attributes[attribute] + value)
        
        self._save_world_state()
        return {
            "status": "updated",
            "player": player.to_dict(),
        }

    @function_tool
    async def add_to_inventory(self, context: RunContext, item: str) -> Dict:
        """Add an item to the player's inventory."""
        if not self.world_state:
            self._initialize_world()
        
        if item not in self.world_state.player.inventory:
            self.world_state.player.inventory.append(item)
            self.world_state.add_event("item_found", f"Found: {item}")
            self._save_world_state()
            return {
                "status": "added",
                "item": item,
                "inventory": self.world_state.player.inventory,
            }
        return {
            "status": "already_owned",
            "item": item,
        }

    @function_tool
    async def remove_from_inventory(self, context: RunContext, item: str) -> Dict:
        """Remove an item from the player's inventory."""
        if not self.world_state:
            self._initialize_world()
        
        if item in self.world_state.player.inventory:
            self.world_state.player.inventory.remove(item)
            self.world_state.add_event("item_lost", f"Lost: {item}")
            self._save_world_state()
            return {
                "status": "removed",
                "item": item,
                "inventory": self.world_state.player.inventory,
            }
        return {
            "status": "not_found",
            "item": item,
            }

    @function_tool
    async def update_location(
        self,
        context: RunContext,
        location_name: str,
        description: str,
        paths: List[str] = None,
    ) -> Dict:
        """Update or add a location. Mark it as visited if the player moves there."""
        if not self.world_state:
            self._initialize_world()
        
        is_new = location_name not in self.world_state.locations
        self.world_state.locations[location_name] = Location(
            name=location_name,
            description=description,
            paths=paths or [],
            visited=True,
        )
        
        if location_name != self.world_state.current_location:
            self.world_state.current_location = location_name
            self.world_state.add_event(
                "location_change",
                f"Moved to: {location_name}",
                {"is_new": is_new}
            )
        
        self._save_world_state()
        return {
            "status": "updated",
            "location": location_name,
            "is_new": is_new,
        }

    @function_tool
    async def add_npc(
        self,
        context: RunContext,
        name: str,
        role: str,
        attitude: str = "neutral",
        hp: int = 100,
    ) -> Dict:
        """Add or update an NPC character."""
        if not self.world_state:
            self._initialize_world()
        
        is_new = name not in self.world_state.npcs
        self.world_state.npcs[name] = Character(
            name=name,
            role=role,
            attitude=attitude,
            hp=hp,
            max_hp=hp,
        )
        
        if is_new:
            self.world_state.add_event("npc_met", f"Met: {name} ({role})")
        
        self._save_world_state()
        return {
            "status": "added" if is_new else "updated",
            "npc": self.world_state.npcs[name].to_dict(),
        }

    @function_tool
    async def add_event(
        self, context: RunContext, event_type: str, description: str
    ) -> Dict:
        """Record an important event in the game history."""
        if not self.world_state:
            self._initialize_world()
        
        self.world_state.add_event(event_type, description)
        self._save_world_state()
        return {
            "status": "recorded",
            "event_type": event_type,
            "description": description,
        }

    @function_tool
    async def add_quest(
        self,
        context: RunContext,
        title: str,
        description: str,
        status: str = "active",
    ) -> Dict:
        """Add or update a quest."""
        if not self.world_state:
            self._initialize_world()
        
        self.world_state.add_quest(title, description, status)
        self._save_world_state()
        return {
            "status": "added",
            "quest": {
                "title": title,
                "description": description,
                "status": status,
            },
        }

    @function_tool
    async def dice_roll(
        self,
        context: RunContext,
        sides: int = 20,
        modifier: int = 0,
        reason: str = "",
    ) -> Dict:
        """Roll dice for skill checks, combat, or random events. Returns the roll result."""
        roll = random.randint(1, sides)
        total = roll + modifier
        
        # Determine outcome tier
        if sides == 20:  # D20 system
            if total >= 18:
                outcome = "critical_success"
            elif total >= 12:
                outcome = "success"
            elif total >= 8:
                outcome = "partial_success"
            else:
                outcome = "failure"
        else:
            # Generic system
            threshold = sides // 2
            if total >= threshold + (sides // 4):
                outcome = "success"
            elif total >= threshold:
                outcome = "partial_success"
            else:
                outcome = "failure"
        
        result = {
            "roll": roll,
            "modifier": modifier,
            "total": total,
            "outcome": outcome,
            "reason": reason,
        }
        
        logger.info(f"Dice roll: {result}")
        return result

    @function_tool
    async def restart_game(self, context: RunContext) -> Dict:
        """Start a completely fresh adventure. Use this when the player explicitly requests to restart."""
        self._initialize_world()
        self._save_world_state()
        return {
            "status": "restarted",
            "message": "A new adventure begins!",
        }

    async def send_initial_greeting(self):
        """Send the opening Game Master greeting when audio is ready."""
        if not self._session:
            return
        
        # Get initial world state to include in greeting
        if not self.world_state:
            self._initialize_world()
        
        location = self.world_state.locations.get(
            self.world_state.current_location,
            Location(
                name=self.world_state.current_location,
                description=self.universe_config["initial_location_desc"],
            )
        )
        
        greeting = (
            f"Welcome, adventurer, to the world of {self.universe_config['name']}. "
            f"{location.description} "
            "The story begins now. What do you do?"
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

    # Create Game Master agent (default to fantasy universe)
    # You can change this to "sci_fi" or "post_apocalypse" for different universes
    game_master = GameMasterAgent(universe="fantasy")
    game_master._session = session
    game_master._room = ctx.room

    await session.start(
        agent=game_master,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()
    
    import asyncio

    await asyncio.sleep(1.0)
    await game_master.send_initial_greeting()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
