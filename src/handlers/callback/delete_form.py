import aio_pika
import msgpack
from aio_pika import ExchangeType
from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config.settings import settings
from src.handlers.callback.router import router
from src.handlers.command.get_profile import get_profile
from src.logger import LOGGING_CONFIG, logger
from src.metrics import SEND_MESSAGE
from src.storage.rabbit import channel_pool


@router.callback_query(F.data == "delete_form")
async def start_delete_form(call: CallbackQuery):
    buttons = [
        [
            InlineKeyboardButton(text="Удалить", callback_data="final_delete"),
            InlineKeyboardButton(
                text="Вернуться к анкете", callback_data="return_form"
            ),
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.answer(
        text="Вы уверены, что хотите удалить анкету, действие назад отменить нельзя будет",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "final_delete")
async def delete_form(call: CallbackQuery):
    user_id = call.from_user.id
    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        user_queue = await channel.declare_queue("user_messages", durable=True)
        queue = await channel.declare_queue(
            settings.USER_QUEUE.format(user_id=user_id), durable=True
        )

        await user_queue.bind(exchange, "user_messages")
        await queue.bind(exchange, settings.USER_QUEUE.format(user_id=user_id))
        body = {"id": user_id, "action": "delete_profile"}
        await exchange.publish(aio_pika.Message(msgpack.packb(body)), "user_messages")
        SEND_MESSAGE.inc()
        await call.message.delete()
        await call.message.answer("Анкета успешно удалена")


@router.callback_query(F.data == "return_form")
async def return_get_profile(call: CallbackQuery):
    await call.message.delete()
