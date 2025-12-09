"""
Migration script to update lots table structure
"""
import asyncio
import aiosqlite
import config


async def migrate():
    """Migrate lots table to new structure"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Check current table structure
        async with db.execute("PRAGMA table_info(lots)") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            print(f"Current columns: {column_names}")

        # Check if migration is needed
        needs_migration = False

        if 'city' not in column_names:
            print("Need to add 'city' column")
            needs_migration = True

        if 'wear_hours' in column_names:
            print("Need to migrate 'wear_hours' to 'wear'")
            needs_migration = True

        if 'lot_type' not in column_names:
            print("Need to add 'lot_type' column")
            needs_migration = True

        if not needs_migration:
            print("Database is already up to date")
            return

        # Create backup table name
        print("\nStarting migration...")

        # Create new lots table with correct structure
        await db.execute('''
            CREATE TABLE IF NOT EXISTS lots_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                lot_type TEXT DEFAULT 'auction',
                photos TEXT NOT NULL,
                description TEXT NOT NULL,
                city TEXT NOT NULL,
                size TEXT NOT NULL,
                wear TEXT NOT NULL,
                start_price REAL NOT NULL,
                current_price REAL,
                leader_id INTEGER,
                auction_started INTEGER DEFAULT 0,
                start_time TEXT,
                end_time TEXT,
                status TEXT DEFAULT 'pending',
                channel_message_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES users(telegram_id),
                FOREIGN KEY (leader_id) REFERENCES users(telegram_id)
            )
        ''')

        # Copy data from old table to new table
        if 'city' in column_names and 'wear' in column_names:
            # Already has both columns, add lot_type
            if 'lot_type' in column_names:
                # All columns present, direct copy
                await db.execute('''
                    INSERT INTO lots_new
                    SELECT * FROM lots
                ''')
            else:
                # Need to add lot_type, set to 'auction' by default
                await db.execute('''
                    INSERT INTO lots_new
                    (id, owner_id, lot_type, photos, description, city, size, wear,
                     start_price, current_price, leader_id, auction_started,
                     start_time, end_time, status, channel_message_id, created_at)
                    SELECT
                        id, owner_id, 'auction', photos, description, city, size, wear,
                        start_price, current_price, leader_id, auction_started,
                        start_time, end_time, status, channel_message_id, created_at
                    FROM lots
                ''')
        elif 'city' not in column_names and 'wear_hours' in column_names:
            # Need to add city, lot_type and convert wear_hours
            await db.execute('''
                INSERT INTO lots_new
                (id, owner_id, lot_type, photos, description, city, size, wear,
                 start_price, current_price, leader_id, auction_started,
                 start_time, end_time, status, channel_message_id, created_at)
                SELECT
                    id, owner_id, 'auction', photos, description, 'Не указан', size,
                    CASE
                        WHEN wear_hours = 0 THEN 'Сегодняшний'
                        WHEN wear_hours <= 24 THEN '1 дневный'
                        WHEN wear_hours <= 48 THEN '2 дневный'
                        ELSE 'Более 3 дней'
                    END,
                    start_price, current_price, leader_id, auction_started,
                    start_time, end_time, status, channel_message_id, created_at
                FROM lots
            ''')
        else:
            # Unknown structure - just try to copy what we can
            print("Unknown table structure, attempting best-effort migration")
            try:
                await db.execute('''
                    INSERT INTO lots_new
                    SELECT id, owner_id, 'auction', photos, description,
                           'Не указан', size, 'Не указан',
                           start_price, current_price, leader_id, auction_started,
                           start_time, end_time, status, channel_message_id, created_at
                    FROM lots
                ''')
            except Exception as e:
                print(f"Migration failed: {e}")
                await db.execute("DROP TABLE IF EXISTS lots_new")
                return

        # Drop old table and rename new one
        await db.execute("DROP TABLE lots")
        await db.execute("ALTER TABLE lots_new RENAME TO lots")

        await db.commit()
        print("Successfully migrated lots table!")
        print("   - Added 'city' field (if needed)")
        print("   - Added 'lot_type' field (if needed)")
        print("   - Converted 'wear_hours' to 'wear' with text values (if needed)")


if __name__ == '__main__':
    asyncio.run(migrate())
