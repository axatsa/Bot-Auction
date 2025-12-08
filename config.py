import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'auction_bot.db')
AUCTION_DURATION_HOURS = int(os.getenv('AUCTION_DURATION_HOURS', 2))
