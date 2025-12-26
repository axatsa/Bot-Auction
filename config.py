import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'auction_bot.db')

# Prefer minutes for testing if provided; fallback to hours
_action_minutes = os.getenv('ACTION_DURATION_MINUTES') or os.getenv('action_duration_minutes') or os.getenv('AUCTION_DURATION_MINUTES')
AUCTION_DURATION_MINUTES = int(_action_minutes) if _action_minutes else None
AUCTION_DURATION_HOURS = int(os.getenv('AUCTION_DURATION_HOURS', 2))

# Effective duration (in minutes)
EFFECTIVE_AUCTION_DURATION_MINUTES = AUCTION_DURATION_MINUTES if AUCTION_DURATION_MINUTES is not None else AUCTION_DURATION_HOURS * 60

# Payment settings
PAYMENT_AMOUNT = 500  # тенге
PAYMENT_CARD_NUMBER = os.getenv('PAYMENT_CARD_NUMBER')
PAYMENT_PHONE_NUMBER = os.getenv('PAYMENT_PHONE_NUMBER')

# Admin contact
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'Re_Bloom_Admin')