from aiogram.fsm.state import StatesGroup, State

class LikedProfilesFlow(StatesGroup):
    viewing = State()
