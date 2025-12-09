from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging

from database import db
from keyboards import get_main_menu, get_cancel_keyboard
from states import LotCreation

router = Router()
logger = logging.getLogger(__name__)


async def check_registration(message: Message) -> bool:
    """Check if user is registered"""
    is_registered = await db.is_user_registered(message.from_user.id)
    if not is_registered:
        await message.answer(
            "Вы не зарегистрированы! Используйте /start для регистрации."
        )
    return is_registered


@router.message(F.text == "🔥 Добавить товарный аукцион")
async def create_auction(message: Message, state: FSMContext):
    """Start auction creation"""
    if not await check_registration(message):
        return

    await message.answer(
        "📸 <b>Шаг 1/6 - Фото букета</b>\n\n"
        "Загрузите фото букета (от 1 до 10 фотографий)\n\n"
        "💡 <b>Совет:</b> Чёткие фото при хорошем освещении привлекут больше покупателей",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LotCreation.waiting_for_photos)
    await state.update_data(lot_type='auction')


@router.message(F.text == "💐 Выставить букет")
async def create_regular_sale(message: Message, state: FSMContext):
    """Start regular sale creation"""
    if not await check_registration(message):
        return

    await message.answer(
        "📸 <b>Шаг 1/6 - Фото букета</b>\n\n"
        "Загрузите фото букета (от 1 до 10 фотографий)\n\n"
        "💡 <b>Совет:</b> Чёткие фото при хорошем освещении привлекут больше покупателей",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LotCreation.waiting_for_photos)
    await state.update_data(lot_type='regular')


@router.message(F.text == "📋 Текущие аукционы")
async def show_current_auctions(message: Message):
    """Show all current auctions in bot"""
    if not await check_registration(message):
        return

    from database import db
    from utils import format_lot_message, get_photos_list, format_auction_status
    from keyboards import get_participate_keyboard, get_buy_keyboard
    from bot import bot

    # Get all active and approved lots
    lots = await db.get_all_active_lots()

    if not lots:
        await message.answer(
            "📭 <b>Нет активных аукционов</b>\n\n"
            "На данный момент нет активных аукционов или товаров.\n"
            "Следите за обновлениями в канале!",
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"📋 <b>Текущие аукционы и товары: {len(lots)}</b>\n\n"
        f"Отправляю их вам...",
        parse_mode="HTML"
    )

    for lot in lots:
        photos = get_photos_list(lot['photos'])

        # Build caption
        if lot['lot_type'] == 'auction':
            caption = "🔥 <b>Аукцион</b>\n\n"
        else:
            caption = "💐 <b>Букет на продажу</b>\n\n"

        caption += format_lot_message(lot)

        if lot['lot_type'] == 'auction' and lot.get('auction_started'):
            caption += format_auction_status(lot)

        # Choose keyboard based on lot type
        if lot['lot_type'] == 'auction':
            keyboard = get_participate_keyboard(lot['id'])
        else:
            keyboard = get_buy_keyboard(lot['id'])

        # Send lot
        try:
            if len(photos) == 1:
                await bot.send_photo(
                    chat_id=message.from_user.id,
                    photo=photos[0],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                from utils import create_media_group
                media = create_media_group(photos, caption)
                await bot.send_media_group(
                    chat_id=message.from_user.id,
                    media=media
                )
                await bot.send_message(
                    chat_id=message.from_user.id,
                    text="👇 Нажмите чтобы участвовать" if lot['lot_type'] == 'auction' else "👇 Нажмите чтобы купить",
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Failed to send lot {lot['id']}: {e}")


# Debug handler - catches unhandled text messages
@router.message(F.text)
async def debug_unhandled_text(message: Message, state: FSMContext):
    """Debug: catch any unhandled text message"""
    current_state = await state.get_state()
    logger.warning(f"⚠️ MENU.PY caught unhandled text: '{message.text}' from user {message.from_user.id}, state: {current_state}")
