from aiogram.fsm.state import State, StatesGroup


class LocationStates(StatesGroup):
    waiting_for_region = State()
    waiting_for_area = State()

