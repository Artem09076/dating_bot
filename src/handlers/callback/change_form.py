import re

import aio_pika
import msgpack
from aio_pika import ExchangeType
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from config.settings import settings
from src.handlers.callback.router import router
from src.handlers.command.gender import gender_keyboard
from src.handlers.state.change_form import EditProfileForm
from src.storage.minio import minio_client
from src.storage.rabbit import channel_pool

edit_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Имя", callback_data="edit_name")],
        [InlineKeyboardButton(text="🎂 Возраст", callback_data="edit_age")],
        [InlineKeyboardButton(text="♂️♀️ Пол", callback_data="edit_gender")],
        [InlineKeyboardButton(text="📍 Город", callback_data="edit_city")],
        [InlineKeyboardButton(text="🎯 Интересы", callback_data="edit_interests")],
        [InlineKeyboardButton(text="🖼️ Фото", callback_data="edit_photo")],
        [
            InlineKeyboardButton(
                text="🔍 Пожелания к партнёру", callback_data="edit_preferences"
            )
        ],
        [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_editing")],
    ]
)


@router.callback_query(F.data == "change_form")
async def start_editing(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "Что вы хотите изменить?", reply_markup=edit_menu_keyboard
    )
    await state.set_state(EditProfileForm.choose_field)


@router.callback_query(EditProfileForm.choose_field)
async def choose_field_to_edit(call: CallbackQuery, state: FSMContext):
    data = call.data

    if data == "edit_name":
        await call.message.answer("Введите новое имя:")
        await state.set_state(EditProfileForm.name)
    elif data == "edit_age":
        await call.message.answer("Введите новый возраст:")
        await state.set_state(EditProfileForm.age)
    elif data == "edit_gender":
        gender_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Мужской", callback_data="gender_male")],
                [InlineKeyboardButton(text="Женский", callback_data="gender_female")],
                [InlineKeyboardButton(text="Другое", callback_data="gender_other")],
            ]
        )
        await call.message.answer("Выберите новый пол:", reply_markup=gender_keyboard)
        await state.set_state(EditProfileForm.gender)
    elif data == "edit_city":
        await call.message.answer("Введите новый город:")
        await state.set_state(EditProfileForm.city)
    elif data == "edit_interests":
        await call.message.answer("Введите новые интересы через запятую:")
        await state.set_state(EditProfileForm.interests)
    elif data == "edit_photo":
        await call.message.answer("Отправьте новое фото:")
        await state.set_state(EditProfileForm.photo)
    elif data == "edit_preferences":
        await call.message.answer("Кто вам интересен? (Мужской / Женский / Все равно)")
        await state.set_state(EditProfileForm.preferred_gender)
    elif data == "finish_editing":
        await save_updated_profile(call, state)


@router.message(EditProfileForm.name)
async def edit_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await back_to_edit_menu(message, state)


@router.message(EditProfileForm.age)
async def edit_age(message: Message, state: FSMContext):
    if message.text.isdigit():
        await state.update_data(age=int(message.text))
        await back_to_edit_menu(message, state)
    else:
        await message.answer("Возраст должен быть числом!")


@router.callback_query(EditProfileForm.gender)
async def handle_gender_selection(callback: CallbackQuery, state: FSMContext):
    gender_map = {
        "gender_male": "Мужской",
        "gender_female": "Женский",
        "gender_other": "Другое",
    }
    gender = gender_map.get(callback.data)

    if gender:
        await state.update_data(gender=gender)
        await callback.message.answer("✅ Пол обновлён!")
        await state.set_state(EditProfileForm.confirm_changes)
    else:
        await callback.answer("Некорректный выбор", show_alert=True)


@router.message(EditProfileForm.city)
async def edit_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await back_to_edit_menu(message, state)


@router.message(EditProfileForm.interests)
async def edit_interests(message: Message, state: FSMContext):
    interests = [i.strip() for i in message.text.split(",") if i.strip()]
    await state.update_data(interests=interests)
    await back_to_edit_menu(message, state)


@router.message(EditProfileForm.photo)
async def edit_photo(message: Message, state: FSMContext):
    if message.photo:
        file_id = message.photo[-1].file_id
        user_id = message.from_user.id
        file_name = f"photo_{user_id}_{file_id}"

        file = await message.bot.get_file(file_id)
        file_bytes = await message.bot.download_file(file.file_path)

        bucket_name = settings.MINIO_BUCKET.format(user_id=user_id)
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)

        minio_client.put_object(
            bucket_name=bucket_name,
            object_name=file_name,
            data=file_bytes,
            length=file.file_size,
            content_type="image/jpeg",
        )

        await state.update_data(photo=file_name)
        await back_to_edit_menu(message, state)
    else:
        await message.answer("Пожалуйста, отправьте именно фото!")


@router.message(EditProfileForm.preferred_gender)
async def edit_preferred_gender(message: Message, state: FSMContext):
    gender_map = {"Мужской": "Мужской", "Женский": "Женский", "Все равно": "Другое"}
    if message.text in gender_map:
        await state.update_data(preferred_gender=gender_map[message.text])
        await message.answer("Укажите минимальный возраст партнера:")
        await state.set_state(EditProfileForm.preferred_age_min)
    else:
        await message.answer(
            "Некорректный выбор. Пожалуйста, выберите из предложенных вариантов."
        )


@router.message(EditProfileForm.preferred_age_min)
async def edit_preferred_age_min(message: Message, state: FSMContext):
    if message.text.isdigit():
        await state.update_data(preferred_age_min=int(message.text))
        await message.answer("Укажите максимальный возраст партнера:")
        await state.set_state(EditProfileForm.preferred_age_max)
    else:
        await message.answer("Минимальный возраст должен быть числом!")


@router.message(EditProfileForm.preferred_age_max)
async def edit_preferred_age_max(message: Message, state: FSMContext):
    if message.text.isdigit():
        await state.update_data(preferred_age_max=int(message.text))
        await message.answer("Из какого города вы хотите найти партнера?")
        await state.set_state(EditProfileForm.preferred_city)
    else:
        await message.answer("Максимальный возраст должен быть числом!")


@router.message(EditProfileForm.preferred_city)
async def edit_preferred_city(message: Message, state: FSMContext):
    await state.update_data(preferred_city=message.text)
    await back_to_edit_menu(message, state)


async def back_to_edit_menu(message: Message, state: FSMContext):
    await message.answer(
        "Выберите, что хотите изменить еще:", reply_markup=edit_menu_keyboard
    )
    await state.set_state(EditProfileForm.choose_field)


async def save_updated_profile(call: CallbackQuery, state: FSMContext):
    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange(
            "user_form", ExchangeType.TOPIC, durable=True
        )

        user_queue = await channel.declare_queue("user_messages", durable=True)

        await user_queue.bind(exchange, "user_messages")
        user_data = await state.get_data()
        body = {
            **user_data,
            "id": call.from_user.id,
            "action": "update_form",
        }
        await exchange.publish(
            aio_pika.Message(msgpack.packb(body)), routing_key="user_messages"
        )

        await call.answer("Данные сохранены")
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer("Анкета обновлена! ✅")
    await state.clear()
