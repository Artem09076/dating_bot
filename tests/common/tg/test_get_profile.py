import uuid

import pytest
from aiogram.types import (BufferedInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, User)

from src.handlers.command.get_profile import get_profile
from src.templates.env import render
from tests.mocking.minio import MockMinioClient
from tests.mocking.tg import MockTgMessage


@pytest.mark.parametrize(
    ("predefined_queue", "correlation_id"),
    [
        (
            {
                "id": "1",
                "name": "test",
                "age": "15",
                "gender": "male",
                "city": "вап",
                "interests": "о, ф",
                "profile_filled": False,
                "photo": "photo_1124590741_AgACAgIAAxkBAAIGyWgH8I2CqzN7HEADugkgsCj1M80sAAKm_DEb5b1BSEeDGHcCwYNlAQADAgADeAADNgQ",
                "preferred_age_min": 17,
                "preferred_age_max": 90,
                "preferred_gender": "male",
                "preferred_city": "dsfc",
            },
            str(uuid.uuid4()),
        ),
    ],
)
@pytest.mark.usefixtures("_load_queue")
@pytest.mark.asyncio
async def test_get_profile(predefined_queue, correlation_id):
    user = User(
        id=1, is_bot=False, is_premium=False, last_name="asde", first_name="asdf"
    )
    message = MockTgMessage(from_user=user)
    photo_data = b"fake-photo-bytes"
    minio = MockMinioClient({"dating-app-user-1": {"profile.jpg": photo_data}})
    await get_profile(message=message)
    buttons = [
        [
            InlineKeyboardButton(text="Изменить анкету", callback_data="change_form"),
            InlineKeyboardButton(text="Удалить анкету", callback_data="delete_form"),
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    message.assert_has_calls(
        [
            (
                "answer_photo",
                (),
                {
                    "caption": render(
                        "profile.jinja2", res=predefined_queue["recipes"]
                    ),
                    "reply_markup": keyboard,
                    "photo": BufferedInputFile(photo_data, "profile.jpg"),
                },
            )
        ]
    )
