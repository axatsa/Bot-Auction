# from aiogram import Router, F
# from aiogram.types import CallbackQuery, Message, ForceReply
# from aiogram.fsm.context import FSMContext
# from datetime import datetime
# import logging
#
# from database import db
# from keyboards import get_bid_confirmation_keyboard, get_main_menu, get_cancel_keyboard
# from states import Bidding
# from utils import format_lot_message, validate_bid, calculate_end_time
# import config
#
# router = Router()
# logger = logging.getLogger(__name__)
#
#
# @router.callback_query(F.data.startswith("buy:"))
# async def handle_buy(callback: CallbackQuery, state: FSMContext):
#     """Handle purchase of item at fixed price"""
#     lot_id = int(callback.data.split(":")[1])
#
#     lot = await db.get_lot(lot_id)
#
#     if not lot:
#         await callback.answer("Лот не найден!", show_alert=True)
#         return
#
#     if lot['status'] not in ['approved', 'active']:
#         await callback.answer("Товар недоступен!", show_alert=True)
#         return
#
#     if lot.get('lot_type') != 'regular':
#         await callback.answer("Это не обычная продажа!", show_alert=True)
#         return
#
#     # Check if already sold
#     if lot.get('leader_id'):
#         await callback.answer("Товар уже продан!", show_alert=True)
#         return
#
#     from bot import bot
#     from utils import get_photos_list, create_media_group
#
#     # Mark as sold
#     await db.update_lot_field(lot_id, 'leader_id', callback.from_user.id)
#     await db.update_lot_status(lot_id, 'finished')
#
#     # Get seller and buyer info
#     seller = await db.get_user(lot['owner_id'])
#     buyer = await db.get_user(callback.from_user.id)
#
#     seller_username = f"@{seller['username']}" if seller.get('username') else "нет username"
#     buyer_username = f"@{buyer['username']}" if buyer.get('username') else "нет username"
#
#     # Notify buyer
#     try:
#         await bot.send_message(
#             chat_id=callback.from_user.id,
#             text=f"✅ <b>Вы купили букет!</b>\n\n"
#                  f"📦 <b>Товар:</b> {lot['description']}\n"
#                  f"💰 <b>Цена:</b> {int(lot['start_price']):,} сум\n"
#                  f"🏙️ <b>Город:</b> {lot['city']}\n\n"
#                  f"👤 <b>Контакт продавца:</b>\n"
#                  f"Имя: {seller['name']}\n"
#                  f"Username: {seller_username}\n"
#                  f"Телефон: {seller['phone']}\n\n"
#                  f"💬 Свяжитесь с продавцом для получения товара и оплаты",
#             parse_mode="HTML"
#         )
#     except Exception as e:
#         logger.error(f"Failed to notify buyer: {e}")
#
#     # Notify seller
#     try:
#         await bot.send_message(
#             chat_id=lot['owner_id'],
#             text=f"🎉 <b>Ваш букет продан!</b>\n\n"
#                  f"📦 <b>Товар:</b> {lot['description']}\n"
#                  f"💰 <b>Цена:</b> {int(lot['start_price']):,} сум\n\n"
#                  f"👤 <b>Контакт покупателя:</b>\n"
#                  f"Имя: {buyer['name']}\n"
#                  f"Username: {buyer_username}\n"
#                  f"Телефон: {buyer['phone']}\n\n"
#                  f"💬 Свяжитесь с покупателем для передачи товара и получения оплаты",
#             parse_mode="HTML"
#         )
#     except Exception as e:
#         logger.error(f"Failed to notify seller: {e}")
#
#     # Update channel message to show "SOLD"
#     if lot.get('channel_message_id'):
#         try:
#             from utils import format_sold_message, get_photos_list
#
#             # Format sold message
#             sold_text = format_sold_message(lot, lot['start_price'])
#
#             # Get photos to determine if it's a single photo or media group
#             photos = get_photos_list(lot['photos'])
#
#             # Edit message (remove keyboard to prevent further interaction)
#             if len(photos) == 1:
#                 # Single photo - edit caption
#                 await bot.edit_message_caption(
#                     chat_id=config.CHANNEL_ID,
#                     message_id=lot['channel_message_id'],
#                     caption=sold_text,
#                     parse_mode="HTML",
#                     reply_markup=None
#                 )
#             else:
#                 # Media group - can't edit, so we'll try to delete and ignore errors
#                 # Note: Media groups can't have their captions edited easily
#                 try:
#                     await bot.delete_message(
#                         chat_id=config.CHANNEL_ID,
#                         message_id=lot['channel_message_id']
#                     )
#                 except Exception:
#                     pass
#         except Exception as e:
#             logger.error(f"Failed to update channel message: {e}")
#
#     await callback.answer("✅ Вы купили этот букет! Проверьте сообщения от бота.")
#
#
# @router.callback_query(F.data.startswith("participate:"))
# async def handle_participate(callback: CallbackQuery, state: FSMContext):
#     """Handle participation in auction"""
#     lot_id = int(callback.data.split(":")[1])
#
#     lot = await db.get_lot(lot_id)
#
#     if not lot:
#         await callback.answer("Лот не найден!", show_alert=True)
#         return
#
#     if lot['status'] not in ['approved', 'active']:
#         await callback.answer("Аукцион недоступен!", show_alert=True)
#         return
#
#     if lot.get('lot_type') != 'auction':
#         await callback.answer("Это не аукцион! Используйте кнопку 'Купить'", show_alert=True)
#         return
#
#     # Check if auction needs to start
#     if not lot['auction_started']:
#         # Start auction timer
#         end_time = calculate_end_time()
#         await db.start_auction(
#             lot_id=lot_id,
#             start_time=datetime.now().isoformat(),
#             end_time=end_time.isoformat()
#         )
#
#         # Schedule auction completion
#         from scheduler import schedule_auction_completion
#         await schedule_auction_completion(lot_id, end_time)
#
#         # Update channel message
#         from bot import bot
#         from utils import format_auction_status, get_photos_list
#
#         try:
#             updated_text = format_lot_message(lot) + format_auction_status({
#                 **lot,
#                 'auction_started': True,
#                 'end_time': end_time.isoformat()
#             })
#
#             # Try to update message
#             if lot.get('channel_message_id'):
#                 photos = get_photos_list(lot['photos'])
#                 if len(photos) == 1:
#                     await bot.edit_message_caption(
#                         chat_id=config.CHANNEL_ID,
#                         message_id=lot['channel_message_id'],
#                         caption=updated_text,
#                         parse_mode="HTML",
#                         reply_markup=callback.message.reply_markup
#                     )
#         except Exception as e:
#             print(f"Failed to update channel message: {e}")
#
#     # Show lot info and ask for bid
#     lot = await db.get_lot(lot_id)  # Refresh lot data
#
#     # Get bid statistics
#     bids = await db.get_lot_bids(lot_id)
#     bid_count = len(set([bid['user_id'] for bid in bids]))  # Unique participants
#
#     current_price = lot.get('current_price') or lot['start_price']
#     MIN_BID_STEP = 1000
#
#     # Calculate minimum bid
#     if lot.get('current_price') and lot['current_price'] > lot['start_price']:
#         min_bid = lot['current_price'] + MIN_BID_STEP
#     else:
#         min_bid = lot['start_price']
#
#     # Build message text
#     text = "🎯 <b>Участие в аукционе</b>\n\n"
#     text += format_lot_message(lot, include_price=False)
#     text += f"\n💰 <b>Стартовая цена:</b> {int(lot['start_price']):,} сум\n"
#
#     if lot.get('current_price') and lot['current_price'] > lot['start_price']:
#         text += f"🔥 <b>Текущая ставка:</b> {int(lot['current_price']):,} сум\n"
#
#     text += f"👥 <b>Количество участников:</b> {bid_count}\n"
#     text += f"📊 <b>Минимальная ставка:</b> {int(min_bid):,} сум\n"
#     text += f"\n💬 Введите вашу ставку:"
#
#     # Send photo(s) with lot info to user (private) and use ForceReply so reply_to_message exists
#     from bot import bot
#     from utils import get_photos_list, create_media_group
#
#     photos = get_photos_list(lot['photos'])
#
#     # Append a simple marker with lot id so we can identify replies
#     marker = f"\n\n#lot:{lot_id}"
#
#     try:
#         if len(photos) == 0:
#             # No photos
#             sent = await bot.send_message(
#                 chat_id=callback.from_user.id,
#                 text=text + marker,
#                 parse_mode="HTML",
#                 reply_markup=ForceReply(force_reply=True, input_field_placeholder="Введите вашу ставку")
#             )
#         elif len(photos) == 1:
#             # Single photo - send photo with caption + force reply via separate message
#             await bot.send_photo(
#                 chat_id=callback.from_user.id,
#                 photo=photos[0],
#                 caption=text,
#                 parse_mode="HTML"
#             )
#             sent = await bot.send_message(
#                 chat_id=callback.from_user.id,
#                 text="Отправьте вашу ставку как ответ на это сообщение:" + marker,
#                 reply_markup=ForceReply(force_reply=True, input_field_placeholder="Введите вашу ставку")
#             )
#         else:
#             # Multiple photos - send as media group + message with force reply
#             media = create_media_group(photos, text)
#             await bot.send_media_group(
#                 chat_id=callback.from_user.id,
#                 media=media
#             )
#             sent = await bot.send_message(
#                 chat_id=callback.from_user.id,
#                 text="Отправьте вашу ставку как ответ на это сообщение:" + marker,
#                 reply_markup=ForceReply(force_reply=True, input_field_placeholder="Введите вашу ставку")
#             )
#     except Exception as e:
#         # If can't send photo, attempt to reply in channel or fallback
#         logger.error(f"Failed to send photos or DM: {e}")
#         await callback.message.answer(text + marker, parse_mode="HTML", reply_markup=get_cancel_keyboard())
#         await callback.answer()
#         return
#
#     # Do NOT use FSM state here; we rely on reply_to_message marker + confirmation callback data
#     logger.info(f"📍 Sent force-reply to user {callback.from_user.id} for lot {lot_id}")
#     await callback.answer()
#
#
# # Now process replies to the ForceReply message. We don't rely on FSM state.
# @router.message(F.text)
# async def process_bid(message: Message, state: FSMContext):
#     """Process bid amount — only when user replied to bot's ForceReply message that contains marker '#lot:<id>'"""
#     # Ensure this is a reply to the bot message that contains our marker
#     if not message.reply_to_message or not message.reply_to_message.text:
#         # Not a reply -> ignore, let other handlers process
#         return
#
#     reply_text = message.reply_to_message.text
#     if "#lot:" not in reply_text:
#         # Not related to bidding -> ignore
#         return
#
#     # Extract lot_id from marker
#     try:
#         marker_part = [part for part in reply_text.splitlines() if part.strip().startswith("#lot:")][0].strip()
#         lot_id = int(marker_part.split(":")[1])
#     except Exception:
#         logger.warning(f"Couldn't extract lot id from reply_to_message for user {message.from_user.id}")
#         return
#
#     logger.info(f"🎯 process_bid HANDLER CALLED (reply flow). User: {message.from_user.id}, Lot: {lot_id}, Text: '{message.text}'")
#
#     # Check if message has text
#     if not message.text:
#         await message.answer("❌ Пожалуйста, введите числовую ставку!")
#         return
#
#     # Handle cancel (user can send 'Отмена' as text)
#     if message.text.strip().lower() in ["отмена", "cancel", "❌ отмена"]:
#         await message.answer("❌ Отменено.", reply_markup=get_main_menu())
#         return
#
#     # Try to parse the bid amount
#     try:
#         # Remove spaces and replace comma with dot
#         amount_str = message.text.strip().replace(',', '.').replace(' ', '')
#         amount = float(amount_str)
#         logger.info(f"✅ Parsed bid amount: {amount} from input: {message.text}")
#     except ValueError:
#         await message.answer(
#             "❌ Неверный формат!\n\n"
#             "Введите число, например: 1000 или 1000.50"
#         )
#         return
#
#     lot = await db.get_lot(lot_id)
#     if not lot:
#         await message.answer("Лот не найден! Возможно, аукцион завершён.", reply_markup=get_main_menu())
#         return
#
#     # Validate bid against current price
#     current_price = lot.get('current_price') or lot['start_price']
#     is_valid, error_msg = validate_bid(amount, lot['start_price'], current_price)
#     if not is_valid:
#         await message.answer(error_msg)
#         return
#
#     # Ask for confirmation — include amount in callback data so we don't need FSM
#     amount_int = int(amount)  # use integer sum to keep callback_data short
#     # Build a keyboard manually with callback data confirm_bid:<lot_id>:<amount>
#     # Reuse existing get_bid_confirmation_keyboard if it supports passing amount via callback; if not, build simple keyboard here.
#     try:
#         # Try to use existing keyboard factory (it may accept lot_id only). If it doesn't encode amount, we'll send inline keyboard manually.
#         kb = get_bid_confirmation_keyboard(lot_id)
#         # NOTE: if get_bid_confirmation_keyboard doesn't include amount, confirm handler below will read amount from callback data.
#         await message.answer(
#             f"<b>Подтверждение ставки</b>\n\nВаша ставка: {amount_int} сум\nЛот: {lot['description']}\n\nПодтвердить?",
#             parse_mode="HTML",
#             reply_markup=kb
#         )
#     except Exception:
#         # Fallback: create inline keyboard manually
#         from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
#         kb = InlineKeyboardMarkup(inline_keyboard=[
#             [
#                 InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_bid:{lot_id}:{amount_int}"),
#                 InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_bid:{lot_id}")
#             ]
#         ])
#         await message.answer(
#             f"<b>Подтверждение ставки</b>\n\nВаша ставка: {amount_int} сум\nЛот: {lot['description']}\n\nПодтвердить?",
#             parse_mode="HTML",
#             reply_markup=kb
#         )
#
#
# @router.callback_query(F.data.startswith("confirm_bid:"))
# async def confirm_bid(callback: CallbackQuery, state: FSMContext):
#     """Confirm bid — data contains lot_id and amount: confirm_bid:<lot_id>:<amount>"""
#     parts = callback.data.split(":")
#     if len(parts) < 3:
#         await callback.answer()
#         return
#
#     lot_id = int(parts[1])
#     try:
#         amount = float(parts[2])
#     except Exception:
#         await callback.answer("Некорректные данные.", show_alert=True)
#         return
#
#     lot = await db.get_lot(lot_id)
#     if not lot:
#         await callback.message.edit_text("Лот не найден или завершён.")
#         await callback.answer()
#         return
#
#     # Re-validate in case someone else bid
#     current_price = lot.get('current_price') or lot['start_price']
#     is_valid, error_msg = validate_bid(amount, lot['start_price'], current_price)
#     if not is_valid:
#         await callback.message.edit_text(f"❌ {error_msg}", parse_mode="HTML")
#         await callback.answer()
#         return
#
#     # Save bid
#     previous_leader_id = lot.get('leader_id')
#
#     await db.add_bid(lot_id, callback.from_user.id, amount)
#
#     await callback.message.edit_text(
#         f"✅ <b>Ваша ставка принята!</b>\n\n"
#         f"💰 Сумма: {int(amount):,} сум\n"
#         f"🥇 Вы — текущий лидер аукциона!",
#         parse_mode="HTML"
#     )
#
#     # Notify previous leader
#     if previous_leader_id and previous_leader_id != callback.from_user.id:
#         from bot import bot
#         try:
#             await bot.send_message(
#                 chat_id=previous_leader_id,
#                 text=f"⚠️ <b>Вашу ставку перебили!</b>\n\n"
#                      f"📦 Лот: {lot['description']}\n"
#                      f"💰 Новая ставка: {int(amount):,} сум",
#                 parse_mode="HTML"
#             )
#         except Exception:
#             pass
#
#     await callback.answer()
#
#
# @router.callback_query(F.data.startswith("cancel_bid:"))
# async def cancel_bid(callback: CallbackQuery, state: FSMContext):
#     """Cancel bid"""
#     await callback.message.edit_text("Отменено.")
#     await callback.answer()


from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ForceReply
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import logging
import secrets
import re

from database import db
from keyboards import get_bid_confirmation_keyboard, get_main_menu, get_cancel_keyboard
from utils import format_lot_message, validate_bid, calculate_end_time
import config

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("participate:"))
async def handle_participate(callback: CallbackQuery, state: FSMContext):
    """Handle participation in auction using one-time token + ForceReply"""
    lot_id = int(callback.data.split(":")[1])

    lot = await db.get_lot(lot_id)
    if not lot:
        await callback.answer("Лот не найден!", show_alert=True)
        return

    if lot['status'] not in ['approved', 'active']:
        await callback.answer("Аукцион недоступен!", show_alert=True)
        return

    if lot.get('lot_type') != 'auction':
        await callback.answer("Это не аукцион! Используйте кнопку 'Купить'", show_alert=True)
        return

    # Start auction if needed (existing logic)
    if not lot['auction_started']:
        end_time = calculate_end_time()
        await db.start_auction(
            lot_id=lot_id,
            start_time=datetime.now().isoformat(),
            end_time=end_time.isoformat()
        )
        from scheduler import schedule_auction_completion
        await schedule_auction_completion(lot_id, end_time)

        # Attempt to update channel message (existing logic)
        from bot import bot
        from utils import format_auction_status, get_photos_list
        try:
            updated_text = format_lot_message(lot) + format_auction_status({
                **lot,
                'auction_started': True,
                'end_time': end_time.isoformat()
            })
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
            logger.error(f"Failed to update channel message: {e}")

    # Build text for user
    bids = await db.get_lot_bids(lot_id)
    bid_count = len(set([bid['user_id'] for bid in bids]))
    current_price = lot.get('current_price') or lot['start_price']
    MIN_BID_STEP = 1000
    if lot.get('current_price') and lot['current_price'] > lot['start_price']:
        min_bid = lot['current_price'] + MIN_BID_STEP
    else:
        min_bid = lot['start_price']

    text = "🎯 <b>Участие в аукционе</b>\n\n"
    text += format_lot_message(lot, include_price=False)
    text += f"\n💰 <b>Стартовая цена:</b> {int(lot['start_price']):,} сум\n"
    if lot.get('current_price') and lot['current_price'] > lot['start_price']:
        text += f"🔥 <b>Текущая ставка:</b> {int(lot['current_price']):,} сум\n"
    text += f"👥 <b>Количество участников:</b> {bid_count}\n"
    text += f"📊 <b>Минимальная ставка:</b> {int(min_bid):,} сум\n"
    text += f"\n💬 Введите вашу ставку:"

    from bot import bot
    from utils import get_photos_list, create_media_group
    photos = get_photos_list(lot['photos'])

    # Create one-time token (short hex) and save to DB with expiry
    token = secrets.token_hex(4)  # 8 hex chars, short enough
    expires_at = (datetime.now() + timedelta(minutes=15)).isoformat()
    await db.create_bid_token(token=token, lot_id=lot_id, user_id=callback.from_user.id, expires_at=expires_at)

    # Include token in message (user will reply to this message). Keep token concise in text.
    marker = f"\n\nToken: {token} (действует 15 минут) — ответьте на это сообщение вашей ставкой"

    try:
        if len(photos) == 0:
            sent = await bot.send_message(
                chat_id=callback.from_user.id,
                text=text + marker,
                parse_mode="HTML",
                reply_markup=ForceReply(force_reply=True, input_field_placeholder="Введите вашу ставку")
            )
        elif len(photos) == 1:
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=photos[0],
                caption=text,
                parse_mode="HTML"
            )
            sent = await bot.send_message(
                chat_id=callback.from_user.id,
                text="Ответьте на это сообщение вашей ставкой." + marker,
                reply_markup=ForceReply(force_reply=True, input_field_placeholder="Введите вашу ставку")
            )
        else:
            media = create_media_group(photos, text)
            await bot.send_media_group(
                chat_id=callback.from_user.id,
                media=media
            )
            sent = await bot.send_message(
                chat_id=callback.from_user.id,
                text="Ответьте на это сообщение вашей ставкой." + marker,
                reply_markup=ForceReply(force_reply=True, input_field_placeholder="Введите вашу ставку")
            )
    except Exception as e:
        logger.error(f"Failed to DM user or send media: {e}")
        await callback.message.answer(text + marker, parse_mode="HTML", reply_markup=get_cancel_keyboard())
        await callback.answer()
        return

    logger.info(f"Created bid token {token} for user {callback.from_user.id}, lot {lot_id}")
    await callback.answer()


@router.message(F.text)
async def process_bid_reply(message: Message, state: FSMContext):
    """Process reply to ForceReply that contains token in original message text"""
    if not message.reply_to_message or not message.reply_to_message.text:
        return  # not a reply to our token message

    reply_text = message.reply_to_message.text
    m = re.search(r"Token:\s*([0-9a-fA-F]+)", reply_text)
    if not m:
        return  # not our token message

    token = m.group(1)
    token_row = await db.get_bid_token(token)
    if not token_row:
        await message.answer("Сессия для ставки устарела или недействительна. Нажмите кнопку 'Участвовать' снова.", reply_markup=get_main_menu())
        return

    # Check ownership and expiry
    if token_row['user_id'] != message.from_user.id:
        await message.answer("Этот токен предназначен для другого пользователя.", reply_markup=get_main_menu())
        return

    if datetime.fromisoformat(token_row['expires_at']) < datetime.now():
        await db.delete_bid_token(token)
        await message.answer("Сессия истекла. Нажмите 'Участвовать' ещё раз.", reply_markup=get_main_menu())
        return

    lot_id = token_row['lot_id']

    # Parse amount
    if not message.text:
        await message.answer("❌ Пожалуйста, введите числовую ставку!")
        return

    # Handle cancel
    if message.text.strip().lower() in ["отмена", "cancel", "❌ отмена"]:
        await db.delete_bid_token(token)
        await message.answer("❌ Отменено.", reply_markup=get_main_menu())
        return

    try:
        amount_str = message.text.strip().replace(',', '.').replace(' ', '')
        amount = float(amount_str)
    except ValueError:
        await message.answer("❌ Неверный формат! Введите число, например: 1000 или 1000.50")
        return

    lot = await db.get_lot(lot_id)
    if not lot:
        await message.answer("Лот не найден или уже завершён.", reply_markup=get_main_menu())
        await db.delete_bid_token(token)
        return

    # Validate bid against current price
    current_price = lot.get('current_price') or lot['start_price']
    is_valid, error_msg = validate_bid(amount, lot['start_price'], current_price)
    if not is_valid:
        await message.answer(error_msg)
        return

    amount_int = int(amount)

    # Send confirmation with token+amount in callback_data so we don't need FSM
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_bid:{token}:{amount_int}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_bid:{token}")
        ]
    ])

    await message.answer(
        f"<b>Подтверждение ставки</b>\n\nВаша ставка: {amount_int:,} сум\nЛот: {lot['description']}\n\nПодтвердить?",
        parse_mode="HTML",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("confirm_bid:"))
async def confirm_bid(callback: CallbackQuery, state: FSMContext):
    """Confirm bid using token and amount in callback data"""
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer()
        return

    token = parts[1]
    try:
        amount = float(parts[2])
    except Exception:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    token_row = await db.get_bid_token(token)
    if not token_row:
        await callback.answer("Сессия устарела или недействительна.", show_alert=True)
        return

    # Ownership + expiry checks
    if token_row['user_id'] != callback.from_user.id:
        await callback.answer("Этот токен предназначен для другого пользователя.", show_alert=True)
        return

    if datetime.fromisoformat(token_row['expires_at']) < datetime.now():
        await db.delete_bid_token(token)
        await callback.answer("Сессия истекла.", show_alert=True)
        return

    lot_id = token_row['lot_id']
    lot = await db.get_lot(lot_id)
    if not lot:
        await callback.message.edit_text("Лот не найден или завершён.")
        await db.delete_bid_token(token)
        await callback.answer()
        return

    # Re-validate the bid in case price changed
    current_price = lot.get('current_price') or lot['start_price']
    is_valid, error_msg = validate_bid(amount, lot['start_price'], current_price)
    if not is_valid:
        await callback.message.edit_text(f"❌ {error_msg}", parse_mode="HTML")
        await db.delete_bid_token(token)
        await callback.answer()
        return

    # Save bid
    previous_leader_id = lot.get('leader_id')
    await db.add_bid(lot_id, callback.from_user.id, amount)

    await callback.message.edit_text(
        f"✅ <b>Ваша ставка принята!</b>\n\n"
        f"💰 Сумма: {int(amount):,} сум\n"
        f"🥇 Вы — текущий лидер аукциона!",
        parse_mode="HTML"
    )

    # Notify previous leader
    if previous_leader_id and previous_leader_id != callback.from_user.id:
        from bot import bot
        try:
            await bot.send_message(
                chat_id=previous_leader_id,
                text=f"⚠️ <b>Вашу ставку перебили!</b>\n\n"
                     f"📦 Лот: {lot['description']}\n"
                     f"💰 Новая ставка: {int(amount):,} сум",
                parse_mode="HTML"
            )
        except Exception:
            pass

    # Consume token
    await db.delete_bid_token(token)
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_bid:"))
async def cancel_bid(callback: CallbackQuery, state: FSMContext):
    """Cancel bid using token"""
    parts = callback.data.split(":")
    token = parts[1] if len(parts) > 1 else None
    if token:
        await db.delete_bid_token(token)
    await callback.message.edit_text("Отменено.")
    await callback.answer()