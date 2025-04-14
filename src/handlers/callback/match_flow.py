import asyncio
import aio_pika
import msgpack
from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aio_pika import ExchangeType
from src.storage.rabbit import channel_pool
from config.settings import settings
from src.handlers.callback.router import router
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto
from src.bot import bot
from src.handlers.command.menu import menu


@router.callback_query(F.data == "find_pair")
async def find_pair_handler(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🔍 Ищу подходящие анкеты...")

    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange("user_receipts", ExchangeType.TOPIC, durable=True)

        body = {
            "user_id": call.from_user.id,
            "action": "find_candidates"
        }

        await exchange.publish(
            aio_pika.Message(msgpack.packb(body)),
            routing_key="user_messages"
        )

        user_queue = await channel.declare_queue(
            settings.USER_QUEUE.format(user_id=call.from_user.id),
            durable=True
        )

        retries = 3
        for _ in range(retries):
            try:
                res = await user_queue.get(timeout=3)
                await res.ack()
                data = msgpack.unpackb(res.body)
                candidates = data.get("candidates", [])
                if not candidates:
                    await call.message.answer("😕 Подходящих анкет не найдено.")
                    return

                await state.set_data({"candidates": candidates, "current_index": 0})
                await show_next_candidate(call, state)
                return

            except asyncio.QueueEmpty:
                await asyncio.sleep(1)

        await call.message.answer("⚠️ Не удалось получить анкеты. Попробуйте позже.")


async def show_next_candidate(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data.get("current_index", 0)
    candidates = data.get("candidates", [])

    if index >= len(candidates):
        await call.message.answer("✅ Больше анкет нет.")
        await menu(call.message)
        await state.clear()
        return

    candidate = candidates[index]
    caption = (
        f"{candidate['name']}, {candidate['age']}, {candidate['city']}\n"
        f"Интересы: {candidate['interests']}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Лайк", callback_data="like")],
        [InlineKeyboardButton(text="👎 Дизлайк", callback_data="dislike")],
        [InlineKeyboardButton(text="❌ Закончить", callback_data="stop_search")]
    ])

    await call.message.answer_photo(candidate["photo"], caption=caption, reply_markup=keyboard)


@router.callback_query(F.data.in_(["like", "dislike"]))
async def handle_reaction(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data.get("current_index", 0)
    candidates = data.get("candidates", [])

    if index >= len(candidates):
        await callback.message.answer("📭 Анкеты закончились.")
        return

    if callback.data == "like":
        liked_user_id = candidates[index]["id"]
        await notify_liked_user(liked_user_id, callback.from_user.id)

    await state.update_data(current_index=index + 1)
    await show_next_candidate(callback, state)


@router.callback_query(F.data == "stop_search")
async def stop_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📋 Главное меню")
    await menu(callback.message)
    await state.clear()


async def notify_liked_user(target_user_id, who_liked_id):
    # логика отправки уведомления тому, кого лайкнули
    text = f"❤️ Вам поставили лайк!"
    await bot.send_message(target_user_id, text)
