# /backend/app/agent/sentiment.py
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_client = AsyncOpenAI(api_key=settings.openai_api_key)
_VALID = {"positive", "neutral", "negative"}


async def classify_sentiment(text: str) -> str:
    """Classify user message sentiment using GPT-4o-mini. Fast, cheap, bilingual."""
    try:
        resp = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a sentiment classifier. "
                        "Respond with exactly one word: positive, neutral, or negative. "
                        "No punctuation. No explanation."
                    ),
                },
                {"role": "user", "content": text[:500]},
            ],
            max_tokens=5,
            temperature=0,
        )
        word = resp.choices[0].message.content.strip().lower()
        return word if word in _VALID else "neutral"
    except Exception as exc:
        logger.warning("Sentiment classification failed: %s", exc)
        return "neutral"
