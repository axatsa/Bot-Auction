from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from keyboards import get_draft_edit_keyboard, get_draft_preview_keyboard, get_main_menu, get_cancel_keyboard, get_moderation_keyboard, get_size_keyboard, get_wear_keyboard, get_delete_confirmation_keyboard, get_city_keyboard
from states import LotCreation
from utils import format_lot_message, get_photos_list, photos_to_string, create_media_group, get_user_menu
import config

router = Router()


@router.message(LotCreation.waiting_for_photos, F.photo)
async def process_photos(message: Message, state: FSMContext):
    """Collect photos silently; confirm once when user finishes with 'Готово'"""
    data = await state.get_data()
    photos = data.get('photos', [])

    MAX_PHOTOS = 10

    # If already at limit, just keep state and do not spam
    if len(photos) >= MAX_PHOTOS:
        await state.set_state(LotCreation.waiting_for_photos)
        return

    # Add new photo and stay on this step without confirmations
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await state.set_state(LotCreation.waiting_for_photos)


@router.message(LotCreation.waiting_for_photos, F.text)
async def cancel_photos(message: Message, state: FSMContext):
    """Handle controls during photo upload"""
    text = message.text.strip().lower()

    # Cancel
    if text in ["❌ отмена", "отмена", "cancel"]:
        await state.clear()
        menu = await get_user_menu(message.from_user.id)
        await message.answer("❌ Создание лота отменено.", reply_markup=menu)
        return

    # Back (on first step -> back to menu)
    if text in ["◀️ назад", "назад", "back"]:
        await state.clear()
        menu = await get_user_menu(message.from_user.id)
        await message.answer("◀️ Возврат в меню.", reply_markup=menu)
        return

    # Finish photos batch
    if text in ["готово", "далее", "продолжить"]:
        data = await state.get_data()
        photos = data.get('photos', [])
        if not photos:
            await message.answer(
                "❌ Вы не загрузили ни одной фотографии. Пожалуйста, отправьте хотя бы одно фото.",
                reply_markup=get_cancel_keyboard()
            )
            return

        await message.answer(
            f"✅ Фотографии загружены: {len(photos)}/10\n\nТеперь введите описание товара.",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(LotCreation.waiting_for_description)
        return

    # Any other text -> hint
    await message.answer(
        "📸 Отправляйте фото товара. Когда закончите — напишите 'Готово'.\nИли нажмите '❌ Отмена' для отмены.",
        reply_markup=get_cancel_keyboard()
    )


@router.message(LotCreation.waiting_for_photos)
async def invalid_photos(message: Message):
    """Handle invalid photo input (non-text, non-photo)"""
    await message.answer(
        "Пожалуйста, отправьте фото товара. Когда закончите — введите 'Готово'.",
        reply_markup=get_cancel_keyboard()
    )


@router.message(LotCreation.waiting_for_description, F.text)
async def process_description(message: Message, state: FSMContext):
    """Process lot description"""
    text = message.text.strip()

    # Cancel
    if text.lower() in ["❌ отмена", "отмена", "cancel"]:
        await state.clear()
        menu = await get_user_menu(message.from_user.id)
        await message.answer("❌ Создание лота отменено.", reply_markup=menu)
        return

    # Back -> photos
    if text.lower() in ["◀️ назад", "назад", "back"]:
        await message.answer(
            "📸 Вернитесь к загрузке фото. Отправляйте фото и напишите 'Готово' когда закончите.",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(LotCreation.waiting_for_photos)
        return

    # Check if user has added photos
    data = await state.get_data()
    photos = data.get('photos', [])

    if not photos:
        await message.answer(
            "❌ Сначала загрузите хотя бы одно фото товара!",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(LotCreation.waiting_for_photos)
        return

    # Validate description length
    MIN_DESCRIPTION_LENGTH = 10
    MAX_DESCRIPTION_LENGTH = 500

    if len(message.text) < MIN_DESCRIPTION_LENGTH:
        await message.answer(
            f"❌ Описание слишком короткое!\n\n"
            f"Минимум: {MIN_DESCRIPTION_LENGTH} символов\n"
            f"Ваше описание: {len(message.text)} символов\n\n"
            f"Добавьте больше деталей о товаре.",
            reply_markup=get_cancel_keyboard()
        )
        return

    if len(message.text) > MAX_DESCRIPTION_LENGTH:
        await message.answer(
            f"❌ Описание слишком длинное!\n\n"
            f"Максимум: {MAX_DESCRIPTION_LENGTH} символов\n"
            f"Ваше описание: {len(message.text)} символов\n\n"
            f"Пожалуйста, сократите описание.",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(description=message.text)

    from keyboards import get_city_keyboard

    await message.answer(
        "🏙️ <b>Шаг 2/5 - Город</b>\n\n"
        "В каком городе находится товар?\n\n"
        "💡 <b>Совет:</b> Покупатель узнает где можно забрать товар",
        parse_mode="HTML",
        reply_markup=get_city_keyboard()
    )
    await state.set_state(LotCreation.waiting_for_city)


@router.message(LotCreation.waiting_for_city, F.text)
async def process_city(message: Message, state: FSMContext):
    """Process lot city"""
    text = message.text.strip()

    # Cancel
    if text.lower() in ["❌ отмена", "отмена", "cancel"]:
        await state.clear()
        menu = await get_user_menu(message.from_user.id)
        await message.answer("❌ Создание лота отменено.", reply_markup=menu)
        return

    # Back -> to description
    if text.lower() in ["◀️ назад", "назад", "back"]:
        await message.answer(
            "✍️ Введите описание товара:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(LotCreation.waiting_for_description)
        return

    # Handle custom city input
    if text == "✏️ Другой город":
        await message.answer(
            "✏️ Введите название вашего города:",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Validate city name
    if len(message.text) < 2:
        await message.answer(
            "❌ Укажите корректное название города",
            reply_markup=get_city_keyboard()
        )
        return

    await state.update_data(city=message.text)

    from keyboards import get_size_keyboard

    await message.answer(
        "📏 <b>Шаг 3/6 - Размер букета</b>\n\n"
        "Выберите размер букета:",
        parse_mode="HTML",
        reply_markup=get_size_keyboard()
    )
    await state.set_state(LotCreation.waiting_for_size)


@router.message(LotCreation.waiting_for_size, F.text)
async def process_size(message: Message, state: FSMContext):
    """Process lot size"""
    text = message.text.strip()

    # Cancel
    if text.lower() in ["❌ отмена", "отмена", "cancel"]:
        await state.clear()
        menu = await get_user_menu(message.from_user.id)
        await message.answer("❌ Создание лота отменено.", reply_markup=menu)
        return

    # Back -> to city
    if text.lower() in ["◀️ назад", "назад", "back"]:
        await message.answer(
            "🏙️ Выберите город:",
            reply_markup=get_city_keyboard()
        )
        await state.set_state(LotCreation.waiting_for_city)
        return

    # Validate size selection
    valid_sizes = ["Маленький", "Средний", "Большой", "Огромный"]
    if text not in valid_sizes:
        await message.answer(
            "❌ Пожалуйста, выберите размер из предложенных вариантов.",
            reply_markup=get_size_keyboard()
        )
        return

    await state.update_data(size=text)

    from keyboards import get_wear_keyboard

    await message.answer(
        "🌸 <b>Шаг 4/6 - Свежесть букета</b>\n\n"
        "Выберите свежесть букета:",
        parse_mode="HTML",
        reply_markup=get_wear_keyboard()
    )
    await state.set_state(LotCreation.waiting_for_wear)


@router.message(LotCreation.waiting_for_wear, F.text)
async def process_wear(message: Message, state: FSMContext):
    """Process lot wear"""
    text = message.text.strip()

    # Cancel
    if text.lower() in ["❌ отмена", "отмена", "cancel"]:
        await state.clear()
        menu = await get_user_menu(message.from_user.id)
        await message.answer("❌ Создание лота отменено.", reply_markup=menu)
        return

    # Back -> to size
    if text.lower() in ["◀️ назад", "назад", "back"]:
        await message.answer(
            "📏 Выберите размер букета:",
            parse_mode="HTML",
            reply_markup=get_size_keyboard()
        )
        await state.set_state(LotCreation.waiting_for_size)
        return

    # Validate wear selection
    valid_wear_options = ["Сегодняшняя", "1 дневная", "2 дневная", "Более 3 дней"]
    if message.text not in valid_wear_options:
        await message.answer(
            "❌ Пожалуйста, выберите свежесть из предложенных вариантов.",
            reply_markup=get_wear_keyboard()
        )
        return

    await state.update_data(wear=message.text)

    # Check lot type to show appropriate message
    data = await state.get_data()
    lot_type = data.get('lot_type', 'auction')

    if lot_type == 'auction':
        price_text = (
            "💰 <b>Шаг 5/6 - Стартовая цена</b>\n\n"
            "Укажите стартовую цену для аукциона (в тенгеах)\n\n"
            "💡 <b>Совет:</b> Оптимальная стартовая цена - 60-70% от желаемой"
        )
    else:
        price_text = (
            "💰 <b>Шаг 5/6 - Цена</b>\n\n"
            "Укажите цену букета (в тенгеах)\n\n"
            "💡 <b>Совет:</b> Указывайте справедливую цену за букет"
        )

    await message.answer(
        price_text,
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LotCreation.waiting_for_price)


@router.message(LotCreation.waiting_for_price, F.text)
async def process_price(message: Message, state: FSMContext):
    """Process lot price and create draft"""
    text = message.text.strip()

    # Cancel
    if text.lower() in ["❌ отмена", "отмена", "cancel"]:
        await state.clear()
        menu = await get_user_menu(message.from_user.id)
        await message.answer("❌ Создание лота отменено.", reply_markup=menu)
        return

    # Back -> to wear
    if text.lower() in ["◀️ назад", "назад", "back"]:
        await message.answer(
            "🌸 Выберите состояние букета:",
            parse_mode="HTML",
            reply_markup=get_wear_keyboard()
        )
        await state.set_state(LotCreation.waiting_for_wear)
        return

    try:
        # Parse price
        price_str = text.replace(',', '').replace(' ', '')
        price = float(price_str)

        # Validate price
        if price <= 0:
            raise ValueError("negative")

        if price < 1000:
            await message.answer(
                "❌ Минимальная стартовая цена: 1,000 тенге",
                reply_markup=get_cancel_keyboard()
            )
            return

        await state.update_data(price=price)

        # Create lot in database
        data = await state.get_data()
        lot_type = data.get('lot_type', 'auction')  # Default to auction
        lot_id = await db.create_lot(
            owner_id=message.from_user.id,
            photos=photos_to_string(data['photos']),
            description=data['description'],
            city=data['city'],
            size=data['size'],
            wear=data['wear'],
            start_price=price,
            lot_type=lot_type
        )

        await state.update_data(lot_id=lot_id)

        # Show draft with preview
        await show_lot_draft(message, lot_id, state)
        await state.set_state(LotCreation.editing_draft)

    except ValueError:
        await message.answer(
            "❌ Введите корректное число (например: 50000 или 50 000)",
            reply_markup=get_cancel_keyboard()
        )


async def show_lot_draft(message: Message, lot_id: int, state: FSMContext):
    """Show lot draft with edit buttons"""
    lot = await db.get_lot(lot_id)

    if not lot:
        await message.answer(
            "❌ Ошибка: лот не найден.",
            reply_markup=await get_user_menu(message.from_user.id)
        )
        await state.clear()
        return

    # Build preview caption
    lot_type_label = "🔥 Аукцион" if lot.get('lot_type') == 'auction' else "💐 Букет на продажу"
    caption = f"✅ <b>Шаг 6/6 - Предпросмотр</b>\n\n"
    caption += f"<b>Тип:</b> {lot_type_label}\n\n"
    caption += format_lot_message(lot)
    caption += "\n\n<i>Так увидят ваш лот покупатели в канале</i>"

    photos = get_photos_list(lot['photos'])

    if len(photos) == 1:
        await message.answer_photo(
            photo=photos[0],
            caption=caption,
            parse_mode="HTML",
            reply_markup=get_draft_preview_keyboard(lot_id)
        )
    else:
        media = create_media_group(photos, caption)
        await message.answer_media_group(media)
        await message.answer(
            "📋 <b>Выберите действие:</b>\n\n"
            "Вы можете отредактировать лот или опубликовать его",
            parse_mode="HTML",
            reply_markup=get_draft_preview_keyboard(lot_id)
        )


@router.callback_query(F.data.startswith("edit_draft:"))
async def handle_draft_edit(callback: CallbackQuery, state: FSMContext):
    """Handle draft editing"""
    parts = callback.data.split(":")
    action = parts[1]
    lot_id = int(parts[2])

    await state.update_data(lot_id=lot_id)

    if action == "edit":
        # Show edit menu with 6 options + back button
        await callback.message.edit_text(
            "✏️ <b>Редактирование лота</b>\n\n"
            "Выберите что хотите изменить:",
            parse_mode="HTML",
            reply_markup=get_draft_edit_keyboard(lot_id)
        )
        await callback.answer()
        return

    elif action == "back":
        # Return to preview
        await show_lot_draft(callback.message, lot_id, state)
        await callback.answer()
        return

    elif action == "publish":
        # Send to moderation
        await db.update_lot_status(lot_id, 'pending')

        menu = await get_user_menu(callback.from_user.id)
        await callback.message.answer(
            "🎉 <b>Готово!</b>\n\n"
            "Ваш лот отправлен на модерацию администратору\n\n"
            "⏳ Обычно проверка занимает 5-15 минут\n\n"
            "Мы уведомим вас когда лот будет одобрен и опубликован",
            parse_mode="HTML",
            reply_markup=menu
        )

        # Notify admins
        lot = await db.get_lot(lot_id)
        owner = await db.get_user(lot['owner_id'])

        # Format username safely
        owner_username = f"@{owner['username']}" if owner.get('username') else "нет username"

        # Get all admin IDs from database
        admin_ids = await db.get_all_admin_ids()

        for admin_id in admin_ids:
            try:
                caption = f"🔔 <b>Новый лот на модерацию</b>\n\n"
                caption += f"От: {owner['name']} ({owner_username})\n"
                caption += f"ID лота: {lot_id}\n\n"
                caption += format_lot_message(lot)

                photos = get_photos_list(lot['photos'])

                if len(photos) == 1:
                    from bot import bot
                    await bot.send_photo(
                        chat_id=admin_id,
                        photo=photos[0],
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=get_moderation_keyboard(lot_id)
                    )
                else:
                    from bot import bot
                    media = create_media_group(photos, caption)
                    await bot.send_media_group(chat_id=admin_id, media=media)
                    await bot.send_message(
                        chat_id=admin_id,
                        text="Одобрить или отклонить?",
                        reply_markup=get_moderation_keyboard(lot_id)
                    )
            except Exception as e:
                print(f"Failed to notify admin {admin_id}: {e}")

        await state.clear()

    elif action == "photos":
        await callback.message.answer(
            "Отправьте новые фото:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(LotCreation.edit_photos)

    elif action == "description":
        await callback.message.answer(
            "Введите новое описание:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(LotCreation.edit_description)

    elif action == "city":
        await callback.message.answer(
            "Введите новый город:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(LotCreation.edit_city)

    elif action == "size":
        await callback.message.answer(
            "Выберите новый размер:",
            reply_markup=get_size_keyboard()
        )
        await state.set_state(LotCreation.edit_size)

    elif action == "price":
        await callback.message.answer(
            "Введите новую цену:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(LotCreation.edit_price)

    elif action == "wear":
        await callback.message.answer(
            "Выберите новую свежесть:",
            reply_markup=get_wear_keyboard()
        )
        await state.set_state(LotCreation.edit_wear)

    await callback.answer()


# Edit handlers
@router.message(LotCreation.edit_photos, F.photo)
async def edit_photos(message: Message, state: FSMContext):
    """Edit lot photos"""
    data = await state.get_data()
    photos = data.get('temp_photos', [])
    photos.append(message.photo[-1].file_id)

    await state.update_data(temp_photos=photos)
    await message.answer(f"Фото добавлено ({len(photos)}). Отправьте еще или введите 'Готово'")


@router.message(LotCreation.edit_photos, F.text)
async def finish_edit_photos(message: Message, state: FSMContext):
    """Finish editing photos"""
    data = await state.get_data()
    lot_id = data['lot_id']

    if message.text == "❌ Отмена":
        await message.answer(
            "✏️ <b>Редактирование лота</b>\n\n"
            "Выберите что хотите изменить:",
            parse_mode="HTML",
            reply_markup=get_draft_edit_keyboard(lot_id)
        )
        await state.set_state(LotCreation.editing_draft)
        return

    photos = data.get('temp_photos', [])
    if photos:
        await db.update_lot_field(lot_id, 'photos', photos_to_string(photos))

    await message.answer(
        "✅ Фото обновлены!\n\n✏️ <b>Редактирование лота</b>\n\n"
        "Выберите что хотите изменить:",
        parse_mode="HTML",
        reply_markup=get_draft_edit_keyboard(lot_id)
    )
    await state.set_state(LotCreation.editing_draft)
    await state.update_data(temp_photos=[])


@router.message(LotCreation.edit_description, F.text)
async def edit_description(message: Message, state: FSMContext):
    """Edit lot description"""
    data = await state.get_data()
    lot_id = data['lot_id']

    if message.text == "❌ Отмена":
        await message.answer(
            "✏️ <b>Редактирование лота</b>\n\n"
            "Выберите что хотите изменить:",
            parse_mode="HTML",
            reply_markup=get_draft_edit_keyboard(lot_id)
        )
        await state.set_state(LotCreation.editing_draft)
        return

    await db.update_lot_field(lot_id, 'description', message.text)
    await message.answer(
        "✅ Описание обновлено!\n\n✏️ <b>Редактирование лота</b>\n\n"
        "Выберите что хотите изменить:",
        parse_mode="HTML",
        reply_markup=get_draft_edit_keyboard(lot_id)
    )
    await state.set_state(LotCreation.editing_draft)


@router.message(LotCreation.edit_city, F.text)
async def edit_city(message: Message, state: FSMContext):
    """Edit lot city"""
    data = await state.get_data()
    lot_id = data['lot_id']

    if message.text == "❌ Отмена":
        await message.answer(
            "✏️ <b>Редактирование лота</b>\n\n"
            "Выберите что хотите изменить:",
            parse_mode="HTML",
            reply_markup=get_draft_edit_keyboard(lot_id)
        )
        await state.set_state(LotCreation.editing_draft)
        return

    await db.update_lot_field(lot_id, 'city', message.text)
    await message.answer(
        "✅ Город обновлен!\n\n✏️ <b>Редактирование лота</b>\n\n"
        "Выберите что хотите изменить:",
        parse_mode="HTML",
        reply_markup=get_draft_edit_keyboard(lot_id)
    )
    await state.set_state(LotCreation.editing_draft)


@router.message(LotCreation.edit_size, F.text)
async def edit_size(message: Message, state: FSMContext):
    """Edit lot size"""
    data = await state.get_data()
    lot_id = data['lot_id']

    if message.text == "❌ Отмена":
        await message.answer(
            "✏️ <b>Редактирование лота</b>\n\n"
            "Выберите что хотите изменить:",
            parse_mode="HTML",
            reply_markup=get_draft_edit_keyboard(lot_id)
        )
        await state.set_state(LotCreation.editing_draft)
        return

    # Validate size selection
    valid_sizes = ["Маленький", "Средний", "Большой", "Огромный"]
    if message.text not in valid_sizes:
        await message.answer(
            "Пожалуйста, выберите размер из предложенных вариантов.",
            reply_markup=get_size_keyboard()
        )
        return

    await db.update_lot_field(lot_id, 'size', message.text)
    await message.answer(
        "✅ Размер обновлен!\n\n✏️ <b>Редактирование лота</b>\n\n"
        "Выберите что хотите изменить:",
        parse_mode="HTML",
        reply_markup=get_draft_edit_keyboard(lot_id)
    )
    await state.set_state(LotCreation.editing_draft)


@router.message(LotCreation.edit_price, F.text)
async def edit_price(message: Message, state: FSMContext):
    """Edit lot price"""
    data = await state.get_data()
    lot_id = data['lot_id']

    if message.text == "❌ Отмена":
        await message.answer(
            "✏️ <b>Редактирование лота</b>\n\n"
            "Выберите что хотите изменить:",
            parse_mode="HTML",
            reply_markup=get_draft_edit_keyboard(lot_id)
        )
        await state.set_state(LotCreation.editing_draft)
        return

    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError

        await db.update_lot_field(lot_id, 'start_price', price)
        await db.update_lot_field(lot_id, 'current_price', price)
        await message.answer(
            "✅ Цена обновлена!\n\n✏️ <b>Редактирование лота</b>\n\n"
            "Выберите что хотите изменить:",
            parse_mode="HTML",
            reply_markup=get_draft_edit_keyboard(lot_id)
        )
        await state.set_state(LotCreation.editing_draft)

    except ValueError:
        await message.answer("Введите корректное число.")


@router.message(LotCreation.edit_wear, F.text)
async def edit_wear(message: Message, state: FSMContext):
    """Edit lot wear"""
    data = await state.get_data()
    lot_id = data['lot_id']

    if message.text == "❌ Отмена":
        await message.answer(
            "✏️ <b>Редактирование лота</b>\n\n"
            "Выберите что хотите изменить:",
            parse_mode="HTML",
            reply_markup=get_draft_edit_keyboard(lot_id)
        )
        await state.set_state(LotCreation.editing_draft)
        return

    # Validate wear selection
    valid_wear_options = ["Сегодняшняя", "1 дневная", "2 дневная", "Более 3 дней"]
    if message.text not in valid_wear_options:
        await message.answer(
            "Пожалуйста, выберите свежесть из предложенных вариантов.",
            reply_markup=get_wear_keyboard()
        )
        return

    await db.update_lot_field(lot_id, 'wear', message.text)
    await message.answer(
        "✅ Свежесть обновлена!\n\n✏️ <b>Редактирование лота</b>\n\n"
        "Выберите что хотите изменить:",
        parse_mode="HTML",
        reply_markup=get_draft_edit_keyboard(lot_id)
    )
    await state.set_state(LotCreation.editing_draft)


@router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_lot(callback: CallbackQuery, state: FSMContext):
    """Confirm lot deletion"""
    lot_id = int(callback.data.split(":")[1])

    await db.delete_lot(lot_id)
    await callback.message.edit_text("Лот удален.")
    await callback.answer()

    # Send message with main menu
    await callback.message.answer(
        "Возвращаемся в главное меню.",
        reply_markup=await get_user_menu(callback.from_user.id)
    )
    await state.clear()


@router.callback_query(F.data.startswith("cancel_delete:"))
async def cancel_delete_lot(callback: CallbackQuery, state: FSMContext):
    """Cancel lot deletion"""
    lot_id = int(callback.data.split(":")[1])

    await callback.answer("Удаление отменено")

    # Get current message and get lot_id from state
    data = await state.get_data()

    # Delete the confirmation message
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Show draft again
    await show_lot_draft(callback.message, lot_id, state)
    await state.set_state(LotCreation.editing_draft)
