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

    # Schedule channel updates (every 30 min and at key moments)
    update_intervals = [120, 90, 60, 30]  # minutes before end

    for minutes in update_intervals:
        update_time = end_time - timedelta(minutes=minutes)
        if update_time > datetime.now():
            scheduler.add_job(
                update_auction_status,
                DateTrigger(run_date=update_time),
                args=[lot_id],
                id=f"auction_{lot_id}_update_{minutes}"
            )

    # Schedule participant notifications before auction ends
    notification_intervals = [10, 5]  # notify participants 10 and 5 minutes before end

    for minutes in notification_intervals:
        notification_time = end_time - timedelta(minutes=minutes)
        if notification_time > datetime.now():
            scheduler.add_job(
                notify_participants_before_end,
                DateTrigger(run_date=notification_time),
                args=[lot_id, minutes],
                id=f"auction_{lot_id}_notify_{minutes}"
            )


async def notify_participants_before_end(lot_id: int, minutes_left: int):
    """Notify all auction participants that auction is ending soon"""
    from bot import bot

    lot = await db.get_lot(lot_id)
    if not lot:
        return

    # Get all participants
    participants = await db.get_lot_participants(lot_id)

    # Get current price and leader
    current_price = lot.get('current_price') or lot['start_price']
    leader_id = lot.get('leader_id')

    for participant_id in participants:
        try:
            # Different message for leader vs others
            if participant_id == leader_id:
                await bot.send_message(
                    chat_id=participant_id,
                    text=f"⏰ <b>Торги скоро завершатся!</b>\n\n"
                         f"📦 <b>Лот:</b> {lot['description']}\n"
                         f"💰 <b>Ваша ставка:</b> {int(current_price):,} сум\n"
                         f"🥇 <b>Вы лидируете!</b>\n\n"
                         f"⏱ До завершения осталось: <b>{minutes_left} минут</b>",
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=participant_id,
                    text=f"⏰ <b>Торги скоро завершатся!</b>\n\n"
                         f"📦 <b>Лот:</b> {lot['description']}\n"
                         f"💰 <b>Текущая ставка:</b> {int(current_price):,} сум\n"
                         f"💡 У вас ещё есть время перебить ставку!\n\n"
                         f"⏱ До завершения осталось: <b>{minutes_left} минут</b>",
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"Failed to notify participant {participant_id}: {e}")


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
                text=f"🎉 <b>Поздравляем! Вы выиграли аукцион!</b>\n\n"
                     f"📦 <b>Лот:</b> {lot['description']}\n"
                     f"💰 <b>Ваша ставка:</b> {int(winning_bid):,} тенге\n"
                     f"🏙️ <b>Город:</b> {lot['city']}\n\n"
                     f"👤 <b>Контакт продавца:</b>\n"
                     f"Имя: {owner['name']}\n"
                     f"Username: {owner_username}\n"
                     f"Телефон: {owner['phone']}\n\n"
                     f"💬 Свяжитесь с продавцом для получения товара и оплаты",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Failed to notify winner: {e}")

        # Format winner username safely
        winner_username = f"@{winner['username']}" if winner.get('username') else "нет username"

        # Calculate profit percentage
        profit_percent = int(((winning_bid - lot['start_price']) / lot['start_price']) * 100) if lot['start_price'] > 0 else 0

        # Notify owner
        try:
            await bot.send_message(
                chat_id=lot['owner_id'],
                text=f"🎉 <b>Ваш лот продан!</b>\n\n"
                     f"📦 <b>Лот:</b> {lot['description']}\n"
                     f"💰 <b>Финальная цена:</b> {int(winning_bid):,} тенге\n"
                     f"🚀 <b>Рост от стартовой:</b> +{profit_percent}%\n\n"
                     f"👤 <b>Контакт покупателя:</b>\n"
                     f"Имя: {winner['name']}\n"
                     f"Username: {winner_username}\n"
                     f"Телефон: {winner['phone']}\n\n"
                     f"💬 Свяжитесь с покупателем для передачи товара и получения оплаты",
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
                         f"Цена: {winning_bid} тенге",
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
                        text=f"😔 <b>Аукцион завершён</b>\n\n"
                             f"📦 Лот: {lot['description']}\n"
                             f"💔 Ваша ставка была перебита\n"
                             f"💰 Финальная цена: {int(winning_bid):,} тенге\n\n"
                             f"Не расстраивайтесь, следите за новыми лотами в канале!",
                        parse_mode="HTML"
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
                text=f"😔 <b>Аукцион завершён</b>\n\n"
                     f"📦 Лот: {lot['description']}\n"
                     f"К сожалению, ставок не было.\n\n"
                     f"💡 <b>Советы:</b>\n"
                     f"• Снизьте стартовую цену\n"
                     f"• Добавьте больше качественных фото\n"
                     f"• Улучшите описание товара",
                parse_mode="HTML"
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

    # Update channel message to show "SOLD"
    if lot.get('channel_message_id'):
        try:
            from utils import format_sold_message, get_photos_list

            # Determine final price
            final_price = winning_bid if bids else lot['start_price']

            # Format sold message
            sold_text = format_sold_message(lot, final_price)

            # Get photos to determine if it's a single photo or media group
            photos = get_photos_list(lot['photos'])

            # Edit message (remove keyboard to prevent further interaction)
            if len(photos) == 1:
                # Single photo - edit caption
                await bot.edit_message_caption(
                    chat_id=config.CHANNEL_ID,
                    message_id=lot['channel_message_id'],
                    caption=sold_text,
                    parse_mode="HTML",
                    reply_markup=None
                )
            else:
                # Media group - can't edit, so we'll try to delete and ignore errors
                # Note: Media groups can't have their captions edited easily
                try:
                    await bot.delete_message(
                        chat_id=config.CHANNEL_ID,
                        message_id=lot['channel_message_id']
                    )
                except Exception:
                    pass
        except Exception as e:
            print(f"Failed to update channel message: {e}")


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
