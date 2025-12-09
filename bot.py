import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import db
from scheduler import start_scheduler, recover_active_auctions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize bot and dispatcher
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Bot username and ID will be set on startup
bot_username = None
bot_id = None


async def on_startup():
    """Actions on bot startup"""
    global bot_username, bot_id

    # Get bot username and ID
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    bot_id = bot_info.id
    logging.info(f"Bot username: @{bot_username}, ID: {bot_id}")

    # Validate configuration
    logging.info("Validating configuration...")

    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_bot_token_here":
        raise ValueError("❌ BOT_TOKEN not configured in .env file!")

    if not config.CHANNEL_ID or config.CHANNEL_ID == "@your_channel_name":
        raise ValueError("❌ CHANNEL_ID not configured in .env file!")

    if not config.ADMIN_PASSWORD or config.ADMIN_PASSWORD == "admin123":
        logging.warning("⚠️ ADMIN_PASSWORD not configured - using default password!")

    # Test channel access
    try:
        channel_info = await bot.get_chat(config.CHANNEL_ID)
        logging.info(f"✅ Channel '{channel_info.title}' ({config.CHANNEL_ID}) is accessible")
    except Exception as e:
        raise ValueError(f"❌ Cannot access channel {config.CHANNEL_ID}: {e}\n"
                        f"Make sure the bot is added as admin to the channel!")

    logging.info("✅ Configuration validated")

    # Initialize database
    await db.init_db()
    logging.info("Database initialized")

    # Start scheduler
    start_scheduler()
    logging.info("Scheduler started")

    # Recover active auctions
    await recover_active_auctions()
    logging.info("Active auctions recovered")

    logging.info("🚀 Bot started successfully")


async def on_shutdown():
    """Actions on bot shutdown"""
    await bot.session.close()
    logging.info("Bot stopped")


async def main():
    """Main function"""
    # Register handlers
    from handlers import registration, menu, lot_creation, admin, auction

    # Important: Register state-based routers first to handle FSM states
    dp.include_router(auction.router)
    dp.include_router(lot_creation.router)
    dp.include_router(registration.router)

    # Then register general routers
    dp.include_router(admin.router)
    dp.include_router(menu.router)

    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
