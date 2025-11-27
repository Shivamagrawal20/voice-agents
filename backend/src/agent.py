import json
import logging
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

FRAUD_CASES_PATH = (
    Path(__file__).resolve().parents[2] / "shared-data" / "day6_fraud_cases.json"
)
MAX_VERIFICATION_ATTEMPTS = 2
VALID_FINAL_STATUSES = {"confirmed_safe", "confirmed_fraud", "verification_failed"}


def _load_cases() -> List[Dict]:
    if FRAUD_CASES_PATH.exists():
        try:
            with open(FRAUD_CASES_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)
                if isinstance(data, list):
                    return data
        except json.JSONDecodeError as exc:
            logger.warning("Unable to parse fraud cases at %s: %s", FRAUD_CASES_PATH, exc)
    return []


def _save_cases(cases: List[Dict]) -> None:
    FRAUD_CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FRAUD_CASES_PATH, "w", encoding="utf-8") as file:
        json.dump(cases, file, indent=2, ensure_ascii=False)


def _normalize(text: str) -> str:
    return text.strip().lower()


def _mask_case(case: Dict) -> Dict:
    return {
        "caseId": case.get("caseId"),
        "userName": case.get("userName"),
        "securityIdentifier": case.get("securityIdentifier"),
        "securityQuestion": case.get("securityQuestion"),
        "cardMask": case.get("cardMask"),
        "transactionAmount": case.get("transactionAmount"),
        "currency": case.get("currency", "USD"),
        "transactionName": case.get("transactionName"),
        "transactionCategory": case.get("transactionCategory"),
        "transactionSource": case.get("transactionSource"),
        "location": case.get("location"),
        "transactionTime": case.get("transactionTime"),
        "channel": case.get("channel"),
        "status": case.get("status", "pending_review"),
        "outcomeNote": case.get("outcomeNote", ""),
    }


def _find_case_by_username(user_name: str) -> Optional[Dict]:
    normalized = _normalize(user_name)
    for case in _load_cases():
        if _normalize(case.get("userName", "")) == normalized:
            return case
    return None


class FraudAlertAgent(Agent):
    """Fraud alert representative that audits a single case per call."""

    def __init__(self, bank_name: str = "Falcon National Bank") -> None:
        self.bank_name = bank_name
        self.active_case: Optional[Dict] = None
        self.is_verified = False
        self.verification_attempts = 0

        instructions = f"""
You are Ava, a calm fraud prevention specialist for {self.bank_name}. Calls are demo-only, so keep language professional, reassuring, and brief.

CALL FLOW YOU MUST FOLLOW:
1. INTRO: Immediately introduce yourself as the {self.bank_name} fraud department calling about a suspicious card transaction and ask for the customer's preferred first name.
2. CASE LOOKUP: After the caller gives a name, call load_fraud_case(user_name). If no case is found, explain that nothing is pending and end politely.
3. SECURITY: When you have a case, read the provided security question word-for-word. Never share the stored answer. After the caller responds, call verify_security_answer(answer). If it returns verified=false, kindly let them know how many attempts remain (max {MAX_VERIFICATION_ATTEMPTS}) and re-ask. If they fail all attempts, stop and call update_case_status(status="verification_failed", note=...).
4. BRIEFING: Once verified, recap the suspicious charge. Mention the merchant, amount with currency, masked card, timestamp, location, and channel from the tool output. Remind them you will not ask for full card numbers, PINs, or passwords.
5. DECISION: Ask if they recognize the charge. A "yes" means the transaction is safe; a "no" (or uncertainty) means it is fraudulent. Keep them focused on a direct answer.
6. PERSISTENCE: Always call update_case_status once the disposition is known:
   - confirmed_safe + note describing their confirmation.
   - confirmed_fraud + note describing next steps (e.g., card blocked, dispute raised).
   - verification_failed when identity could not be verified.
7. WRAP-UP: Verbally summarize the outcome, next actions, and thank them before ending the call.

TOOLS AVAILABLE:
- load_fraud_case(user_name:str) -> loads the pending case for that customer. Only proceed with the information returned by this tool.
- verify_security_answer(answer:str) -> validates the caller's response. Never guess or announce the stored answer; rely on this tool's boolean.
- update_case_status(status:str, note:str) -> persists the final state back to the database. Status must be one of confirmed_safe, confirmed_fraud, or verification_failed.

BEHAVIORAL GUARDRAILS:
- Never request full PAN, CVV, PIN, passwords, OTPs, or any sensitive secret beyond the provided security question.
- Stay empathetic, avoid alarming language, and speak in concise statements suitable for audio.
- If the caller digresses, gently bring the conversation back to resolving the fraud alert.
- If the caller confirms multiple attempts or new suspicious activity, document that in your note but still complete the single provided case.
- If the caller asks about data sources, clarify that this is a sandbox demo using fake accounts.
"""

        super().__init__(instructions=instructions)
        self._session: Optional[AgentSession] = None
        self._room = None

    def _ensure_active_case(self) -> Dict:
        if not self.active_case:
            raise ValueError("No fraud case loaded.")
        return self.active_case

    @function_tool
    async def load_fraud_case(self, context: RunContext, user_name: str):
        """Load a fraud case for the provided customer name."""
        if not user_name.strip():
            return {"status": "error", "message": "Customer name is required."}

        case = _find_case_by_username(user_name)
        if not case:
            logger.info("No fraud case found for user=%s", user_name)
            self.active_case = None
            self.is_verified = False
            self.verification_attempts = 0
            return {"status": "not_found"}

        self.active_case = case
        self.is_verified = False
        self.verification_attempts = 0
        logger.info(
            "Loaded fraud case %s for user=%s", case.get("caseId"), case.get("userName")
        )
        return {"status": "loaded", "case": _mask_case(case)}

    @function_tool
    async def verify_security_answer(self, context: RunContext, answer: str):
        """Validate the caller's response to the stored security question."""
        try:
            case = self._ensure_active_case()
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

        if not answer.strip():
            return {"status": "error", "message": "An answer is required to verify identity."}

        self.verification_attempts += 1
        expected = _normalize(case.get("securityAnswer", ""))
        provided = _normalize(answer)
        is_match = bool(expected) and provided == expected

        if is_match:
            self.is_verified = True
            logger.info(
                "Security verification succeeded for case %s", case.get("caseId")
            )
            return {
                "status": "verified",
                "verified": True,
                "attempts_used": self.verification_attempts,
                "attempts_left": max(0, MAX_VERIFICATION_ATTEMPTS - self.verification_attempts),
            }

        remaining = max(0, MAX_VERIFICATION_ATTEMPTS - self.verification_attempts)
        self.is_verified = False
        logger.info(
            "Security verification failed for case %s (remaining=%s)",
            case.get("caseId"),
            remaining,
        )
        return {
            "status": "not_verified",
            "verified": False,
            "attempts_used": self.verification_attempts,
            "attempts_left": remaining,
        }

    @function_tool
    async def update_case_status(self, context: RunContext, status: str, note: str):
        """Persist the final outcome of the fraud review."""
        try:
            case = self._ensure_active_case()
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

        normalized_status = status.strip().lower()
        if normalized_status not in VALID_FINAL_STATUSES:
            return {
                "status": "error",
                "message": f"Status must be one of {', '.join(sorted(VALID_FINAL_STATUSES))}.",
            }

        if not note.strip():
            return {"status": "error", "message": "An outcome note is required."}

        cases = _load_cases()
        updated_case = None
        for record in cases:
            if record.get("caseId") == case.get("caseId"):
                record["status"] = normalized_status
                record["outcomeNote"] = note.strip()
                record["updatedAt"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                updated_case = record
                break

        if not updated_case:
            return {
                "status": "error",
                "message": f"Could not locate case {case.get('caseId')} for update.",
            }

        _save_cases(cases)
        self.active_case = updated_case
        logger.info(
            "Updated fraud case %s -> status=%s",
            updated_case.get("caseId"),
            normalized_status,
        )
        return {
            "status": "updated",
            "case": _mask_case(updated_case),
        }

    async def send_initial_greeting(self):
        """Send the opening fraud-alert greeting when audio is ready."""
        if not self._session:
            return
        greeting = (
            f"Hello, this is Ava with {self.bank_name}'s fraud protection team. "
            "I'm calling about a suspicious charge on your card. "
            "Could I please confirm the name you use on the account before we continue?"
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

    fraud_agent = FraudAlertAgent()
    fraud_agent._session = session
    fraud_agent._room = ctx.room

    await session.start(
        agent=fraud_agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()
    
    import asyncio

    await asyncio.sleep(1.0)
    await fraud_agent.send_initial_greeting()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))


