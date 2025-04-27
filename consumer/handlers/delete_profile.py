import logging.config
from typing import Any, Dict

from sqlalchemy import delete

from consumer.logger import LOGGING_CONFIG, logger
from consumer.storage.db import async_session
from src.model.model import User


async def delete_profile(body: Dict[str, Any]):
    logging.config.dictConfig(LOGGING_CONFIG)
    async with async_session() as db:
        user_id = body.get("id")
        res = await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
