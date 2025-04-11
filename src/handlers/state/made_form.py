from aiogram.fsm.state import State, StatesGroup

class ProfileForm(StatesGroup):
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
    profile_filled = State()
    check_state = State()
