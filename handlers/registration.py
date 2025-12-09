from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from database import db
from keyboards import get_phone_keyboard, get_main_menu, get_admin_menu
from states import Registration
from utils import is_admin

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    # Check if user is already registered
    is_registered = await db.is_user_registered(message.from_user.id)

    if is_registered:
        # Check if user is admin
        user_is_admin = await is_admin(message.from_user.id)
        menu = get_admin_menu() if user_is_admin else get_main_menu()

        await message.answer(
            "Добро пожаловать! Выберите действие:",
            reply_markup=menu
        )
    else:
        await message.answer(
            "Добро пожаловать в бот аукционов!\n\n"
            "Для начала работы необходимо зарегистрироваться.\n"
            "Пожалуйста, отправьте свой номер телефона.",
            reply_markup=get_phone_keyboard()
        )
        await state.set_state(Registration.waiting_for_phone)


@router.message(Registration.waiting_for_phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    """Process phone number from contact"""
    contact = message.contact

    # Verify that user sent their own contact
    if contact.user_id != message.from_user.id:
        await message.answer(
            "Пожалуйста, отправьте свой собственный номер телефона.",
            reply_markup=get_phone_keyboard()
        )
        return

    # Save user to database
    success = await db.add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        name=message.from_user.full_name,
        phone=contact.phone_number
    )

    if success:
        # Check if user is admin
        user_is_admin = await is_admin(message.from_user.id)
        menu = get_admin_menu() if user_is_admin else get_main_menu()

        await message.answer(
            f"✅ <b>Регистрация завершена!</b>\n\n"
            f"Ваш ID: {message.from_user.id}\n"
            f"Имя: {message.from_user.full_name}\n"
            f"Телефон: {contact.phone_number}\n\n"
            f"Теперь вы можете пользоваться ботом.",
            parse_mode="HTML",
            reply_markup=menu
        )
        await state.clear()
    else:
        # Check if user is admin
        user_is_admin = await is_admin(message.from_user.id)
        menu = get_admin_menu() if user_is_admin else get_main_menu()

        await message.answer(
            "Произошла ошибка при регистрации. Попробуйте еще раз.",
            reply_markup=menu
        )
        await state.clear()


@router.message(Registration.waiting_for_phone)
async def invalid_phone(message: Message):
    """Handle invalid phone submission"""
    await message.answer(
        "Пожалуйста, используйте кнопку 'Отправить номер' для отправки контакта.",
        reply_markup=get_phone_keyboard()
    )
