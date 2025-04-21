from consumer.storage.celery import celery_app
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.model.model import User, PrimaryRating, BehaviorRating, CombinedRating, Like, Conversation
from consumer.storage.db import async_session
import asyncio
from consumer.storage import rabbit
from aio_pika import ExchangeType
import aio_pika
import msgpack
from config.settings import settings
from consumer.logger import LOGGING_CONFIG, logger
import logging.config

@celery_app.task
async def calculate_user_ratings(body: dict):
    logger.info("Прием запроса на расчет рейтинга для пользователя", body)
    await _calculate_user_ratings(body)


async def _calculate_user_ratings(body: dict):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info("Обработка запроса на расчет рейтинга", body)
    user_id = body["id"]
    async with async_session() as db:

        user = await db.get(User, user_id)
        if not user:
            logger.error(f"Пользователь с id {user_id} не найден.")
            return

        completeness_score = 1.0 if user.profile_filled else 0.5
        photo_score = 1.0 if user.photo else 0.0

        preference_match_score = 0.0
        if user.preferred_age_min and user.preferred_age_max and user.preferred_gender:
            preference_match_score = 1.0

        primary_rating = await db.scalar(select(PrimaryRating).where(PrimaryRating.user_id == user.id))
        if not primary_rating:
            primary_rating = PrimaryRating(user_id=user.id)

        primary_rating.completeness_score = completeness_score
        primary_rating.photo_score = photo_score
        primary_rating.preference_match_score = preference_match_score
        db.add(primary_rating)

        likes_received = await db.scalar(select(func.count(Like.id)).where(Like.to_user_id == user.id)) or 0
        total_likes = await db.scalar(select(func.count(Like.id)).where(Like.from_user_id == user.id)) or 0
        mutual_likes = await db.scalar(select(func.count(Like.id)).where(Like.from_user_id == user.id, Like.is_mutual == True)) or 0
        conversations_started = await db.scalar(select(func.count(Conversation.id)).where(
            (Conversation.user1_id == user.id) | (
                Conversation.user2_id == user.id)
        )) or 0

        likes_skipped_ratio = (
            mutual_likes / total_likes) if total_likes > 0 else 0.0
        active_hours_score = 1.0

        behavior_rating = await db.scalar(select(BehaviorRating).where(BehaviorRating.user_id == user.id))
        if not behavior_rating:
            behavior_rating = BehaviorRating(user_id=user.id)

        behavior_rating.likes_received = likes_received
        behavior_rating.likes_skipped_ratio = likes_skipped_ratio
        behavior_rating.mutual_likes = mutual_likes
        behavior_rating.post_match_conversations = conversations_started
        behavior_rating.active_hours_score = active_hours_score
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

        combined_rating = await db.scalar(select(CombinedRating).where(CombinedRating.user_id == user.id))
        if not combined_rating:
            combined_rating = CombinedRating(user_id=user.id)

        combined_rating.score = combined_score
        db.add(combined_rating)
        await db.commit()

        response_body = {
            "status": "success",
            "user_id": user_id,
            "primary_rating": {
                "completeness_score": primary_rating.completeness_score,
                "photo_score": primary_rating.photo_score,
                "preference_match_score": primary_rating.preference_match_score,
            },
            "behavior_rating": {
                "likes_received": behavior_rating.likes_received,
                "likes_skipped_ratio": behavior_rating.likes_skipped_ratio,
                "mutual_likes": behavior_rating.mutual_likes,
                "post_match_conversations": behavior_rating.post_match_conversations,
                "active_hours_score": behavior_rating.active_hours_score,
            },
            "combined_rating": combined_rating.score if combined_rating else None
        }

    async with rabbit.channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        logger.info(
            f"Отправка сообщения для пользователя {user_id} в очередь {settings.USER_QUEUE.format(user_id=user_id)}")

        await exchange.publish(
            aio_pika.Message(
                body=msgpack.packb(response_body),
            ),
            routing_key=settings.USER_QUEUE.format(user_id=user_id),
        )
        logger.info(
            f"Сообщение успешно отправлено в очередь для пользователя {user_id}")
