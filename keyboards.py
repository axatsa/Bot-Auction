from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for requesting phone number"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="Отправить номер", request_contact=True)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔥 Добавить товарный аукцион")
    kb.button(text="💐 Выставить букет")
    kb.button(text="📋 Текущие аукционы")
    if is_admin:
        kb.button(text="⚙️ Режим администратора")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


def get_admin_menu() -> ReplyKeyboardMarkup:
    """Admin menu keyboard"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔔 Модерация")
    kb.button(text="📜 История")
    kb.button(text="👤 Режим пользователя")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


def get_draft_edit_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for editing lot draft"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📸 Фото", callback_data=f"edit_draft:photos:{lot_id}")
    kb.button(text="📝 Описание", callback_data=f"edit_draft:description:{lot_id}")
    kb.button(text="🏙️ Город", callback_data=f"edit_draft:city:{lot_id}")
    kb.button(text="📏 Размер", callback_data=f"edit_draft:size:{lot_id}")
    kb.button(text="🌸 Износ", callback_data=f"edit_draft:wear:{lot_id}")
    kb.button(text="💰 Цена", callback_data=f"edit_draft:price:{lot_id}")
    kb.button(text="🗑️ Удалить", callback_data=f"edit_draft:delete:{lot_id}")
    kb.button(text="✅ Опубликовать", callback_data=f"edit_draft:publish:{lot_id}")
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup()


def get_moderation_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for lot moderation"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Одобрить", callback_data=f"moderate:approve:{lot_id}")
    kb.button(text="❌ Отклонить", callback_data=f"moderate:reject:{lot_id}")
    kb.adjust(2)
    return kb.as_markup()


def get_rejection_reasons_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for selecting rejection reason"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📸 Плохое качество фото", callback_data=f"reject_reason:{lot_id}:bad_photos")
    kb.button(text="📝 Неполное описание", callback_data=f"reject_reason:{lot_id}:incomplete_desc")
    kb.button(text="🚫 Нарушение правил", callback_data=f"reject_reason:{lot_id}:rules_violation")
    kb.button(text="❌ Неподходящий товар", callback_data=f"reject_reason:{lot_id}:inappropriate")
    kb.button(text="✏️ Своя причина", callback_data=f"reject_reason:{lot_id}:custom")
    kb.button(text="◀️ Назад", callback_data=f"reject_reason:{lot_id}:back")
    kb.adjust(1, 1, 1, 1, 1, 1)
    return kb.as_markup()


def get_confirm_rejection_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for confirming rejection"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить отклонение", callback_data=f"confirm_reject:{lot_id}")
    kb.button(text="◀️ Назад", callback_data=f"cancel_reject:{lot_id}")
    kb.adjust(1)
    return kb.as_markup()


def get_participate_keyboard(lot_id: int, bot_username: str = None) -> InlineKeyboardMarkup:
    """Keyboard for participating in auction"""
    kb = InlineKeyboardBuilder()

    # If bot_username provided, use deep link, otherwise use callback
    if bot_username:
        kb.button(text="🎯 Участвовать", url=f"https://t.me/{bot_username}?start=lot_{lot_id}")
    else:
        kb.button(text="🎯 Участвовать", callback_data=f"participate:{lot_id}")

    return kb.as_markup()


def get_buy_keyboard(lot_id: int, bot_username: str = None) -> InlineKeyboardMarkup:
    """Keyboard for buying item at fixed price"""
    kb = InlineKeyboardBuilder()

    # If bot_username provided, use deep link, otherwise use callback
    if bot_username:
        kb.button(text="💳 Купить", url=f"https://t.me/{bot_username}?start=buy_{lot_id}")
    else:
        kb.button(text="💳 Купить", callback_data=f"buy:{lot_id}")

    return kb.as_markup()


def get_bid_confirmation_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for confirming bid"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"confirm_bid:{lot_id}")
    kb.button(text="❌ Отменить", callback_data=f"cancel_bid:{lot_id}")
    kb.adjust(2)
    return kb.as_markup()


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard with cancel button"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="❌ Отмена")
    return kb.as_markup(resize_keyboard=True)


def get_city_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for selecting city"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="Алматы")
    kb.button(text="Астана")
    kb.button(text="Шымкент")
    kb.button(text="Караганда")
    kb.button(text="Актобе")
    kb.button(text="Тараз")
    kb.button(text="Павлодар")
    kb.button(text="Усть-Каменогорск")
    kb.button(text="Семей")
    kb.button(text="Атырау")
    kb.button(text="Костанай")
    kb.button(text="Кызылорда")
    kb.button(text="✏️ Другой город")
    kb.button(text="❌ Отмена")
    kb.adjust(2, 2, 2, 2, 2, 2, 1, 1)
    return kb.as_markup(resize_keyboard=True)


def get_size_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for selecting bouquet size"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="Маленький")
    kb.button(text="Средний")
    kb.button(text="Большой")
    kb.button(text="❌ Отмена")
    kb.adjust(3, 1)
    return kb.as_markup(resize_keyboard=True)


def get_wear_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for selecting bouquet wear"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="Сегодняшний")
    kb.button(text="1 дневный")
    kb.button(text="2 дневный")
    kb.button(text="Более 3 дней")
    kb.button(text="❌ Отмена")
    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def get_delete_confirmation_keyboard(lot_id: int) -> InlineKeyboardMarkup:
    """Keyboard for confirming lot deletion"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑️ Да, удалить", callback_data=f"confirm_delete:{lot_id}")
    kb.button(text="◀️ Отмена", callback_data=f"cancel_delete:{lot_id}")
    kb.adjust(2)
    return kb.as_markup()
