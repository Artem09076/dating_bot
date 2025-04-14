from sqlalchemy import select, and_
from consumer.storage.db import async_session
from src.model.model import User
from config.settings import settings
import msgpack
from aio_pika import ExchangeType, Message
from src.storage.rabbit import channel_pool


async def find_candidates(body):
    user_id = body.get("user_id")

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        filters = and_(
            User.gender == user.preferred_gender,
            User.age >= user.preferred_age_min,
            User.age <= user.preferred_age_max,
            User.city == user.preferred_city,
            User.id != user.id
        )

        candidates_result = await db.execute(select(User).where(filters).limit(10))
        candidates = candidates_result.scalars().all()

        candidates_data = [c.to_dict() for c in candidates]

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange("user_receipts", ExchangeType.TOPIC, durable=True)
        user_queue = await channel.declare_queue(settings.USER_QUEUE.format(user_id=user_id), durable=True)

        await user_queue.bind(exchange, routing_key=settings.USER_QUEUE.format(user_id=user_id))

        await exchange.publish(
            Message(msgpack.packb({
                "action": "show_candidates",
                "user_id": user_id,
                "candidates": candidates_data
            })),
            routing_key=settings.USER_QUEUE.format(user_id=user_id)
        )
