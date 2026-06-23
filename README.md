# Telegram Auction Bot

A Telegram bot for running product auctions — users place bids, a scheduler automatically closes auctions and announces winners.

## Features
- Create and manage auction listings
- Real-time bidding with live updates
- Automatic auction closing via scheduler
- Admin panel for moderation

## Tech Stack
- Python 3.11+
- aiogram 3.x
- SQLite
- APScheduler

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env  # add BOT_TOKEN
python bot.py
```