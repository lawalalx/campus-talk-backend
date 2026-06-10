from collections import defaultdict
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MessageSentiment, SentimentLabel


POSITIVE_WORDS = {
    "good", "great", "excellent", "love", "happy", "awesome", "amazing", "best", "nice", "cool", "supportive",
}
NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "hate", "sad", "angry", "worst", "broken", "frustrated", "depressed", "anxious",
}


def analyze_text(text: str) -> tuple[float, SentimentLabel]:
    tokens = [token.strip(".,!?;:\"'()[]{}").lower() for token in text.split() if token.strip()]
    if not tokens:
        return 0.0, SentimentLabel.NEUTRAL

    pos_hits = sum(1 for token in tokens if token in POSITIVE_WORDS)
    neg_hits = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    score = (pos_hits - neg_hits) / max(len(tokens), 1)

    if score > 0.05:
        return score, SentimentLabel.POSITIVE
    if score < -0.05:
        return score, SentimentLabel.NEGATIVE
    return score, SentimentLabel.NEUTRAL


async def store_message_sentiment(
    session: AsyncSession,
    *,
    message_id: str,
    conversation_id: str,
    institution_id: str | None,
    content: str,
) -> MessageSentiment:
    score, label = analyze_text(content)
    sentiment = MessageSentiment(
        message_id=message_id,
        conversation_id=conversation_id,
        institution_id=institution_id,
        score=score,
        label=label,
        analyzed_text=content,
    )
    session.add(sentiment)
    await session.commit()
    await session.refresh(sentiment)
    return sentiment


async def get_sentiment_summary_for_institution(
    session: AsyncSession,
    *,
    institution_id: str,
    limit: int = 50,
) -> dict:
    stmt = (
        select(MessageSentiment)
        .where(MessageSentiment.institution_id == institution_id)
        .order_by(MessageSentiment.analyzed_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()

    if not rows:
        return {
            "institution_id": institution_id,
            "sample_size": 0,
            "average_score": 0.0,
            "distribution": {"positive": 0, "neutral": 0, "negative": 0},
            "recent_entries": [],
        }

    distribution = defaultdict(int)
    total_score = 0.0
    for row in rows:
        distribution[row.label.value] += 1
        total_score += row.score

    return {
        "institution_id": institution_id,
        "sample_size": len(rows),
        "average_score": total_score / len(rows),
        "distribution": {
            "positive": distribution.get("positive", 0),
            "neutral": distribution.get("neutral", 0),
            "negative": distribution.get("negative", 0),
        },
        "recent_entries": [
            {
                "message_id": row.message_id,
                "conversation_id": row.conversation_id,
                "score": row.score,
                "label": row.label.value,
                "text": row.analyzed_text,
                "analyzed_at": row.analyzed_at,
            }
            for row in rows
        ],
    }
