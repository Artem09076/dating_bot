from aiogram.fsm.state import State, StatesGroup


class PopularUser(StatesGroup):
    viewing = State()
