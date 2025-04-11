import aio_pika
import msgpack
from aiogram import F
from aiogram.types import Message, ReplyKeyboardMarkup, CallbackQuery, KeyboardButton
from aiogram.fsm.context import FSMContext
from src.storage.rabbit import channel_pool
from aio_pika import ExchangeType
from src.handlers.callback.router import router
from src.handlers.state.made_form import ProfileForm

@router.callback_query(F.data == "⚙️ Создать анкету")
async def start_profile_creation(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if isinstance(call.message, Message):
        await call.message.answer("Как тебя зовут?")
    await state.set_state(ProfileForm.name)

@router.callback_query(F.text, ProfileForm.name)
async def process_name(message: Message, state: FSMContext) -> None:
    if message.text and not message.text.isdigit():
        await state.update_data(name=message.text)
        if isinstance(message, Message):
            await message.answer("Сколько тебе лет?")
        await state.set_state(ProfileForm.age)
    else:
        if isinstance(message, Message):
            await message.answer('Кажется вы ввели число. Напишите свое имя')



@router.message(F.text, RecipeGroup.recipe_title)
@track_latency('create_recipe_recipe_title')
async def create_recipe_recipe_title(message: Message, state: FSMContext) -> None:
    if message.text and not message.text.isdigit():
        await state.update_data(recipe_title=message.text)
        if isinstance(message, Message):
            await message.answer('Спасибо! А теперь какие ингредиенты нам нужны')
        await state.set_state(RecipeGroup.ingredients)
    else:
        if isinstance(message, Message):
            await message.answer('Кажется вы ввели число. Напишите название рецепта')


@router.message(F.text, ProfileForm.age)
async def process_age(message: Message, state: FSMContext) -> None:
    if message.text and not message.text.isdigit():
        await state.update_data(age=message.text)
        if isinstance(message, Message):
            await message.answer("Укажи свой пол (м/ж):")
        await state.set_state(ProfileForm.gender)
    else:
        if isinstance(message, Message):
            await message.answer('Кажется вы ввели число. Напишите ваш пол')


@router.message(F.text, ProfileForm.gender)
async def process_gender(message: Message, state: FSMContext) -> None:
    if message.text and not message.text.isdigit():
        await state.update_data(gender=message.text)
        if isinstance(message, Message):
            await message.answer("Из какого ты города?")
        await state.set_state(ProfileForm.city)
    else:
        if isinstance(message, Message):
            await message.answer('Кажется вы ввели число. Напишите ваш город')


@router.message(F.text, ProfileForm.city)
async def process_city(message: Message, state: FSMContext):
    if message.text and not message.text.isdigit():
        await state.update_data(city=message.text)
        if isinstance(message, Message):
            await message.answer("Расскажи о своих интересах:")
        await state.set_state(ProfileForm.interests)
    else:
        if isinstance(message, Message):
            await message.answer('Кажется вы ввели число. Напишите ваши интересы')


@router.message(F.text, ProfileForm.interests)
async def process_interests(message: Message, state: FSMContext) -> None:
    if message.text and not message.text.isdigit():
        await state.update_data(interests=message.text)
        if isinstance(message, Message):
            await message.answer("Отправь своё фото:")
        await state.set_state(ProfileForm.photo)
    else:
        if isinstance(message, Message):
            await message.answer('Кажется вы ввели текст. Отправьте ваше фото')


@router.message(F.text, ProfileForm.photo)
async def process_photo(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer("Пожалуйста, отправь именно фото 📷")
        return

    photo_id = message.photo[-1].file_id
    if message.text and not message.text.isdigit():
        await state.update_data(photo=photo_id)
        if isinstance(message, Message):
            await message.answer("Кого ты ищешь? (м/ж/все):")
        await state.set_state(ProfileForm.preferred_gender)
    else:
        if isinstance(message, Message):
            await message.answer('Кажется вы ввели число. Напишите пол парнтера, которого вы ищите')

@router.message(F.text, ProfileForm.preferred_gender)
async def process_preferred_gender(message: Message, state: FSMContext) -> None:
    if message.text and not message.text.isdigit():
        await state.update_data(preferred_gender=message.text)
        if isinstance(message, Message):
            await message.answer("Укажи минимальный возраст партнёра:")
        await state.set_state(ProfileForm.preferred_age_min)
    else:
        if isinstance(message, Message):
            await message.answer('Кажется вы ввели текст. Напишите минимальный возраст партнёра, которого вы ищите')


@router.message(F.text, ProfileForm.preferred_age_min)
async def process_preferred_age_min(message: Message, state: FSMContext) -> None:
    if message.text and not message.text.isdigit():
        await state.update_data(preferred_age_min=message.text)
        if isinstance(message, Message):
            await message.answer("А теперь максимальный возраст:")
        await state.set_state(ProfileForm.preferred_age_max)
    else:
        if isinstance(message, Message):
            await message.answer('Кажется вы ввели текст. Напишите максиммальный возраст партнёра, которого вы ищите')


@router.message(F.text, ProfileForm.preferred_age_max)
async def process_preferred_age_max(message: Message, state: FSMContext) -> None:
    if message.text and not message.text.isdigit():
        await state.update_data(preferred_age_max=message.text)
        if isinstance(message, Message):
            await message.answer("Из какого города ты хочешь найти пару? (или напиши 'все'):")
        await state.set_state(ProfileForm.preferred_city)
    else:
        if isinstance(message, Message):
            await message.answer('Кажется вы ввели число. Напишите предпочитаемый город партнера, которого вы ищите')


@router.message(F.text, ProfileForm.preferred_city)
async def process_preferred_city(message: Message, state: FSMContext) -> None:
    await state.update_data(preferred_city=message.text)

    user_data = await state.get_data()
    caption = (
        f'Пожалуйста, проверьте все ли верно: \n\n'
        f"Твоя анкета готова! 🎉\n\n"
        f"👤 Имя: {user_data.get('name')}\n"
        f"🎂 Возраст: {user_data.get('age')}\n"
        f"⚧ Пол: {user_data.get('gender')}\n"
        f"📍 Город: {user_data.get('city')}\n"
        f"🎯 Интересы: {user_data.get('interests')}\n\n"
        f"🔍 Ищет: {user_data.get('preferred_gender')} "
        f"({user_data.get('preferred_age_min')}-{user_data.get('preferred_age_max')} лет, "
        f"город: {user_data.get('preferred_city')})",
    )

    await message.answer(
        f"Твоя анкета готова! 🎉\n\n"
        f"👤 Имя: {user_data['name']}\n"
        f"🎂 Возраст: {user_data['age']}\n"
        f"⚧ Пол: {user_data['gender']}\n"
        f"📍 Город: {user_data['city']}\n"
        f"🎯 Интересы: {user_data['interests']}\n\n"
        f"🔍 Ищет: {user_data['preferred_gender']} "
        f"({user_data['preferred_age_min']}-{user_data['preferred_age_max']} лет, "
        f"город: {user_data['preferred_city']})",
    )

    menu_list = [
        [KeyboardButton(text='✅Все верно', callback_data='correct')],
        [KeyboardButton(text='❌Заполнить сначала', callback_data='incorrect')],
    ]

    keyboard = ReplyKeyboardMarkup(keyboard=menu_list)
    if isinstance(message, Message):
        await message.answer(caption, reply_markup=keyboard)
    await state.set_state(ProfileForm.profile_filled)

@router.callback_query(F.data == 'correct', ProfileForm.profile_filled)
async def create_form_correct(call: CallbackQuery, state: FSMContext) -> None:
    async with channel_pool.acquire() as channel:
        exchange = await channel.declare_exchange('user_form', ExchangeType.TOPIC, durable=True)

        user_queue = await channel.declare_queue('user_messages', durable=True)

        await user_queue.bind(exchange, 'user_messages')

        user_data = await state.get_data()
        interests = user_data.get('interests', '').split(', ')
        
        body = {
            'id': call.from_user.id,
            'name': user_data.get('name'),
            'age': user_data.get('age'),
            'gender': user_data.get('gender'),
            'city': user_data.get('city'),
            'interests': interests,
            'preferred_gender': user_data.get('preferred_gender'),
            'preferred_age_min': user_data.get('preferred_age_min'),
            'preferred_age_max': user_data.get('preferred_age_max'),
            'preferred_city': user_data.get('preferred_city'),
        }

        await exchange.publish(aio_pika.Message(msgpack.packb(body)), 'user_messages')

    if isinstance(call.message, Message):
        await call.answer('Данные сохранены')
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer('Благодарю за регистрацию. Ваши данные успешно сохранены!')
    await state.clear()

@router.callback_query(F.data == 'incorrect', ProfileForm.check_state)
async def create_form_incorrect(call: CallbackQuery, state: FSMContext) -> None:
    if isinstance(call.message, Message):
        await call.answer('Заново создаем анкету')
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer('Пожалуйста, введите ваше имя')
    await state.set_state(ProfileForm.name)