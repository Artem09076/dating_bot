import asyncio
import logging.config

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from consumer.logger import logger
from consumer.storage.db import async_session
from src.model.model import (
    BehaviorRating,
    CombinedRating,
    Conversation,
    Like,
    PrimaryRating,
    User,
)

app = Celery(
    "tasks", broker=settings.celery_broker_url, backend=settings.celery_result_backend
)

app.conf.update(
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,
    broker_connection_retry_delay=5,
)


async def calculate_user_rating(user_id: int, db: AsyncSession):
    user = await db.get(User, user_id)
    if not user:
        logger.error(f"Пользователь с id {user_id} не найден.")
        return

    completeness_score = 1.0 if user.profile_filled else 0.5
    photo_score = 1.0 if user.photo else 0.0
    preference_match_score = (
        1.0
        if (user.preferred_age_min and user.preferred_age_max and user.preferred_gender)
        else 0.0
    )

    primary_rating = await db.scalar(
        select(PrimaryRating).where(PrimaryRating.user_id == user.id)
    )
    if not primary_rating:
        primary_rating = PrimaryRating(user_id=user.id)
    primary_rating.completeness_score = completeness_score
    primary_rating.photo_score = photo_score
    primary_rating.preference_match_score = preference_match_score
    db.add(primary_rating)

    likes_received = (
        await db.scalar(select(func.count(Like.id)).where(Like.to_user_id == user.id))
        or 0
    )
    total_likes = (
        await db.scalar(select(func.count(Like.id)).where(Like.from_user_id == user.id))
        or 0
    )
    mutual_likes = (
        await db.scalar(
            select(func.count(Like.id)).where(
                Like.from_user_id == user.id, Like.is_mutual == True
            )
        )
        or 0
    )
    conversations_started = (
        await db.scalar(
            select(func.count(Conversation.id)).where(
                (Conversation.user1_id == user.id) | (Conversation.user2_id == user.id)
            )
        )
        or 0
    )

    likes_skipped_ratio = (mutual_likes / total_likes) if total_likes > 0 else 0.0

    behavior_rating = await db.scalar(
        select(BehaviorRating).where(BehaviorRating.user_id == user.id)
    )
    if not behavior_rating:
        behavior_rating = BehaviorRating(user_id=user.id)
    behavior_rating.likes_received = likes_received
    behavior_rating.likes_skipped_ratio = likes_skipped_ratio
    behavior_rating.mutual_likes = mutual_likes
    behavior_rating.post_match_conversations = conversations_started
    behavior_rating.active_hours_score = 1.0
    db.add(behavior_rating)

    combined_score = (
        (primary_rating.completeness_score * 0.3)
        + (primary_rating.photo_score * 0.2)
        + (primary_rating.preference_match_score * 0.2)
        + (behavior_rating.likes_received * 0.1)
        + (behavior_rating.likes_skipped_ratio * 0.05)
        + (behavior_rating.mutual_likes * 0.1)
        + (behavior_rating.post_match_conversations * 0.05)
    )

    combined_rating = await db.scalar(
        select(CombinedRating).where(CombinedRating.user_id == user.id)
    )
    if not combined_rating:
        combined_rating = CombinedRating(user_id=user.id)
    combined_rating.score = combined_score
    db.add(combined_rating)

    await db.commit()



async def recalculate_all_users():
    async with async_session() as db:
        users = await db.execute(select(User.id))
        user_ids = [row[0] for row in users.fetchall()]

    for user_id in user_ids:
        async with async_session() as db:
            try:
                await calculate_user_rating(user_id, db)
            except Exception as e:
                logger.error(f"Ошибка при пересчете рейтинга для user_id={user_id}: {e}")


@app.task
def periodic_recalculate_ratings():
    loop = asyncio.get_event_loop()
    loop.create_task(recalculate_all_users())


app.conf.beat_schedule = {
    "recalculate-all-user-ratings-every-5-minutes": {
        "task": "script.calculate_ratings.periodic_recalculate_ratings",
        "schedule": crontab(minute='*/5'),
    },
}
