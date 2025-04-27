import logging.config

import msgpack
from sqlalchemy import select, update

from consumer.logger import LOGGING_CONFIG, logger
from src.model.model import User, GenderEnum
from src.storage.db import async_session
from src.storage.rabbit import channel_pool


async def change_form(body: dict):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info(f"ПРИЕМ ЗАПРОСА НА ИЗМЕНЕНИЕ АНКЕТЫ: {body}")
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

            gender_value = body.get("gender")
            if isinstance(gender_value, str):
                try:
                    gender_value = GenderEnum(gender_value)
                except ValueError:
                    logger.warning(
                        f"Некорректное значение пола: {gender_value}. Оставляем старое.")
                    gender_value = user.gender
            else:
                gender_value = user.gender

            preferred_gender_value = body.get("preferred_gender")
            if isinstance(preferred_gender_value, str):
                try:
                    preferred_gender_value = GenderEnum(preferred_gender_value)
                except ValueError:
                    logger.warning(
                        f"Некорректное значение предпочтительного пола: {preferred_gender_value}. Оставляем старое."
                    )
                    preferred_gender_value = user.preferred_gender
            else:
                preferred_gender_value = user.preferred_gender

            
            await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    name=body.get("name", user.name),
                    age=body.get("age", user.age),
                    gender=gender_value,
                    city=body.get("city", user.city),
                    interests=interests,
                    preferred_gender=preferred_gender_value,
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
            logger.info(f"ИЗМЕНЕНИЕ АНКЕТЫ В БАЗЕ {body}")
            await db.commit()
        except Exception as err:
            await db.rollback()
            logger.exception(err)
