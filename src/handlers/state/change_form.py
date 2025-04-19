from aiogram.fsm.state import StatesGroup, State

class EditProfileForm(StatesGroup):
    choose_field = State()
    name = State()
    age = State()
    gender = State()
    city = State()
    interests = State()
    photo = State()
    preferred_gender = State()
    preferred_age_min = State()
    preferred_age_max = State()
    preferred_city = State()
    confirm_changes = State()
