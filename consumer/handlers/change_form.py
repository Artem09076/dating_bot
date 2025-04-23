import logging.config

import msgpack
from sqlalchemy import select, update

from consumer.logger import LOGGING_CONFIG, logger
from src.model.model import User
from src.storage.db import async_session
from src.storage.rabbit import channel_pool


async def change_form(body: dict):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info(f"Прием запроса: {body}")
    user_id = body.get("id")

    async with async_session() as db:
        try:
            user_query = await db.execute(select(User).where(User.id == user_id))
            user = user_query.scalar_one_or_none()
            existing_interests = user.interests if user.interests is not None else ""
            interests = (
                ",".join(body["interests"])
                if isinstance(body.get("interests"), list)
                else body.get("interests", existing_interests)
            )
            res = await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    name=body.get("name", user.name),
                    age=body.get("age", user.age),
                    gender=body.get("gender", user.gender),
                    city=body.get("city", user.city),
                    interests=interests,
                    preferred_gender=body.get(
                        "preferred_gender", user.preferred_gender
                    ),
                    preferred_age_min=body.get(
                        "preferred_age_min", user.preferred_age_min
                    ),
                    preferred_age_max=body.get(
                        "preferred_age_max", user.preferred_age_max
                    ),
                    preferred_city=body.get("preferred_city", user.preferred_city),
                    photo=body.get("photo", user.photo),
                )
            )
            logger.info(res)
            await db.commit()
        except Exception as err:
            await db.rollback()
            logger.exception(err)
