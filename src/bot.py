from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config.settings import settings
dp = Dispatcher()

default = DefaultBotProperties(parse_mode=ParseMode.HTML)

bot = Bot(token=settings.BOT_TOKEN, default=default)


