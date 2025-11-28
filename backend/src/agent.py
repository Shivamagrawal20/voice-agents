import json
import logging
import uuid
from dataclasses import dataclass, field
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

CATALOG_PATH = (
    Path(__file__).resolve().parents[2] / "shared-data" / "day7_catalog.json"
)
ORDERS_PATH = (
    Path(__file__).resolve().parents[2] / "shared-data" / "day7_orders.json"
)
FALCON_PANTRY = "Falcon Pantry"


def _load_json(path: Path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as exc:
            logger.warning("Unable to parse %s: %s", path, exc)
    return default


def _save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


@dataclass
class CatalogItem:
    id: str
    name: str
    category: str
    price: float
    unit: str
    brand: Optional[str] = None
    size: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict) -> "CatalogItem":
        return cls(
            id=data["id"],
            name=data["name"],
            category=data.get("category", "General"),
            price=float(data.get("price", 0)),
            unit=data.get("unit", ""),
            brand=data.get("brand"),
            size=data.get("size"),
            tags=data.get("tags") or [],
        )

    def to_public_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "unit": self.unit,
            "brand": self.brand,
            "size": self.size,
            "tags": self.tags,
        }


@dataclass
class CartLine:
    item: CatalogItem
    quantity: float
    note: str = ""

    def subtotal(self) -> float:
        return round(self.item.price * self.quantity, 2)


RECIPES = {
    "peanut butter sandwich": {
        "items": [
            {"item_id": "whole_wheat_bread", "quantity": 1},
            {"item_id": "peanut_butter", "quantity": 1},
            {"item_id": "strawberry_jam", "quantity": 1},
        ],
        "servings": 4,
        "description": "Classic PB&J sandwiches.",
    },
    "pasta night": {
        "items": [
            {"item_id": "spaghetti_pasta", "quantity": 1},
            {"item_id": "marinara_sauce", "quantity": 1},
            {"item_id": "fresh_spinach", "quantity": 1},
        ],
        "servings": 2,
        "description": "Pantry pasta with greens.",
    },
    "quick breakfast": {
        "items": [
            {"item_id": "free_range_eggs", "quantity": 1},
            {"item_id": "whole_wheat_bread", "quantity": 1},
            {"item_id": "cold_brew_coffee", "quantity": 1},
        ],
        "servings": 2,
        "description": "Eggs on toast with cold brew.",
    },
    "game night snacks": {
        "items": [
            {"item_id": "tortilla_chips", "quantity": 1},
            {"item_id": "fresh_salsa", "quantity": 1},
            {"item_id": "rotisserie_chicken", "quantity": 1},
        ],
        "servings": 4,
        "description": "Shareable snacks and protein.",
    },
}


class GroceryOrderingAgent(Agent):
    """Friendly food & grocery ordering concierge."""

    def __init__(self, store_name: str = FALCON_PANTRY) -> None:
        self.store_name = store_name
        self.catalog: Dict[str, CatalogItem] = self._load_catalog()
        self.cart: Dict[str, CartLine] = {}
        self.last_order: Optional[Dict] = None

        instructions = f"""
You are Sona, the upbeat voice concierge for {self.store_name}, a same-day grocery & prepared food service. 

CONVERSATION FLOW:
1. Greet the caller, mention {self.store_name}, and state you can help with groceries, snacks, or easy meal ingredient bundles.
2. Clarify item details (brand, size, quantity, dietary tags) before adding anything to the cart. Use get_catalog_items when you need product details.
3. For requests like "ingredients for X" or "meal for two", pick the closest recipe by calling apply_recipe. Confirm what you added and why.
4. Keep the cart current:
   - add_item_to_cart to add new items.
   - update_cart_item for quantity changes (set quantity=0 or use remove_item_from_cart to drop items).
   - list_cart whenever the caller asks what's inside, before checkout, or when the total matters.
5. Pricing:
   - All prices are USD. Quote running totals briefly after changes.
   - If a request would exceed a budget they mention, warn them and suggest alternatives from the catalog.
6. Checkout:
   - When the caller says they are done, read back the cart by calling list_cart, collect their name plus delivery notes, then call place_order.
   - Confirm the order number and that status starts as "received" for tracking.

AVAILABLE TOOLS (always call them instead of guessing):
- get_catalog_items(category:str="", tag:str="", search:str="", limit:int=5) -> show catalog matches. Use search parameter to find items by name (e.g., "milk", "eggs"). Returns status="error" if catalog unavailable - in that case, apologize and suggest they browse by category or ask for specific items.
- add_item_to_cart(item_id:str, quantity:float, note:str="") -> add or stack items.
- update_cart_item(item_id:str, quantity:float, note:str="") -> change quantity (<=0 removes).
- remove_item_from_cart(item_id:str) -> delete a line.
- list_cart() -> structured view with totals.
- apply_recipe(recipe_name:str, servings:int=1, note:str="") -> add a predefined ingredient bundle.
- place_order(customer_name:str, fulfillment:str, notes:str="") -> saves the order JSON; only run once the caller approves the cart.

IMPORTANT: If get_catalog_items returns status="error", do NOT say "technical difficulties". Instead, apologize briefly and offer to help them add items by name or suggest browsing categories like "Groceries", "Pantry", "Prepared Food", or "Snacks".

CATALOG QUICK GLANCE (use tools for full details):
- Whole Wheat Bread $4/loaf (Harvest Lane)
- Free-Range Eggs $4.75/dozen (Sunrise Farms)
- Organic 2% Milk $5.25 half gallon
- Creamy Peanut Butter $6.50/jar
- Roasted Garlic Marinara $5.50/jar
- Bronze-Cut Spaghetti $2.75/box
- Herb Rotisserie Chicken $12.99 each
- Super Greens Salad Kit $9.50 kit
- Vanilla Cold Brew $7.99 bottle
- Blue Corn Chips + Roasted Salsa combo

STYLE:
- Keep answers under two punchy sentences whenever possible.
- Confirm every cart change aloud.
- If a request is unclear, ask a focused follow-up rather than assuming.
- Mention Murf Falcon powering your voice when thanking them at the end.
"""

        super().__init__(instructions=instructions)
        self._session: Optional[AgentSession] = None
        self._room = None

    def _load_catalog(self) -> Dict[str, CatalogItem]:
        logger.info("Loading catalog from: %s", CATALOG_PATH)
        if not CATALOG_PATH.exists():
            logger.error("Catalog file does not exist at %s", CATALOG_PATH)
            return {}
        
        raw_items = _load_json(CATALOG_PATH, default=[])
        if not raw_items:
            logger.error("Catalog file is empty or could not be parsed at %s", CATALOG_PATH)
            return {}
        
        if not isinstance(raw_items, list):
            logger.error("Catalog file does not contain a list at %s", CATALOG_PATH)
            return {}
            
        catalog = {}
        for item in raw_items:
            try:
                if not isinstance(item, dict):
                    logger.warning("Skipping non-dict catalog entry: %s", item)
                    continue
                catalog[item["id"]] = CatalogItem.from_dict(item)
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping catalog entry missing key or invalid data %s: %s", exc, item)
        
        if not catalog:
            logger.error("No valid catalog items loaded from %s (tried %d entries)", CATALOG_PATH, len(raw_items))
        else:
            logger.info("Successfully loaded %d catalog items from %s", len(catalog), CATALOG_PATH)
        return catalog

    def _ensure_item(self, item_id: str) -> CatalogItem:
        item = self.catalog.get(item_id)
        if not item:
            raise ValueError(f"Unknown item_id '{item_id}'.")
        return item

    def _cart_total(self) -> float:
        total = sum(line.subtotal() for line in self.cart.values())
        return round(total, 2)

    def _serialize_cart(self) -> List[Dict]:
        return [
            {
                "itemId": line.item.id,
                "name": line.item.name,
                "quantity": line.quantity,
                "unitPrice": line.item.price,
                "subtotal": line.subtotal(),
                "note": line.note,
            }
            for line in self.cart.values()
        ]

    def _persist_order(self, order: Dict) -> None:
        orders = _load_json(ORDERS_PATH, default=[])
        orders.append(order)
        _save_json(ORDERS_PATH, orders)

    @function_tool
    async def get_catalog_items(
        self, context: RunContext, category: str = "", tag: str = "", search: str = "", limit: int = 5
    ):
        """List catalog items with optional category, tag, or name search filters."""
        if not self.catalog:
            logger.error("Catalog is empty - cannot retrieve items")
            return {
                "status": "error",
                "message": "Catalog is not available. Please check the catalog file.",
                "count": 0,
                "items": [],
            }

        # be defensive about limit type (LLM may pass it as a string)
        try:
            limit_value = int(limit)
        except (TypeError, ValueError):
            limit_value = 5

        filtered: List[CatalogItem] = []
        normalized_category = category.strip().lower() if category else ""
        normalized_tag = tag.strip().lower() if tag else ""
        normalized_search = search.strip().lower() if search else ""

        for item in self.catalog.values():
            # Filter by category if provided
            if normalized_category and normalized_category not in item.category.lower():
                continue
            # Filter by tag if provided
            if normalized_tag and normalized_tag not in [t.lower() for t in item.tags]:
                continue
            # Search in name, id, or brand if search term provided
            if normalized_search:
                item_name_lower = item.name.lower()
                item_id_lower = item.id.lower()
                item_brand_lower = (item.brand or "").lower()
                if (normalized_search not in item_name_lower and 
                    normalized_search not in item_id_lower and
                    normalized_search not in item_brand_lower):
                    continue
            filtered.append(item)

        # If filters didn't match anything, return all items (up to limit)
        if not filtered and (normalized_category or normalized_tag or normalized_search):
            filtered = list(self.catalog.values())

        limited = filtered[: max(1, min(limit_value, 20))]  # Increased max to 20
        
        try:
            items_data = [entry.to_public_dict() for entry in limited]
            result = {
                "status": "success",
                "count": len(limited),
                "items": items_data,
            }
            # Log items to console as JSON for debugging
            logger.info("Catalog items retrieved: %s", json.dumps(result, indent=2))
            return result
        except Exception as exc:
            logger.error("Error serializing catalog items: %s", exc)
            return {
                "status": "error",
                "message": f"Error processing catalog items: {str(exc)}",
                "count": 0,
                "items": [],
            }

    @function_tool
    async def add_item_to_cart(
        self, context: RunContext, item_id: str, quantity: float = 1.0, note: str = ""
    ):
        """Add a catalog item to the cart or increase its quantity."""
        if quantity <= 0:
            return {"status": "error", "message": "Quantity must be positive."}
        try:
            item = self._ensure_item(item_id)
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

        current_qty = self.cart[item_id].quantity if item_id in self.cart else 0
        self.cart[item_id] = CartLine(
            item=item, quantity=current_qty + quantity, note=note.strip()
            )
        return {
            "status": "added",
            "item": item.to_public_dict(),
            "quantity": self.cart[item_id].quantity,
            "cartTotal": self._cart_total(),
        }

    @function_tool
    async def update_cart_item(
        self, context: RunContext, item_id: str, quantity: float, note: str = ""
    ):
        """Update the quantity of an existing cart line. Set quantity<=0 to remove."""
        if item_id not in self.cart:
            return {"status": "error", "message": "Item not currently in cart."}

        if quantity <= 0:
            self.cart.pop(item_id, None)
            return {"status": "removed", "cartTotal": self._cart_total()}

        line = self.cart[item_id]
        line.quantity = quantity
        if note.strip():
            line.note = note.strip()
        return {
            "status": "updated",
            "item": line.item.to_public_dict(),
            "quantity": line.quantity,
            "cartTotal": self._cart_total(),
        }

    @function_tool
    async def remove_item_from_cart(self, context: RunContext, item_id: str):
        """Remove an item from the cart entirely."""
        if item_id not in self.cart:
            return {"status": "not_found"}
        self.cart.pop(item_id)
        return {"status": "removed", "cartTotal": self._cart_total()}

    @function_tool
    async def list_cart(self, context: RunContext):
        """View the current cart contents and total."""
        cart_data = {
            "items": self._serialize_cart(),
            "total": self._cart_total(),
        }
        # Log cart items to console as JSON for debugging
        logger.info("Cart contents: %s", json.dumps(cart_data, indent=2))
        return cart_data

    @function_tool
    async def apply_recipe(
        self,
        context: RunContext,
        recipe_name: str,
        servings: int = 1,
        note: str = "",
    ):
        """Add the closest recipe bundle (ingredients for X)."""
        normalized = recipe_name.strip().lower()
        recipe_key = None
        for key in RECIPES.keys():
            if normalized in key or key in normalized:
                recipe_key = key
                break
        if not recipe_key:
            return {"status": "not_found", "message": "Recipe not available."}

        recipe = RECIPES[recipe_key]
        applied_items: List[Dict] = []
        multiplier = max(1, servings) / recipe["servings"]
        for entry in recipe["items"]:
            item = self.catalog.get(entry["item_id"])
            if not item:
                continue
            qty = round(entry["quantity"] * multiplier, 2)
            existing_qty = self.cart[entry["item_id"]].quantity if entry["item_id"] in self.cart else 0
            self.cart[entry["item_id"]] = CartLine(
                item=item,
                quantity=existing_qty + qty,
                note=note.strip() or recipe["description"],
            )
            applied_items.append(
                {"item": item.to_public_dict(), "addedQuantity": qty}
            )

        return {
            "status": "applied",
            "recipe": recipe_key,
            "items": applied_items,
            "cartTotal": self._cart_total(),
        }

    @function_tool
    async def place_order(
        self,
        context: RunContext,
        customer_name: str,
        fulfillment: str,
        notes: str = "",
    ):
        """Persist the current cart as an order JSON record."""
        if not self.cart:
            return {"status": "error", "message": "Cart is empty."}

        order = {
            "orderId": f"ORD-{uuid.uuid4().hex[:8].upper()}",
            "placedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "status": "received",
            "customer": {
                "name": customer_name.strip() or "Guest",
                "fulfillment": fulfillment.strip(),
                "notes": notes.strip(),
            },
            "items": self._serialize_cart(),
            "total": self._cart_total(),
        }

        self._persist_order(order)
        self.last_order = order
        self.cart.clear()

        return {"status": "placed", "order": order}

    async def send_initial_greeting(self):
        """Send the opening grocery greeting when audio is ready."""
        if not self._session:
            return
        greeting = (
            f"Hi there, you’ve reached {self.store_name}. "
            "I’m Sona, and I can build your grocery or meal kit order in minutes. "
            "What are you in the mood for today?"
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

    grocery_agent = GroceryOrderingAgent()
    grocery_agent._session = session
    grocery_agent._room = ctx.room

    await session.start(
        agent=grocery_agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()
    
    import asyncio

    await asyncio.sleep(1.0)
    await grocery_agent.send_initial_greeting()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))


