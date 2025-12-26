from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
import logging

from database import db
from keyboards import get_bid_confirmation_keyboard, get_main_menu, get_cancel_keyboard, get_outbid_keyboard, get_mark_sold_keyboard
from states import Bidding
from utils import format_lot_message, validate_bid, calculate_end_time, format_price
import config

router = Router()
logger = logging.getLogger(__name__)

# Dictionary to track users waiting to enter bids: {user_id: lot_id}
awaiting_bids = {}


@router.callback_query(F.data.startswith("contact_seller:"))
async def handle_contact_seller(callback: CallbackQuery, state: FSMContext):
    """Handle contact seller request for fixed price items"""
    lot_id = int(callback.data.split(":")[1])

    lot = await db.get_lot(lot_id)

    if not lot:
        await callback.answer("Лот не найден!", show_alert=True)
        return

    if lot['status'] not in ['approved', 'active']:
        await callback.answer("Товар уже продан!", show_alert=True)
        return

    if lot.get('lot_type') != 'regular':
        await callback.answer("Это не букет на продажу!", show_alert=True)
        return

    from bot import bot

    # Get seller and buyer info
    seller = await db.get_user(lot['owner_id'])
    buyer = await db.get_user(callback.from_user.id)

    if not seller or not buyer:
        await callback.answer("Ошибка получения данных пользователя!", show_alert=True)
        return

    seller_username = f"@{seller['username']}" if seller.get('username') else "нет username"
    buyer_username = f"@{buyer['username']}" if buyer.get('username') else "нет username"

    # Notify buyer with seller contact
    try:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=f"✅ <b>Отлично, мы передали Ваш контакт владельцу букета.</b>\n\n"
                 f"📦 <b>Товар:</b> {lot['description']}\n"
                 f"💰 <b>Цена:</b> {format_price(lot['start_price'])} тенге\n"
                 f"🏙️ <b>Город:</b> {lot['city']}\n\n"
                 f"🙏 Оставайтесь на связи, если владелец не свяжется с Вами в течении часа, то скорей всего букет уже продан",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to notify buyer: {e}")

    # Notify seller with buyer contact and "Sold" button
    try:
        await bot.send_message(
            chat_id=lot['owner_id'],
            text=f"🔔 <b>Кто-то заинтересовался вашим букетом!</b>\n\n"
                 f"📦 <b>Товар:</b> {lot['description']}\n"
                 f"💰 <b>Цена:</b> {format_price(lot['start_price'])} тенге\n\n"
                 f"👤 <b>Контакт покупателя:</b>\n"
                 f"Имя: {buyer['name']}\n"
                 f"Username: {buyer_username}\n"
                 f"Телефон: {buyer['phone']}\n\n"
                 f"💬 Свяжитесь с покупателем для уточнения деталей\n\n"
                 f"После успешной продажи нажмите кнопку ниже:",
            parse_mode="HTML",
            reply_markup=get_mark_sold_keyboard(lot_id)
        )
    except Exception as e:
        logger.error(f"Failed to notify seller: {e}")

    await callback.answer("✅ Ваш контакт отправлен продавцу! Проверьте сообщения от бота.")


@router.callback_query(F.data.startswith("participate:"))
async def handle_participate(callback: CallbackQuery, state: FSMContext):
    """Handle participation in auction"""
    lot_id = int(callback.data.split(":")[1])

    lot = await db.get_lot(lot_id)

    if not lot:
        await callback.answer("Лот не найден!", show_alert=True)
        return

    if lot['status'] not in ['approved', 'active']:
        await callback.answer("Товар продан!", show_alert=True)
        return

    if lot.get('lot_type') != 'auction':
        await callback.answer("Это не аукцион! Используйте кнопку 'Купить'", show_alert=True)
        return

    # Check if user is the owner of the lot
    if lot['owner_id'] == callback.from_user.id:
        await callback.answer("❌ Вы не можете участвовать в аукционе на свой букет!", show_alert=True)
        return

    # Check if user is already bidding on another lot
    if callback.from_user.id in awaiting_bids:
        previous_lot_id = awaiting_bids[callback.from_user.id]
        if previous_lot_id != lot_id:
            logger.info(f"⚠️ User {callback.from_user.id} switching from lot {previous_lot_id} to lot {lot_id}")
            # Will be overwritten below

    # Get bid statistics
    bids = await db.get_lot_bids(lot_id)
    bid_count = len(set([bid['user_id'] for bid in bids]))  # Unique participants

    current_price = lot.get('current_price') or lot['start_price']
    MIN_BID_STEP = 500

    # Calculate minimum bid
    if lot.get('current_price') and lot['current_price'] > lot['start_price']:
        min_bid = lot['current_price'] + MIN_BID_STEP
    else:
        min_bid = lot['start_price']

    # Build message text
    text = "🎯 <b>Участие в аукционе</b>\n\n"
    text += format_lot_message(lot, include_price=False)
    text += f"\n💰 <b>Стартовая цена:</b> {format_price(lot['start_price'])} сум\n"

    if lot.get('current_price') and lot['current_price'] > lot['start_price']:
        text += f"🔥 <b>Текущая ставка:</b> {format_price(lot['current_price'])} сум\n"

    text += f"👥 <b>Количество участников:</b> {bid_count}\n"
    text += f"📊 <b>Минимальная ставка:</b> {format_price(min_bid)} сум\n"
    text += f"\n📋 <b>Участвуя в аукционе, вы </b><a href='https://telegra.ph/Re-Bloom---Term-of-Use-12-06'>соглашаетесь с правилами</a>\n"
    text += f"\n💬 <b>Напишите сумму вашей ставки:</b>"

    # Send photo(s) with lot info to user (private)
    from bot import bot
    from utils import get_photos_list, create_media_group

    photos = get_photos_list(lot['photos'])

    try:
        if len(photos) == 0:
            # No photos
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=text,
                parse_mode="HTML"
            )
        elif len(photos) == 1:
            # Single photo - send photo with caption
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=photos[0],
                caption=text,
                parse_mode="HTML"
            )
        else:
            # Multiple photos - send as media group
            media = create_media_group(photos, text)
            await bot.send_media_group(
                chat_id=callback.from_user.id,
                media=media
            )
    except Exception as e:
        # If can't send photo, attempt to reply in channel or fallback
        logger.error(f"Failed to send photos or DM: {e}")
        await callback.answer("❌ Не могу отправить сообщение в личку. Убедитесь, что вы запустили бота командой /start", show_alert=True)
        return

    # Mark user as waiting for bid input
    awaiting_bids[callback.from_user.id] = lot_id

    logger.info(f"📍 Sent bid request to user {callback.from_user.id} for lot {lot_id}")
    await callback.answer()


# Handle text messages that might be bids
# This handler must be registered BEFORE menu.py handlers!
@router.message(F.text)
async def process_bid(message: Message, state: FSMContext):
    """Process bid amount from user if they're waiting to enter a bid"""
    # Check if user is waiting to enter a bid FIRST
    if message.from_user.id not in awaiting_bids:
        # Not waiting for bid - let other handlers process this
        logger.debug(f"🔄 process_bid: User {message.from_user.id} not in awaiting_bids, skipping text: '{message.text}'")
        return

    # Ignore commands (start with /)
    if message.text.startswith('/'):
        logger.info(f"🔄 process_bid: Ignoring command '{message.text}' from user {message.from_user.id}")
        return

    # Ignore menu buttons (contain emoji or specific keywords)
    menu_keywords = ['Добавить', 'Выставить', 'Текущие', 'Режим', 'Модерация', 'История']
    if any(keyword in message.text for keyword in menu_keywords):
        return

    lot_id = awaiting_bids[message.from_user.id]

    logger.info(f"🎯 process_bid HANDLER CALLED. User: {message.from_user.id}, Lot: {lot_id}, Text: '{message.text}'")

    # Handle cancel
    if message.text.strip().lower() in ["отмена", "cancel", "❌ отмена"]:
        del awaiting_bids[message.from_user.id]
        from utils import get_user_menu
        menu = await get_user_menu(message.from_user.id)
        await message.answer("❌ Отменено.", reply_markup=menu)
        return

    # Try to parse the bid amount
    try:
        # Remove spaces and replace comma with dot
        amount_str = message.text.strip().replace(',', '.').replace(' ', '')
        amount = float(amount_str)
        logger.info(f"✅ Parsed bid amount: {amount} from input: {message.text}")
    except ValueError:
        await message.answer(
            "❌ Неверный формат!\n\n"
            "Введите число, например: 1000 или 1000.50"
        )
        return

    lot = await db.get_lot(lot_id)
    if not lot:
        # Remove from awaiting_bids
        del awaiting_bids[message.from_user.id]
        from utils import get_user_menu
        menu = await get_user_menu(message.from_user.id)
        await message.answer("Лот не найден! Возможно, аукцион завершён.", reply_markup=menu)
        return

    # Validate bid against current price
    current_price = lot.get('current_price') or lot['start_price']
    is_valid, error_msg = validate_bid(amount, lot['start_price'], current_price)
    if not is_valid:
        await message.answer(error_msg)
        return

    # Ask for confirmation with three buttons
    amount_int = int(amount)

    # Send confirmation message (amount is in callback data, no need to store in FSM)
    await message.answer(
        f"<b>Подтверждение ставки</b>\n\n"
        f"💰 Ваша ставка: {format_price(amount_int)} сум\n"
        f"📦 Лот: {lot['description']}\n\n"
        f"<b>Подтвердить ставку?</b>",
        parse_mode="HTML",
        reply_markup=get_bid_confirmation_keyboard(lot_id, amount_int)
    )


@router.callback_query(F.data.startswith("confirm_bid:"))
async def confirm_bid(callback: CallbackQuery, state: FSMContext):
    """Confirm bid — data contains lot_id and amount: confirm_bid:<lot_id>:<amount>"""
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer()
        return

    lot_id = int(parts[1])
    try:
        amount = float(parts[2])
    except Exception:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    lot = await db.get_lot(lot_id)
    if not lot:
        await callback.message.edit_text("Лот не найден или завершён.")
        await callback.answer()
        return

    # Re-validate in case someone else bid
    current_price = lot.get('current_price') or lot['start_price']
    is_valid, error_msg = validate_bid(amount, lot['start_price'], current_price)
    if not is_valid:
        await callback.message.edit_text(f"❌ {error_msg}", parse_mode="HTML")
        await callback.answer()
        return

    # Check if this is the first bid (auction not started yet)
    auction_just_started = not lot.get('auction_started')

    # Save bid
    previous_leader_id = lot.get('leader_id')

    await db.add_bid(lot_id, callback.from_user.id, amount)

    # If this is the first bid, start the auction timer
    if auction_just_started:
        end_time = calculate_end_time()
        await db.start_auction(
            lot_id=lot_id,
            start_time=datetime.now().isoformat(),
            end_time=end_time.isoformat()
        )

        # Schedule auction completion and updates
        from scheduler import schedule_auction_completion
        await schedule_auction_completion(lot_id, end_time)

        logger.info(f"🚀 Auction {lot_id} started! Ends at {end_time}")

    # Refresh lot data after bid
    lot = await db.get_lot(lot_id)

    # Prepare confirmation message
    confirmation_msg = f"✅ <b>Ваша ставка принята!</b>\n\n"
    confirmation_msg += f"💰 Сумма: {format_price(amount)} сум\n"
    confirmation_msg += f"🥇 Вы — текущий лидер аукциона!"

    if auction_just_started:
        confirmation_msg += f"\n\n⏰ <b>Торги начались!</b>\nДо завершения: 2 часа"

    await callback.message.edit_text(confirmation_msg, parse_mode="HTML")

    # Remove user from awaiting_bids (bid completed)
    if callback.from_user.id in awaiting_bids:
        del awaiting_bids[callback.from_user.id]

    # Restore main menu after bid confirmation
    from bot import bot
    from utils import get_user_menu
    menu = await get_user_menu(callback.from_user.id)
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="Используйте меню ниже для навигации:",
        reply_markup=menu
    )

    # Update channel message with new bid info
    if lot.get('channel_message_id'):
        from bot import bot
        from bot import bot_username
        from utils import format_lot_message, format_auction_status, get_photos_list
        from keyboards import get_participate_keyboard

        try:
            photos = get_photos_list(lot['photos'])

            if len(photos) == 1:
                # Single photo - edit caption
                updated_text = format_lot_message(lot) + format_auction_status(lot)
                await bot.edit_message_caption(
                    chat_id=config.CHANNEL_ID,
                    message_id=lot['channel_message_id'],
                    caption=updated_text,
                    parse_mode="HTML",
                    reply_markup=get_participate_keyboard(lot_id, bot_username)
                )

                if auction_just_started:
                    logger.info(f"📢 Channel message updated - auction {lot_id} timer is now visible!")
                else:
                    logger.info(f"📢 Channel message updated - new bid {amount} for auction {lot_id}")
            else:
                # Media group - edit button message with status
                if lot.get('channel_button_message_id'):
                    button_text = "👇 Нажмите чтобы участвовать в аукционе\n\n"
                    button_text += format_auction_status(lot)

                    await bot.edit_message_text(
                        chat_id=config.CHANNEL_ID,
                        message_id=lot['channel_button_message_id'],
                        text=button_text,
                        parse_mode="HTML",
                        reply_markup=get_participate_keyboard(lot_id, bot_username)
                    )

                    if auction_just_started:
                        logger.info(f"📢 Button message updated - auction {lot_id} timer is now visible!")
                    else:
                        logger.info(f"📢 Button message updated - new bid {amount} for auction {lot_id}")
        except Exception as e:
            logger.error(f"Failed to update channel message after bid: {e}")

    # Notify previous leader
    if previous_leader_id and previous_leader_id != callback.from_user.id:
        from bot import bot
        try:
            await bot.send_message(
                chat_id=previous_leader_id,
                text=f"⚠️ <b>Вашу ставку перебили!</b>\n\n"
                     f"📦 Лот: {lot['description']}\n"
                     f"💰 Новая ставка: {format_price(amount)} сум",
                parse_mode="HTML",
                reply_markup=get_outbid_keyboard(lot_id)
            )
        except Exception:
            pass

    await callback.answer()


@router.callback_query(F.data.startswith("change_bid:"))
async def change_bid(callback: CallbackQuery, state: FSMContext):
    """Handle change bid button - user wants to enter a different amount"""
    lot_id = int(callback.data.split(":")[1])

    # Edit confirmation message
    await callback.message.edit_text(
        "✏️ <b>Изменение ставки</b>\n\n"
        "Напишите новую сумму вашей ставки:",
        parse_mode="HTML"
    )

    # Keep FSM state (waiting_for_bid) and lot_id
    # User will enter new amount via process_bid handler

    logger.info(f"📝 User {callback.from_user.id} wants to change bid for lot {lot_id}")
    await callback.answer()


@router.callback_query(F.data.startswith("stop_participation:"))
async def stop_participation(callback: CallbackQuery, state: FSMContext):
    """Handle stop participation button - user wants to cancel bidding"""
    lot_id = int(callback.data.split(":")[1])

    # Remove user from awaiting_bids
    if callback.from_user.id in awaiting_bids:
        del awaiting_bids[callback.from_user.id]

    # Edit message
    await callback.message.edit_text(
        "❌ <b>Вы перестали участвовать в аукционе</b>\n\n"
        "Ставка не принята.",
        parse_mode="HTML"
    )

    # Restore main menu
    from bot import bot
    from utils import get_user_menu
    menu = await get_user_menu(callback.from_user.id)
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="Используйте меню ниже для навигации:",
        reply_markup=menu
    )

    logger.info(f"❌ User {callback.from_user.id} stopped participating in lot {lot_id}")
    await callback.answer()


@router.callback_query(F.data.startswith("mark_sold:"))
async def handle_mark_sold(callback: CallbackQuery, state: FSMContext):
    """Handle seller marking lot as sold"""
    lot_id = int(callback.data.split(":")[1])

    lot = await db.get_lot(lot_id)

    if not lot:
        await callback.answer("Лот не найден!", show_alert=True)
        return

    # Check if user is the owner
    if lot['owner_id'] != callback.from_user.id:
        await callback.answer("❌ Только владелец лота может пометить его как проданный!", show_alert=True)
        return

    # Check if already sold
    if lot['status'] == 'finished':
        await callback.answer("Этот лот уже помечен как проданный!", show_alert=True)
        return

    # Mark as sold
    await db.update_lot_status(lot_id, 'finished')

    # Update the message to remove the button
    try:
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>Букет помечен как проданный!</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    # Update channel message to show "SOLD"
    if lot.get('channel_message_id'):
        from bot import bot
        from utils import format_sold_message, get_photos_list

        try:
            # Format sold message
            sold_text = format_sold_message(lot, lot['start_price'])

            # Get photos to determine if it's a single photo or media group
            photos = get_photos_list(lot['photos'])

            # Edit message (remove keyboard to prevent further interaction)
            if len(photos) == 1:
                # Single photo - edit caption
                await bot.edit_message_caption(
                    chat_id=config.CHANNEL_ID,
                    message_id=lot['channel_message_id'],
                    caption=sold_text,
                    parse_mode="HTML",
                    reply_markup=None
                )
            else:
                # Media group - edit button message to show sold
                if lot.get('channel_button_message_id'):
                    await bot.edit_message_text(
                        chat_id=config.CHANNEL_ID,
                        message_id=lot['channel_button_message_id'],
                        text=sold_text,
                        parse_mode="HTML",
                        reply_markup=None
                    )
        except Exception as e:
            logger.error(f"Failed to update channel message: {e}")

    await callback.answer("✅ Букет помечен как проданный! Сообщение в канале обновлено.")