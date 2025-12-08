from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import db
from keyboards import get_participate_keyboard
from utils import is_admin, format_lot_message, get_photos_list, format_auction_status
from states import AdminAuth
import config

router = Router()


async def get_moderation_keyboard(lot_id: int):
    """Import to avoid circular dependency"""
    from keyboards import get_moderation_keyboard as _get_moderation_keyboard
    return _get_moderation_keyboard(lot_id)


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Handle /admin command"""
    # Check if already admin
    if await is_admin(message.from_user.id):
        await message.answer("✅ Вы уже авторизованы как администратор!")
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
            await message.answer("✅ Вы успешно авторизованы как администратор!\n\n"
                               "Теперь вы можете модерировать лоты.")
        else:
            await message.answer("✅ Вы уже являетесь администратором!")

        await state.clear()
    else:
        await message.answer("❌ Неверный пароль! Попробуйте еще раз или используйте /admin для начала.")
        await state.clear()


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

        caption = format_lot_message(lot) + format_auction_status(lot)

        photos = get_photos_list(lot['photos'])

        # Add note about multiple photos
        if len(photos) > 1:
            caption += f"\n\n📸 Всего фото: {len(photos)}"

        try:
            # Always publish only first photo to enable timer updates
            sent_message = await bot.send_photo(
                chat_id=config.CHANNEL_ID,
                photo=photos[0],
                caption=caption,
                parse_mode="HTML",
                reply_markup=get_participate_keyboard(lot_id)
            )

            # Save channel message ID
            await db.update_lot_field(lot_id, 'channel_message_id', sent_message.message_id)

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
                await bot.send_message(
                    chat_id=lot['owner_id'],
                    text=f"✅ Ваш лот был одобрен и опубликован в канале!"
                )
            except Exception:
                pass

        except Exception as e:
            await callback.answer(f"Ошибка публикации в канал: {e}", show_alert=True)
            return

    elif action == "reject":
        # Reject lot
        await db.update_lot_status(lot_id, 'rejected')

        # Delete the moderation message
        try:
            await callback.message.delete()
        except Exception:
            # If can't delete, just edit the message
            await callback.message.edit_text(
                f"❌ Лот {lot_id} отклонен."
            )

        # Notify owner
        from bot import bot
        try:
            await bot.send_message(
                chat_id=lot['owner_id'],
                text="❌ Ваш лот был отклонен администратором."
            )
        except Exception:
            pass

    await callback.answer()
