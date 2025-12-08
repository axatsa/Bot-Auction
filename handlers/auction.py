from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
import logging

from database import db
from keyboards import get_bid_confirmation_keyboard, get_main_menu, get_cancel_keyboard
from states import Bidding
from utils import format_lot_message, validate_bid, calculate_end_time
import config

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("participate:"))
async def handle_participate(callback: CallbackQuery, state: FSMContext):
    """Handle participation in auction"""
    lot_id = int(callback.data.split(":")[1])

    lot = await db.get_lot(lot_id)

    if not lot:
        await callback.answer("Лот не найден!", show_alert=True)
        return

    if lot['status'] not in ['approved', 'active']:
        await callback.answer("Аукцион недоступен!", show_alert=True)
        return

    # Check if auction needs to start
    if not lot['auction_started']:
        # Start auction timer
        end_time = calculate_end_time()
        await db.start_auction(
            lot_id=lot_id,
            start_time=datetime.now().isoformat(),
            end_time=end_time.isoformat()
        )

        # Schedule auction completion
        from scheduler import schedule_auction_completion
        await schedule_auction_completion(lot_id, end_time)

        # Update channel message
        from bot import bot
        from utils import format_auction_status, get_photos_list

        try:
            updated_text = format_lot_message(lot) + format_auction_status({
                **lot,
                'auction_started': True,
                'end_time': end_time.isoformat()
            })

            # Try to update message
            if lot.get('channel_message_id'):
                photos = get_photos_list(lot['photos'])
                if len(photos) == 1:
                    await bot.edit_message_caption(
                        chat_id=config.CHANNEL_ID,
                        message_id=lot['channel_message_id'],
                        caption=updated_text,
                        parse_mode="HTML",
                        reply_markup=callback.message.reply_markup
                    )
        except Exception as e:
            print(f"Failed to update channel message: {e}")

    # Show lot info and ask for bid
    lot = await db.get_lot(lot_id)  # Refresh lot data

    # Get bid statistics
    bids = await db.get_lot_bids(lot_id)
    bid_count = len(set([bid['user_id'] for bid in bids]))  # Unique participants

    current_price = lot.get('current_price') or lot['start_price']

    # Build message text
    text = "🎯 <b>Участие в аукционе</b>\n\n"
    text += format_lot_message(lot, include_price=False)
    text += f"\n<b>Стартовая цена:</b> {lot['start_price']} сум\n"

    if lot.get('current_price') and lot['current_price'] > lot['start_price']:
        text += f"<b>Текущая ставка:</b> {lot['current_price']} сум\n"

    text += f"<b>Количество участников:</b> {bid_count}\n"
    text += f"<b>Минимальная ставка:</b> {current_price + 1} сум\n"
    text += f"\n💬 Введите вашу ставку:"

    # Send photo with lot info
    from bot import bot
    from utils import get_photos_list

    photos = get_photos_list(lot['photos'])

    try:
        if photos:
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=photos[0],
                caption=text,
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard()
            )
        else:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard())
    except Exception as e:
        # If can't send photo, send text only
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard())

    await state.set_state(Bidding.waiting_for_bid)
    await state.update_data(lot_id=lot_id)

    logger.info(f"User {callback.from_user.id} set to Bidding.waiting_for_bid state for lot {lot_id}")

    # Verify state was set
    current_state = await state.get_state()
    logger.info(f"Current state after setting: {current_state}")

    await callback.answer()


@router.message(Bidding.waiting_for_bid)
async def process_bid(message: Message, state: FSMContext):
    """Process bid amount"""
    current_state = await state.get_state()
    logger.info(f"process_bid handler triggered! User: {message.from_user.id}, State: {current_state}, Text: {message.text}")

    # Check if message has text
    if not message.text:
        logger.warning(f"User {message.from_user.id} sent message without text")
        await message.answer("Пожалуйста, введите числовую ставку!")
        return

    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_main_menu())
        return

    # Try to parse the bid amount
    try:
        # Remove spaces and replace comma with dot
        amount_str = message.text.strip().replace(',', '.').replace(' ', '')
        amount = float(amount_str)
        logger.info(f"Parsed bid amount: {amount} from input: {message.text}")
    except ValueError:
        logger.warning(f"Invalid bid format from user {message.from_user.id}: {message.text}")
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Введите число, например: 1000 или 1000.50"
        )
        return

    data = await state.get_data()
    lot_id = data.get('lot_id')

    if not lot_id:
        logger.error(f"No lot_id in state for user {message.from_user.id}")
        await message.answer("Ошибка: лот не найден. Попробуйте снова.", reply_markup=get_main_menu())
        await state.clear()
        return

    logger.info(f"Processing bid {amount} for lot {lot_id} from user {message.from_user.id}")

    lot = await db.get_lot(lot_id)

    if not lot:
        await message.answer("Лот не найден!", reply_markup=get_main_menu())
        await state.clear()
        return

    # Validate bid
    current_price = lot.get('current_price') or lot['start_price']
    is_valid, error_msg = validate_bid(amount, lot['start_price'], current_price)

    if not is_valid:
        await message.answer(error_msg)
        return

    # Ask for confirmation
    await state.update_data(bid_amount=amount)

    text = f"<b>Подтверждение ставки</b>\n\n"
    text += f"Ваша ставка: {amount} сум\n"
    text += f"Лот: {lot['description']}\n\n"
    text += f"Подтвердить?"

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_bid_confirmation_keyboard(lot_id)
    )
    await state.set_state(Bidding.confirming_bid)


@router.callback_query(F.data.startswith("confirm_bid:"))
async def confirm_bid(callback: CallbackQuery, state: FSMContext):
    """Confirm bid"""
    lot_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    amount = data['bid_amount']

    lot = await db.get_lot(lot_id)

    # Re-validate in case someone else bid
    current_price = lot.get('current_price') or lot['start_price']
    is_valid, error_msg = validate_bid(amount, lot['start_price'], current_price)

    if not is_valid:
        await callback.message.edit_text(
            f"❌ {error_msg}",
            parse_mode="HTML"
        )
        await state.clear()
        await callback.answer()
        return

    # Save bid
    previous_leader_id = lot.get('leader_id')

    await db.add_bid(lot_id, callback.from_user.id, amount)

    await callback.message.edit_text(
        f"✅ Ваша ставка принята!\n\n"
        f"Сумма: {amount} сум\n"
        f"Вы — текущий лидер аукциона!",
        parse_mode="HTML"
    )

    # Notify previous leader
    if previous_leader_id and previous_leader_id != callback.from_user.id:
        from bot import bot
        try:
            await bot.send_message(
                chat_id=previous_leader_id,
                text=f"⚠️ Вашу ставку перебили!\n\n"
                     f"Лот: {lot['description']}\n"
                     f"Новая ставка: {amount} сум"
            )
        except Exception:
            pass

    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_bid:"))
async def cancel_bid(callback: CallbackQuery, state: FSMContext):
    """Cancel bid"""
    await callback.message.edit_text("Отменено.")
    await state.clear()
    await callback.answer()
