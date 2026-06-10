# /backend/app/agent/briefing.py
import json

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_client = AsyncOpenAI(api_key=settings.openai_api_key)
_VALID_URGENCY = {"low", "medium", "high"}

_SYSTEM_PROMPT = """You are an assistant that briefs human customer-service agents.
Given a cross-channel conversation history (oldest first), summarize the
customer's situation for an agent who has not seen it yet.

Respond with strict JSON only, in this exact shape:
{"summary": "...", "urgency": "low" | "medium" | "high", "recommended_action": "..."}

- summary: 1-3 sentences, what the customer needs and the current state.
- urgency: "high" if the customer is angry, blocked, or reports a safety
  issue; "medium" if there is an open problem but no immediate risk; "low"
  for general inquiries or resolved issues.
- recommended_action: one concrete next step for the agent.
"""


async def generate_briefing(history: list[dict]) -> dict:
    """Summarize a cross-channel conversation for a human agent using GPT-4o-mini."""
    default = {
        "summary": "No conversation history available.",
        "urgency": "medium",
        "recommended_action": "Review the conversation history manually.",
    }
    if not history:
        return default

    transcript = "\n".join(
        f"[{h['channel']}] {h['role']}: {h['text']}" for h in history
    )

    try:
        resp = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": transcript[:6000]},
            ],
            max_tokens=300,
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        if data.get("urgency") not in _VALID_URGENCY:
            data["urgency"] = "medium"
        return {
            "summary": data.get("summary") or default["summary"],
            "urgency": data["urgency"],
            "recommended_action": data.get("recommended_action") or default["recommended_action"],
        }
    except Exception as exc:
        logger.warning("Briefing generation failed: %s", exc)
        return default
