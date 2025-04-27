from aiogram.fsm.state import State, StatesGroup


class LikedProfilesFlow(StatesGroup):
    viewing = State()
