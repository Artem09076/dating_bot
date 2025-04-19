from sqlalchemy import select, and_
from consumer.storage.db import async_session
from src.model.model import Like, User, Conversation
import logging.config
from consumer.logger import LOGGING_CONFIG, logger
from sqlalchemy.exc import SQLAlchemyError

async def get_my_matches(body: dict):
    user_id = body["id"]

    async with async_session() as db:
        try:
            subquery = (
                select(Like.from_user_id)
                .where(
                    and_(
                        Like.to_user_id == user_id,
                        Like.is_mutual == True
                    )
                )
            ).subquery()

            query = (
                select(User.id, User.name, User.age, User.description)
                .where(
                    and_(
                        User.id.in_(subquery),
                    )
                )
            )

            result = await db.execute(query)
            matches = result.mappings().all()

            response_matches = []
            for match in matches:
                conv_query = select(Conversation).where(
                    ((Conversation.user1_id == user_id) & (Conversation.user2_id == match.id)) |
                    ((Conversation.user1_id == match.id) & (Conversation.user2_id == user_id))
                )
                conv_result = await db.execute(conv_query)
                conversation = conv_result.scalar_one_or_none()

                if not conversation:
                    conversation = Conversation(user1_id=user_id, user2_id=match.id)
                    db.add(conversation)
                    await db.commit()

                response_matches.append({
                    "id": match.id,
                    "name": match.name,
                    "age": match.age,
                    "description": match.description,
                    "conversation_id": conversation.id
                })
            return {
                "matches": response_matches
            }

        except SQLAlchemyError as e:
            return {"matches": []}
