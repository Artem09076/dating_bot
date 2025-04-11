from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❤️ Найти пару"), KeyboardButton(text="💌 Мои мэтчи")],
        [KeyboardButton(text="⚙️ Создать анкету"), KeyboardButton(text="✏️ Редактировать анкету")],
        [KeyboardButton(text="📈 Рейтинг"), KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Что хочешь сделать? 💬"
)
