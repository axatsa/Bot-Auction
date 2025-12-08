from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for requesting phone number"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="Отправить номер", request_contact=True)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_main_menu() -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="Добавить товар на аукцион")
    kb.button(text="Выставить букет")
    kb.button(text="Узнать мой ID")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


def get_lot_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting lot type"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Аукцион", callback_data="lot_type:auction")
    kb.button(text="Обычная продажа", callback_data="lot_type:regular")
    kb.adjust(1)
    return kb.as_markup()


def get_draft_edit_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for editing lot draft"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Медиа", callback_data=f"edit_draft:photos:{lot_id}")
    kb.button(text="Описание", callback_data=f"edit_draft:description:{lot_id}")
    kb.button(text="Город", callback_data=f"edit_draft:city:{lot_id}")
    kb.button(text="Размер", callback_data=f"edit_draft:size:{lot_id}")
    kb.button(text="Цена", callback_data=f"edit_draft:price:{lot_id}")
    kb.button(text="Износ", callback_data=f"edit_draft:wear:{lot_id}")
    kb.button(text="Удалить", callback_data=f"edit_draft:delete:{lot_id}")
    kb.button(text="Опубликовать", callback_data=f"edit_draft:publish:{lot_id}")
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup()


def get_moderation_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for lot moderation"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Одобрить", callback_data=f"moderate:approve:{lot_id}")
    kb.button(text="Отклонить", callback_data=f"moderate:reject:{lot_id}")
    kb.adjust(2)
    return kb.as_markup()


def get_participate_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for participating in auction"""
    kb = InlineKeyboardBuilder()
    kb.button(text="👉 Участвовать", callback_data=f"participate:{lot_id}")
    return kb.as_markup()


def get_bid_confirmation_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for confirming bid"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Подтвердить", callback_data=f"confirm_bid:{lot_id}")
    kb.button(text="Отменить", callback_data=f"cancel_bid:{lot_id}")
    kb.adjust(2)
    return kb.as_markup()


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard with cancel button"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="Отмена")
    return kb.as_markup(resize_keyboard=True)


def get_size_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for selecting bouquet size"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="Маленький")
    kb.button(text="Средний")
    kb.button(text="Большой")
    kb.button(text="Отмена")
    kb.adjust(3, 1)
    return kb.as_markup(resize_keyboard=True)


def get_wear_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for selecting bouquet wear"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="Сегодняшний")
    kb.button(text="1 дневный")
    kb.button(text="2 дневный")
    kb.button(text="Более 3 дней")
    kb.button(text="Отмена")
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def get_delete_confirmation_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for confirming lot deletion"""
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, удалить", callback_data=f"confirm_delete:{lot_id}")
    kb.button(text="Отмена", callback_data=f"cancel_delete:{lot_id}")
    kb.adjust(2)
    return kb.as_markup()
