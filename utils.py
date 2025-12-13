from datetime import datetime, timedelta
from typing import Dict, Any, List
from aiogram.types import Message, InputMediaPhoto
import config


def format_price(price: float) -> str:
    """Format price with spaces as thousand separator"""
    return f"{int(price):,}".replace(',', ' ')


async def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    from database import db
    return await db.is_admin(user_id)


async def get_user_menu(user_id: int):
    """Get appropriate menu for user (admin or regular)"""
    from keyboards import get_main_menu, get_admin_menu
    user_is_admin = await is_admin(user_id)
    return get_main_menu(is_admin=user_is_admin)


def format_lot_message(lot: Dict[str, Any], include_price: bool = True) -> str:
    """Format lot information for display"""
    text = f"<b>Описание:</b> {lot['description']}\n"
    text += f"<b>Город:</b> {lot['city']}\n"
    text += f"<b>Размер:</b> {lot['size']}\n"
    text += f"<b>Свежесть:</b> {lot['wear']}\n"

    if include_price:
        if lot.get('current_price') and lot['current_price'] > lot['start_price']:
            text += f"<b>Стартовая цена:</b> {format_price(lot['start_price'])} тенге\n"
            text += f"<b>Текущая ставка:</b> {format_price(lot['current_price'])} тенге\n"
        else:
            text += f"<b>Стартовая цена:</b> {format_price(lot['start_price'])} тенге\n"

    return text


def format_auction_status(lot: Dict[str, Any]) -> str:
    """Format auction status text"""
    if not lot.get('auction_started'):
        return "\n<b>Статус:</b> До начала аукциона"

    if lot['end_time']:
        end_time = datetime.fromisoformat(lot['end_time'])
        now = datetime.now()

        if now >= end_time:
            return "\n<b>Статус:</b> Завершено"

        remaining = end_time - now
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60

        if hours > 0:
            if minutes > 0:
                return f"\n<b>До завершения:</b> {hours} ч {minutes} мин"
            return f"\n<b>До завершения:</b> {hours} ч"
        else:
            return f"\n<b>До завершения:</b> {minutes} мин"

    return ""


def format_sold_message(lot: Dict[str, Any], final_price: float = None) -> str:
    """Format message for sold items"""
    text = "🔴 <b>ПРОДАНО</b>\n\n"
    text += f"<b>Описание:</b> {lot['description']}\n"
    text += f"<b>Город:</b> {lot['city']}\n"
    text += f"<b>Размер:</b> {lot['size']}\n"
    text += f"<b>Свежесть:</b> {lot['wear']}\n"

    # Show final price
    if final_price:
        text += f"<b>Финальная цена:</b> {format_price(final_price)} тенге\n"
    else:
        text += f"<b>Финальная цена:</b> {format_price(lot['start_price'])} тенге\n"

    # Show price increase for auctions
    if lot.get('lot_type') == 'auction' and final_price and final_price > lot['start_price']:
        increase_percent = int(((final_price - lot['start_price']) / lot['start_price']) * 100)
        text += f"<b>Рост от стартовой:</b> +{increase_percent}%\n"

    return text


def get_photos_list(photos_str: str) -> List[str]:
    """Convert photos string to list"""
    return photos_str.split(',') if photos_str else []


def photos_to_string(photos: List[str]) -> str:
    """Convert photos list to string"""
    return ','.join(photos)


def create_media_group(photos: List[str], caption: str = None) -> List[InputMediaPhoto]:
    """Create media group from photos"""
    media = []
    for i, photo_id in enumerate(photos):
        if i == 0 and caption:
            media.append(InputMediaPhoto(media=photo_id, caption=caption, parse_mode="HTML"))
        else:
            media.append(InputMediaPhoto(media=photo_id))
    return media


def get_time_intervals() -> List[int]:
    """Get time intervals for auction updates (in minutes from end)"""
    total = config.EFFECTIVE_AUCTION_DURATION_MINUTES
    # Choose dynamic checkpoints based on total duration
    if total <= 15:
        return [10, 5, 1, 0]
    elif total <= 30:
        return [20, 10, 5, 1, 0]
    elif total <= 60:
        return [45, 30, 15, 5, 0]
    else:
        return [120, 90, 60, 30, 10, 5, 0]


def calculate_end_time() -> datetime:
    """Calculate auction end time using effective minutes"""
    return datetime.now() + timedelta(minutes=config.EFFECTIVE_AUCTION_DURATION_MINUTES)


def validate_bid(amount: float, start_price: float, current_price: float = None) -> tuple[bool, str]:
    """Validate bid amount"""
    MIN_BID_STEP = 1000  # Минимальный шаг ставки

    # Определяем минимальную требуемую ставку
    if current_price:
        required_bid = current_price + MIN_BID_STEP
    else:
        required_bid = start_price

    # Проверка минимальной ставки
    if amount < required_bid:
        if current_price:
            return False, f"""❌ Ставка слишком низкая!

💰 Текущая ставка: {format_price(current_price)} тенге
📊 Минимальная ставка: {format_price(required_bid)} тенге
💵 Ваша ставка: {format_price(amount)} тенге

💡 Ставка должна быть минимум на {format_price(MIN_BID_STEP)} тенге больше текущей"""
        else:
            return False, f"""❌ Ставка слишком низкая!

📊 Стартовая цена: {format_price(start_price)} тенге
💵 Ваша ставка: {format_price(amount)} тенге

💡 Ставка должна быть не меньше стартовой цены"""

    return True, "OK"


async def safe_delete_message(message: Message):
    """Safely delete message without raising exceptions"""
    try:
        await message.delete()
    except Exception:
        pass


async def safe_edit_message(message: Message, text: str, **kwargs):
    """Safely edit message without raising exceptions"""
    try:
        await message.edit_text(text, **kwargs)
    except Exception:
        pass
