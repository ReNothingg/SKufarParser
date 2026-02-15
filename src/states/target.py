from aiogram.fsm.state import State, StatesGroup


class TargetStates(StatesGroup):
    waiting_for_source = State()
    waiting_for_name = State()

