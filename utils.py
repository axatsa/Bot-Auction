from datetime import datetime, timedelta
from typing import Dict, Any, List
from aiogram.types import Message, InputMediaPhoto
import config


async def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    from database import db
    return await db.is_admin(user_id)


def format_lot_message(lot: Dict[str, Any], include_price: bool = True) -> str:
    """Format lot information for display"""
    text = f"<b>Описание:</b> {lot['description']}\n"
    text += f"<b>Город:</b> {lot['city']}\n"
    text += f"<b>Размер:</b> {lot['size']}\n"
    text += f"<b>Износ:</b> {lot['wear']}\n"

    if include_price:
        if lot.get('current_price') and lot['current_price'] > lot['start_price']:
            text += f"<b>Стартовая цена:</b> {lot['start_price']} сум\n"
            text += f"<b>Текущая ставка:</b> {lot['current_price']} сум\n"
        else:
            text += f"<b>Стартовая цена:</b> {lot['start_price']} сум\n"

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
    return [120, 90, 60, 30, 10, 5, 0]  # 2h, 1h30m, 1h, 30m, 10m, 5m, end


def calculate_end_time() -> datetime:
    """Calculate auction end time"""
    return datetime.now() + timedelta(hours=config.AUCTION_DURATION_HOURS)


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

💰 Текущая ставка: {int(current_price):,} сум
📊 Минимальная ставка: {int(required_bid):,} сум
💵 Ваша ставка: {int(amount):,} сум

💡 Ставка должна быть минимум на {MIN_BID_STEP:,} сум больше текущей"""
        else:
            return False, f"""❌ Ставка слишком низкая!

📊 Стартовая цена: {int(start_price):,} сум
💵 Ваша ставка: {int(amount):,} сум

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
