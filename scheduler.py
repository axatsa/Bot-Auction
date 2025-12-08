from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from database import db
import config

scheduler = AsyncIOScheduler()


async def schedule_auction_completion(lot_id: int, end_time: datetime):
    """Schedule auction completion"""
    scheduler.add_job(
        complete_auction,
        DateTrigger(run_date=end_time),
        args=[lot_id],
        id=f"auction_{lot_id}_complete"
    )

    # Schedule updates
    intervals = [120, 90, 60, 30, 10, 5]  # minutes before end

    for minutes in intervals:
        update_time = end_time - timedelta(minutes=minutes)
        if update_time > datetime.now():
            scheduler.add_job(
                update_auction_status,
                DateTrigger(run_date=update_time),
                args=[lot_id],
                id=f"auction_{lot_id}_update_{minutes}"
            )


async def update_auction_status(lot_id: int):
    """Update auction status in channel"""
    from bot import bot
    from utils import format_lot_message, format_auction_status, get_photos_list
    from keyboards import get_participate_keyboard

    lot = await db.get_lot(lot_id)

    if not lot or not lot.get('channel_message_id'):
        return

    try:
        updated_text = format_lot_message(lot) + format_auction_status(lot)

        photos = get_photos_list(lot['photos'])

        if len(photos) == 1:
            await bot.edit_message_caption(
                chat_id=config.CHANNEL_ID,
                message_id=lot['channel_message_id'],
                caption=updated_text,
                parse_mode="HTML",
                reply_markup=get_participate_keyboard(lot_id)
            )
        else:
            # For media groups, we can't edit, so skip
            pass

    except Exception as e:
        print(f"Failed to update auction {lot_id}: {e}")


async def complete_auction(lot_id: int):
    """Complete auction and determine winner"""
    from bot import bot

    lot = await db.get_lot(lot_id)

    if not lot:
        return

    # Get all bids
    bids = await db.get_lot_bids(lot_id)

    # Update status
    if bids:
        await db.update_lot_status(lot_id, 'finished')

        # Winner is the one with highest bid (already leader)
        winner_id = lot['leader_id']
        winning_bid = lot['current_price']

        # Get winner and owner info
        winner = await db.get_user(winner_id)
        owner = await db.get_user(lot['owner_id'])

        # Format username safely
        owner_username = f"@{owner['username']}" if owner.get('username') else "нет username"

        # Notify winner
        try:
            await bot.send_message(
                chat_id=winner_id,
                text=f"🎉 <b>Вы выиграли аукцион!</b>\n\n"
                     f"Лот: {lot['description']}\n"
                     f"Ваша ставка: {winning_bid} сум\n\n"
                     f"Контакт продавца:\n"
                     f"Имя: {owner['name']}\n"
                     f"Username: {owner_username}\n"
                     f"Телефон: {owner['phone']}",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Failed to notify winner: {e}")

        # Format winner username safely
        winner_username = f"@{winner['username']}" if winner.get('username') else "нет username"

        # Notify owner
        try:
            await bot.send_message(
                chat_id=lot['owner_id'],
                text=f"✅ <b>Ваш аукцион завершён!</b>\n\n"
                     f"Лот: {lot['description']}\n"
                     f"Финальная цена: {winning_bid} сум\n\n"
                     f"Победитель:\n"
                     f"Имя: {winner['name']}\n"
                     f"Username: {winner_username}\n"
                     f"Телефон: {winner['phone']}\n\n"
                     f"Свяжитесь с покупателем.",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Failed to notify owner: {e}")

        # Notify admins
        admin_ids = await db.get_all_admin_ids()
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"ℹ️ <b>Аукцион {lot_id} завершён</b>\n\n"
                         f"Победитель: {winner['name']} ({winner_username})\n"
                         f"Цена: {winning_bid} сум",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Failed to notify admin: {e}")

        # Notify losers
        participants = await db.get_lot_participants(lot_id)
        for participant_id in participants:
            if participant_id != winner_id:
                try:
                    await bot.send_message(
                        chat_id=participant_id,
                        text=f"Аукцион завершён.\n\n"
                             f"Лот: {lot['description']}\n"
                             f"Ваша ставка была перебита.\n"
                             f"Финальная цена: {winning_bid} сум"
                    )
                except Exception:
                    pass

    else:
        # No bids
        await db.update_lot_status(lot_id, 'no_bids')

        # Notify owner
        try:
            await bot.send_message(
                chat_id=lot['owner_id'],
                text=f"Аукцион завершён.\n\n"
                     f"Лот: {lot['description']}\n"
                     f"К сожалению, ставок не было."
            )
        except Exception:
            pass

        # Notify admins
        admin_ids = await db.get_all_admin_ids()
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"ℹ️ Лот {lot_id} завершён без ставок."
                )
            except Exception:
                pass

    # Delete channel message
    if lot.get('channel_message_id'):
        try:
            await bot.delete_message(
                chat_id=config.CHANNEL_ID,
                message_id=lot['channel_message_id']
            )
        except Exception as e:
            print(f"Failed to delete channel message: {e}")


def start_scheduler():
    """Start the scheduler"""
    scheduler.start()


async def recover_active_auctions():
    """Recover active auctions on bot restart"""
    active_auctions = await db.get_active_auctions()

    for lot in active_auctions:
        if lot['end_time']:
            end_time = datetime.fromisoformat(lot['end_time'])

            # If auction already ended, complete it
            if end_time <= datetime.now():
                await complete_auction(lot['id'])
            else:
                # Reschedule
                await schedule_auction_completion(lot['id'], end_time)
