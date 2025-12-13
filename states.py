from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    """States for user registration"""
    waiting_for_phone = State()


class LotCreation(StatesGroup):
    """States for creating a lot"""
    waiting_for_photos = State()
    waiting_for_description = State()
    waiting_for_city = State()
    waiting_for_size = State()
    waiting_for_wear = State()
    waiting_for_price = State()
    editing_draft = State()

    # Edit states
    edit_photos = State()
    edit_description = State()
    edit_city = State()
    edit_size = State()
    edit_wear = State()
    edit_price = State()


class Bidding(StatesGroup):
    """States for bidding process"""
    waiting_for_bid = State()
    confirming_bid = State()


class AdminAuth(StatesGroup):
    """States for admin authentication"""
    waiting_for_password = State()


class AdminModeration(StatesGroup):
    """States for admin moderation"""
    waiting_for_rejection_reason = State()
