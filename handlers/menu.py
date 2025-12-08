from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import db
from keyboards import get_main_menu, get_lot_type_keyboard, get_cancel_keyboard
from states import LotCreation

router = Router()


async def check_registration(message: Message) -> bool:
    """Check if user is registered"""
    is_registered = await db.is_user_registered(message.from_user.id)
    if not is_registered:
        await message.answer(
            "Вы не зарегистрированы! Используйте /start для регистрации."
        )
    return is_registered


@router.message(F.text == "Узнать мой ID")
async def show_my_id(message: Message):
    """Show user's Telegram ID"""
    if not await check_registration(message):
        return

    await message.answer(
        f"Ваш Telegram ID: <code>{message.from_user.id}</code>",
        parse_mode="HTML"
    )


@router.message(F.text == "Добавить товар на аукцион")
async def add_auction_item(message: Message, state: FSMContext):
    """Start creating auction lot"""
    if not await check_registration(message):
        return

    await message.answer(
        "Начинаем создание лота для аукциона.\n\n"
        "Пожалуйста, отправьте фото товара.\n"
        "Вы можете отправить одно или несколько фото.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LotCreation.waiting_for_photos)
    await state.update_data(lot_type='auction')


@router.message(F.text == "Выставить букет")
async def sell_bouquet(message: Message):
    """Show lot type selection"""
    if not await check_registration(message):
        return

    await message.answer(
        "Выберите тип продажи:",
        reply_markup=get_lot_type_keyboard()
    )


@router.callback_query(F.data.startswith("lot_type:"))
async def process_lot_type(callback: CallbackQuery, state: FSMContext):
    """Process lot type selection"""
    lot_type = callback.data.split(":")[1]

    await callback.message.delete()

    if lot_type == "auction":
        await callback.message.answer(
            "Начинаем создание лота для аукциона.\n\n"
            "Пожалуйста, отправьте фото товара.\n"
            "Вы можете отправить одно или несколько фото.",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(LotCreation.waiting_for_photos)
        await state.update_data(lot_type='auction')
    else:
        await callback.message.answer(
            "Функция обычной продажи пока в разработке.",
            reply_markup=get_main_menu()
        )

    await callback.answer()


@router.message(F.text == "Отмена")
async def cancel_action(message: Message, state: FSMContext):
    """Cancel current action"""
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            "Нечего отменять.",
            reply_markup=get_main_menu()
        )
        return

    await state.clear()
    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_menu()
    )
