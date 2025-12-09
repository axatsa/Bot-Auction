from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import db
from keyboards import get_participate_keyboard, get_buy_keyboard, get_rejection_reasons_keyboard, get_confirm_rejection_keyboard, get_moderation_keyboard, get_admin_menu, get_main_menu
from utils import is_admin, format_lot_message, get_photos_list, format_auction_status
from states import AdminAuth, AdminModeration
import config

router = Router()


@router.message(F.text == "👤 Режим пользователя")
async def switch_to_user_mode(message: Message):
    """Switch admin to user mode"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    await message.answer(
        "👤 <b>Режим пользователя активирован</b>\n\n"
        "Теперь вы можете создавать лоты и участвовать в аукционах.\n\n"
        "Для возврата в админку используйте кнопку '⚙️ Режим администратора'",
        parse_mode="HTML",
        reply_markup=get_main_menu(is_admin=True)
    )


@router.message(F.text == "⚙️ Режим администратора")
async def switch_to_admin_mode(message: Message):
    """Switch user to admin mode"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    await message.answer(
        "⚙️ <b>Режим администратора активирован</b>\n\n"
        "Вы вернулись в панель администратора.",
        parse_mode="HTML",
        reply_markup=get_admin_menu()
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Handle /admin command"""
    # Check if already admin
    if await is_admin(message.from_user.id):
        await message.answer(
            "✅ Вы уже авторизованы как администратор!",
            reply_markup=get_admin_menu()
        )
        return

    # Ask for password
    await message.answer("🔐 Введите пароль администратора:")
    await state.set_state(AdminAuth.waiting_for_password)


@router.message(AdminAuth.waiting_for_password)
async def process_admin_password(message: Message, state: FSMContext):
    """Process admin password"""
    password = message.text.strip()

    # Delete message with password for security
    try:
        await message.delete()
    except Exception:
        pass

    if password == config.ADMIN_PASSWORD:
        # Add user as admin
        username = message.from_user.username
        success = await db.add_admin(message.from_user.id, username)

        if success:
            await message.answer(
                "✅ <b>Вы успешно авторизованы как администратор!</b>\n\n"
                "Теперь вы можете модерировать лоты.\n\n"
                "Используйте кнопку 🔔 Модерация для просмотра лотов на модерации.",
                parse_mode="HTML",
                reply_markup=get_admin_menu()
            )
        else:
            await message.answer(
                "✅ Вы уже являетесь администратором!",
                reply_markup=get_admin_menu()
            )

        await state.clear()
    else:
        await message.answer("❌ Неверный пароль! Попробуйте еще раз или используйте /admin для начала.")
        await state.clear()


@router.message(F.text == "📜 История")
async def show_history(message: Message):
    """Show history and statistics"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    # Get statistics
    stats = await db.get_stats()

    # Build statistics message
    text = "📜 <b>История и статистика</b>\n\n"

    text += "👥 <b>Пользователи:</b>\n"
    text += f"Всего: {stats['total_users']}\n\n"

    text += "📦 <b>Лоты:</b>\n"
    text += f"Всего создано: {stats['total_lots']}\n"

    lots_by_status = stats.get('lots_by_status', {})
    if 'pending' in lots_by_status:
        text += f"⏳ На модерации: {lots_by_status['pending']}\n"
    if 'approved' in lots_by_status:
        text += f"✅ Одобрено: {lots_by_status['approved']}\n"
    if 'active' in lots_by_status:
        text += f"🔥 Активных: {lots_by_status['active']}\n"
    if 'finished' in lots_by_status:
        text += f"✅ Завершено: {lots_by_status['finished']}\n"
    if 'rejected' in lots_by_status:
        text += f"❌ Отклонено: {lots_by_status['rejected']}\n"
    if 'no_bids' in lots_by_status:
        text += f"💤 Без ставок: {lots_by_status['no_bids']}\n"

    text += f"\n💰 <b>Торги:</b>\n"
    text += f"Всего ставок: {stats['total_bids']}\n"
    text += f"Успешных аукционов: {stats['finished_auctions']}\n"

    if stats['avg_final_price'] > 0:
        text += f"Средняя цена продажи: {int(stats['avg_final_price']):,} тенге\n"

    await message.answer(text, parse_mode="HTML")

    # Ask what history to show
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Завершённые", callback_data="history:finished")
    kb.button(text="🔥 Активные", callback_data="history:active")
    kb.button(text="❌ Отклонённые", callback_data="history:rejected")
    kb.button(text="📋 Все лоты", callback_data="history:all")
    kb.adjust(2, 2)

    await message.answer(
        "📋 <b>Выберите что показать:</b>",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data.startswith("history:"))
async def show_history_lots(callback: CallbackQuery):
    """Show lots history by status"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    status_type = callback.data.split(":")[1]

    # Map status
    status_map = {
        "finished": "finished",
        "active": "active",
        "rejected": "rejected",
        "all": None
    }

    status = status_map.get(status_type)

    # Get history
    lots = await db.get_lots_history(status=status, limit=20)

    if not lots:
        await callback.message.answer("📭 <b>Нет лотов</b>", parse_mode="HTML")
        await callback.answer()
        return

    status_names = {
        "finished": "✅ Завершённые",
        "active": "🔥 Активные",
        "rejected": "❌ Отклонённые",
        "all": "📋 Все"
    }

    await callback.message.answer(
        f"📜 <b>{status_names[status_type]} лоты (последние 20):</b>",
        parse_mode="HTML"
    )

    from bot import bot

    for lot in lots:
        owner = await db.get_user(lot['owner_id'])
        owner_name = owner['name'] if owner else "Неизвестно"

        text = f"🆔 <b>Лот #{lot['id']}</b>\n"
        text += f"👤 Продавец: {owner_name}\n"
        text += f"📝 {lot['description'][:50]}...\n" if len(lot['description']) > 50 else f"📝 {lot['description']}\n"
        text += f"🏙️ {lot['city']}\n"
        text += f"💰 Старт: {int(lot['start_price']):,} тенге\n"

        if lot.get('current_price') and lot['current_price'] > lot['start_price']:
            text += f"🔥 Финал: {int(lot['current_price']):,} тенге\n"

        # Status
        status_emoji = {
            "pending": "⏳",
            "approved": "✅",
            "active": "🔥",
            "finished": "✅",
            "rejected": "❌",
            "no_bids": "💤"
        }
        text += f"\n{status_emoji.get(lot['status'], '❓')} Статус: {lot['status']}\n"

        # Winner info if finished
        if lot['status'] == 'finished' and lot.get('leader_id'):
            winner = await db.get_user(lot['leader_id'])
            if winner:
                text += f"🏆 Победитель: {winner['name']}\n"

        # Show first photo if available
        photos = get_photos_list(lot['photos'])
        if photos:
            try:
                await bot.send_photo(
                    chat_id=callback.from_user.id,
                    photo=photos[0],
                    caption=text,
                    parse_mode="HTML"
                )
            except Exception:
                await bot.send_message(
                    chat_id=callback.from_user.id,
                    text=text,
                    parse_mode="HTML"
                )
        else:
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=text,
                parse_mode="HTML"
            )

    await callback.answer()


@router.message(F.text == "🔔 Модерация")
async def show_moderation(message: Message):
    """Show pending lots for moderation"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора!")
        return

    # Get pending lots
    pending_lots = await db.get_pending_lots()

    if not pending_lots:
        await message.answer(
            "✅ <b>Нет лотов на модерации</b>\n\n"
            "Все лоты обработаны!",
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"🔔 <b>Лотов на модерации: {len(pending_lots)}</b>\n\n"
        f"Отправляю их вам по очереди...",
        parse_mode="HTML"
    )

    # Send each lot for moderation
    from bot import bot
    from utils import create_media_group

    for lot in pending_lots:
        owner = await db.get_user(lot['owner_id'])
        owner_username = f"@{owner['username']}" if owner.get('username') else "нет username"

        caption = f"🔔 <b>Новый лот на модерацию</b>\n\n"
        caption += f"От: {owner['name']} ({owner_username})\n"
        caption += f"ID лота: {lot['id']}\n\n"
        caption += format_lot_message(lot)

        photos = get_photos_list(lot['photos'])

        if len(photos) == 1:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=photos[0],
                caption=caption,
                parse_mode="HTML",
                reply_markup=get_moderation_keyboard(lot['id'])
            )
        else:
            # Multiple photos - send media group
            media = create_media_group(photos, caption)
            await bot.send_media_group(chat_id=message.from_user.id, media=media)

            # Send buttons separately
            await bot.send_message(
                chat_id=message.from_user.id,
                text="<b>Одобрить или отклонить?</b>",
                parse_mode="HTML",
                reply_markup=get_moderation_keyboard(lot['id'])
            )


@router.callback_query(F.data.startswith("moderate:"))
async def handle_moderation(callback: CallbackQuery):
    """Handle lot moderation"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    parts = callback.data.split(":")
    action = parts[1]
    lot_id = int(parts[2])

    lot = await db.get_lot(lot_id)

    if not lot:
        await callback.answer("Лот не найден!", show_alert=True)
        return

    if action == "approve":
        # Approve lot and publish to channel
        await db.update_lot_status(lot_id, 'approved')

        # Publish to channel
        from bot import bot

        # Add lot type indicator to caption
        lot_type_label = "🔥 Аукцион" if lot.get('lot_type') == 'auction' else "💐 Букет на продажу"
        caption = f"<b>{lot_type_label}</b>\n\n"
        caption += format_lot_message(lot)

        if lot.get('lot_type') == 'auction':
            caption += format_auction_status(lot)

        photos = get_photos_list(lot['photos'])

        # Choose keyboard based on lot type
        # Import bot_username for deep linking
        from bot import bot_username

        if lot.get('lot_type') == 'auction':
            keyboard = get_participate_keyboard(lot_id, bot_username)
            button_text = "👇 Нажмите чтобы участвовать в аукционе"
        else:
            keyboard = get_buy_keyboard(lot_id, bot_username)
            button_text = "👇 Нажмите чтобы купить"

        try:
            if len(photos) == 1:
                # Single photo
                sent_message = await bot.send_photo(
                    chat_id=config.CHANNEL_ID,
                    photo=photos[0],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                # Save channel message ID
                await db.update_lot_field(lot_id, 'channel_message_id', sent_message.message_id)
            else:
                # Multiple photos - send as media group
                from utils import create_media_group

                media = create_media_group(photos, caption)
                sent_messages = await bot.send_media_group(
                    chat_id=config.CHANNEL_ID,
                    media=media
                )

                # Save first message ID for tracking
                await db.update_lot_field(lot_id, 'channel_message_id', sent_messages[0].message_id)

                # Send button in separate message
                await bot.send_message(
                    chat_id=config.CHANNEL_ID,
                    text=button_text,
                    reply_markup=keyboard
                )

            # Delete the moderation message
            try:
                await callback.message.delete()
            except Exception:
                # If can't delete, just edit the message
                await callback.message.edit_text(
                    f"✅ Лот {lot_id} одобрен и опубликован в канале!"
                )

            # Notify owner
            owner = await db.get_user(lot['owner_id'])
            try:
                if lot.get('lot_type') == 'auction':
                    notification_text = (
                        f"🎉 <b>Отличная новость!</b>\n\n"
                        f"Ваш лот одобрен и опубликован в канале\n\n"
                        f"📦 <b>Лот:</b> {lot['description']}\n"
                        f"💰 <b>Стартовая цена:</b> {int(lot['start_price']):,} тенге\n"
                        f"⏰ <b>Длительность:</b> 2 часа\n\n"
                        f"Аукцион начнётся когда кто-то сделает первую ставку"
                    )
                else:
                    notification_text = (
                        f"🎉 <b>Отличная новость!</b>\n\n"
                        f"Ваш букет одобрен и опубликован в канале\n\n"
                        f"📦 <b>Товар:</b> {lot['description']}\n"
                        f"💰 <b>Цена:</b> {int(lot['start_price']):,} тенге\n\n"
                        f"Ожидайте покупателя!"
                    )

                await bot.send_message(
                    chat_id=lot['owner_id'],
                    text=notification_text,
                    parse_mode="HTML"
                )
            except Exception:
                pass

        except Exception as e:
            await callback.answer(f"Ошибка публикации в канал: {e}", show_alert=True)
            return

    elif action == "reject":
        # Ask for confirmation before rejecting
        await callback.message.edit_text(
            f"❌ <b>Вы уверены, что хотите отклонить этот лот?</b>\n\n"
            f"📦 Лот #{lot_id}\n"
            f"👤 От: {lot['owner_id']}\n\n"
            f"После подтверждения вам нужно будет указать причину отклонения.",
            parse_mode="HTML",
            reply_markup=get_confirm_rejection_keyboard(lot_id)
        )

    await callback.answer()


@router.callback_query(F.data.startswith("confirm_reject:"))
async def confirm_rejection(callback: CallbackQuery, state: FSMContext):
    """Confirm lot rejection and ask for reason"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    lot_id = int(callback.data.split(":")[1])

    lot = await db.get_lot(lot_id)
    if not lot:
        await callback.answer("Лот не найден!", show_alert=True)
        return

    # Show reason selection
    await callback.message.edit_text(
        f"📝 <b>Выберите причину отклонения лота #{lot_id}:</b>",
        parse_mode="HTML",
        reply_markup=get_rejection_reasons_keyboard(lot_id)
    )

    # Save lot_id to state
    await state.update_data(rejecting_lot_id=lot_id)

    await callback.answer()


@router.callback_query(F.data.startswith("cancel_reject:"))
async def cancel_rejection(callback: CallbackQuery, state: FSMContext):
    """Cancel lot rejection"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    lot_id = int(callback.data.split(":")[1])
    lot = await db.get_lot(lot_id)

    if not lot:
        await callback.answer("Лот не найден!", show_alert=True)
        return

    # Return to moderation view
    from utils import format_lot_message, get_photos_list, create_media_group
    from keyboards import get_moderation_keyboard

    owner = await db.get_user(lot['owner_id'])
    owner_username = f"@{owner['username']}" if owner.get('username') else "нет username"

    caption = f"🔔 <b>Новый лот на модерацию</b>\n\n"
    caption += f"От: {owner['name']} ({owner_username})\n"
    caption += f"ID лота: {lot_id}\n\n"
    caption += format_lot_message(lot)

    await callback.message.edit_text(
        caption,
        parse_mode="HTML",
        reply_markup=get_moderation_keyboard(lot_id)
    )

    await callback.answer("Отклонение отменено")
    await state.clear()


@router.callback_query(F.data.startswith("reject_reason:"))
async def process_rejection_reason(callback: CallbackQuery, state: FSMContext):
    """Process rejection reason selection"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return

    parts = callback.data.split(":")
    lot_id = int(parts[1])
    reason_code = parts[2]

    lot = await db.get_lot(lot_id)
    if not lot:
        await callback.answer("Лот не найден!", show_alert=True)
        return

    # Handle "back" button
    if reason_code == "back":
        await cancel_rejection(callback, state)
        return

    # Reason mapping
    reasons = {
        "bad_photos": "📸 Плохое качество фото. Пожалуйста, загрузите более чёткие фотографии товара при хорошем освещении.",
        "incomplete_desc": "📝 Неполное описание. Добавьте больше деталей о товаре: состояние, размер, особенности.",
        "rules_violation": "🚫 Нарушение правил платформы. Пожалуйста, ознакомьтесь с правилами публикации лотов.",
        "inappropriate": "❌ Неподходящий товар для нашей платформы."
    }

    if reason_code == "custom":
        # Ask admin to write custom reason
        await callback.message.edit_text(
            f"✏️ <b>Напишите причину отклонения лота #{lot_id}:</b>\n\n"
            f"Эта причина будет отправлена владельцу лота.",
            parse_mode="HTML"
        )
        await state.set_state(AdminModeration.waiting_for_rejection_reason)
        await state.update_data(rejecting_lot_id=lot_id)
        await callback.answer()
    else:
        # Use predefined reason
        reason = reasons.get(reason_code, "Лот не соответствует требованиям.")
        await reject_lot_with_reason(lot_id, reason, callback, state)


async def reject_lot_with_reason(lot_id: int, reason: str, callback: CallbackQuery, state: FSMContext):
    """Reject lot with specified reason"""
    from bot import bot

    lot = await db.get_lot(lot_id)
    if not lot:
        await callback.message.edit_text("❌ Лот не найден.")
        await state.clear()
        return

    # Update lot status
    await db.update_lot_status(lot_id, 'rejected')

    # Notify owner
    try:
        await bot.send_message(
            chat_id=lot['owner_id'],
            text=f"❌ <b>Ваш лот был отклонён</b>\n\n"
                 f"📦 Лот: {lot['description']}\n\n"
                 f"<b>Причина:</b>\n{reason}\n\n"
                 f"💡 Исправьте замечания и создайте лот заново.",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Failed to notify owner: {e}")

    # Update message for admin
    await callback.message.edit_text(
        f"✅ Лот #{lot_id} отклонён.\n\n"
        f"Причина отправлена владельцу:\n{reason}"
    )

    await callback.answer("Лот отклонён")
    await state.clear()


@router.message(AdminModeration.waiting_for_rejection_reason, F.text)
async def process_custom_rejection_reason(message: Message, state: FSMContext):
    """Process custom rejection reason from admin"""
    if not await is_admin(message.from_user.id):
        return

    data = await state.get_data()
    lot_id = data.get('rejecting_lot_id')

    if not lot_id:
        await message.answer("❌ Ошибка: не найден ID лота.")
        await state.clear()
        return

    custom_reason = message.text.strip()

    if len(custom_reason) < 10:
        await message.answer("❌ Причина слишком короткая. Напишите более подробно (минимум 10 символов).")
        return

    # Create a dummy callback for the reject function
    class DummyCallback:
        def __init__(self, msg):
            self.message = msg

    await reject_lot_with_reason(lot_id, custom_reason, DummyCallback(message), state)
