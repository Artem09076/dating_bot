import logging.config

import msgpack
from aio_pika import ExchangeType, Message
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from config.settings import settings
from consumer.logger import LOGGING_CONFIG, logger
from consumer.storage.db import async_session
from src.model.model import CombinedRating, GenderEnum, User
from src.storage.rabbit import channel_pool

TOLERANCE = 0.1


async def find_candidates(body):
    user_id = body.get("user_id")
    candidates_data = []
    try:
        async with async_session() as db:
            logging.config.dictConfig(LOGGING_CONFIG)
            logger.info("ПРИЁМ ЗАПРОСА В БАЗУ ДАННЫХ FIND PAIR", body)

            result = await db.execute(
                select(User)
                .options(selectinload(User.combined_rating))
                .where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return

            if not user.combined_rating:
                logger.info(f"У пользователя {user.id} нет комбинированного рейтинга!")
                return

            logger.info("ПРИНЯЛИ ЮЗЕРА ИЗ БД, ЩАС ФИЛЬТРЫ")

            filters = [
                User.age >= user.preferred_age_min,
                User.age <= user.preferred_age_max,
                User.id != user.id,
                CombinedRating.score.between(
                    user.combined_rating.score - TOLERANCE,
                    user.combined_rating.score + TOLERANCE,
                ),
            ]

            if user.preferred_gender != GenderEnum.other:
                filters.append(
                    or_(
                        User.gender == user.preferred_gender,
                        User.gender == GenderEnum.other,
                    )
                )

            if user.preferred_city != "все":
                filters.append(
                    or_(
                        User.preferred_city == user.preferred_city,
                        User.preferred_city == "все",
                    )
                )

            filters = and_(*filters)

            candidates_result = await db.execute(
                select(User)
                .join(CombinedRating, CombinedRating.user_id == User.id)
                .where(filters)
                .limit(10)
            )
            candidates = candidates_result.scalars().all()

            candidates_data = [c.to_dict() for c in candidates]

            logger.info(f"КАНДИДАТЫ СФОРМИРОВАНЫ {candidates_data}")
    except Exception as err:
        logger.error(err)
        return

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        user_queue = await channel.declare_queue(
            settings.USER_QUEUE.format(user_id=user_id), durable=True
        )

        await user_queue.bind(
            exchange,
            settings.USER_QUEUE.format(user_id=user_id),
        )

        response_body = {
            "action": "show_candidates",
            "user_id": user_id,
            "candidates": candidates_data,
        }

        logger.info("ОТПРАВКА КАНДИДАТОВ В ОЧЕРЕДЬ")

        await exchange.publish(
            Message(msgpack.packb(response_body)),
            routing_key=settings.USER_QUEUE.format(user_id=user_id),
        )
