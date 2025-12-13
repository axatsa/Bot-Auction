from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from database import db
from keyboards import get_phone_keyboard, get_main_menu, get_admin_menu
from states import Registration
from utils import is_admin

router = Router()


async def handle_deep_link(message: Message, param: str, state: FSMContext):
    """Handle deep link parameter"""
    # Parse parameter: lot_{lot_id} or buy_{lot_id}
    if param.startswith("lot_"):
        lot_id = int(param.replace("lot_", ""))
        # Trigger participate handler
        from aiogram.types import CallbackQuery

        # Create a fake callback to reuse participate handler
        class FakeCallback:
            def __init__(self, msg, data):
                self.message = msg
                self.from_user = msg.from_user
                self.data = data

            async def answer(self, text=None, show_alert=False):
                pass

        fake_callback = FakeCallback(message, f"participate:{lot_id}")

        # Import and call participate handler
        from handlers.auction import handle_participate
        await handle_participate(fake_callback, state)

    elif param.startswith("buy_"):
        lot_id = int(param.replace("buy_", ""))
        # Trigger buy handler
        from aiogram.types import CallbackQuery

        class FakeCallback:
            def __init__(self, msg, data):
                self.message = msg
                self.from_user = msg.from_user
                self.data = data

            async def answer(self, text=None, show_alert=False):
                pass

        fake_callback = FakeCallback(message, f"buy:{lot_id}")

        # Import and call buy handler
        from handlers.auction import handle_buy
        await handle_buy(fake_callback, state)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    # Extract deep link parameter if present
    args = message.text.split(maxsplit=1)
    deep_link_param = args[1] if len(args) > 1 else None

    # Check if user is already registered
    is_registered = await db.is_user_registered(message.from_user.id)

    if is_registered:
        # Check if user is admin
        user_is_admin = await is_admin(message.from_user.id)
        menu = get_admin_menu() if user_is_admin else get_main_menu(is_admin=user_is_admin)

        await message.answer(
            "Добро пожаловать! Выберите действие:",
            reply_markup=menu
        )

        # Handle deep link if present
        if deep_link_param:
            await handle_deep_link(message, deep_link_param, state)
    else:
        # Save deep link parameter to state for later use after registration
        if deep_link_param:
            await state.update_data(deep_link=deep_link_param)

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
        menu = get_admin_menu() if user_is_admin else get_main_menu(is_admin=user_is_admin)

        await message.answer(
            f"✅ <b>Регистрация завершена!</b>\n\n"
            f"Ваш ID: {message.from_user.id}\n"
            f"Имя: {message.from_user.full_name}\n"
            f"Телефон: {contact.phone_number}\n\n"
            f"Теперь вы можете пользоваться ботом.",
            parse_mode="HTML",
            reply_markup=menu
        )

        # Check if there's a deep link to process
        data = await state.get_data()
        deep_link = data.get('deep_link')

        await state.clear()

        if deep_link:
            # Handle the deep link after registration
            await handle_deep_link(message, deep_link, state)
    else:
        # Check if user is admin
        user_is_admin = await is_admin(message.from_user.id)
        menu = get_admin_menu() if user_is_admin else get_main_menu(is_admin=user_is_admin)

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
