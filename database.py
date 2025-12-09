# import aiosqlite
# from datetime import datetime
# from typing import Optional, List, Dict, Any
# import config
#
#
# class Database:
#     def __init__(self, db_path: str = config.DATABASE_PATH):
#         self.db_path = db_path
#
#     async def init_db(self):
#         """Initialize database tables"""
#         async with aiosqlite.connect(self.db_path) as db:
#             # Users table
#             await db.execute('''
#                 CREATE TABLE IF NOT EXISTS users (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     telegram_id INTEGER UNIQUE NOT NULL,
#                     username TEXT,
#                     name TEXT,
#                     phone TEXT,
#                     reg_date TEXT NOT NULL,
#                     is_blocked INTEGER DEFAULT 0
#                 )
#             ''')
#
#             # Admins table
#             await db.execute('''
#                 CREATE TABLE IF NOT EXISTS admins (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     telegram_id INTEGER UNIQUE NOT NULL,
#                     username TEXT,
#                     auth_date TEXT NOT NULL
#                 )
#             ''')
#
#             # Lots table
#             await db.execute('''
#                 CREATE TABLE IF NOT EXISTS lots (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     owner_id INTEGER NOT NULL,
#                     lot_type TEXT DEFAULT 'auction',
#                     photos TEXT NOT NULL,
#                     description TEXT NOT NULL,
#                     city TEXT NOT NULL,
#                     size TEXT NOT NULL,
#                     wear TEXT NOT NULL,
#                     start_price REAL NOT NULL,
#                     current_price REAL,
#                     leader_id INTEGER,
#                     auction_started INTEGER DEFAULT 0,
#                     start_time TEXT,
#                     end_time TEXT,
#                     status TEXT DEFAULT 'pending',
#                     channel_message_id INTEGER,
#                     created_at TEXT NOT NULL,
#                     FOREIGN KEY (owner_id) REFERENCES users(telegram_id),
#                     FOREIGN KEY (leader_id) REFERENCES users(telegram_id)
#                 )
#             ''')
#
#             # Bids table
#             await db.execute('''
#                 CREATE TABLE IF NOT EXISTS bids (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     lot_id INTEGER NOT NULL,
#                     user_id INTEGER NOT NULL,
#                     amount REAL NOT NULL,
#                     timestamp TEXT NOT NULL,
#                     FOREIGN KEY (lot_id) REFERENCES lots(id),
#                     FOREIGN KEY (user_id) REFERENCES users(telegram_id)
#                 )
#             ''')
#
#             await db.commit()
#
#     # User methods
#     async def add_user(self, telegram_id: int, username: str, name: str, phone: str) -> bool:
#         """Add new user to database"""
#         try:
#             async with aiosqlite.connect(self.db_path) as db:
#                 await db.execute(
#                     'INSERT INTO users (telegram_id, username, name, phone, reg_date) VALUES (?, ?, ?, ?, ?)',
#                     (telegram_id, username, name, phone, datetime.now().isoformat())
#                 )
#                 await db.commit()
#                 return True
#         except aiosqlite.IntegrityError:
#             return False
#
#     async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
#         """Get user by telegram_id"""
#         async with aiosqlite.connect(self.db_path) as db:
#             db.row_factory = aiosqlite.Row
#             async with db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)) as cursor:
#                 row = await cursor.fetchone()
#                 return dict(row) if row else None
#
#     async def is_user_registered(self, telegram_id: int) -> bool:
#         """Check if user is registered"""
#         user = await self.get_user(telegram_id)
#         return user is not None
#
#     # Lot methods
#     async def create_lot(self, owner_id: int, photos: str, description: str,
#                         city: str, size: str, wear: str, start_price: float,
#                         lot_type: str = 'auction') -> int:
#         """Create new lot"""
#         async with aiosqlite.connect(self.db_path) as db:
#             cursor = await db.execute(
#                 '''INSERT INTO lots (owner_id, lot_type, photos, description, city, size, wear,
#                    start_price, current_price, created_at, status)
#                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
#                 (owner_id, lot_type, photos, description, city, size, wear, start_price,
#                  start_price, datetime.now().isoformat(), 'pending')
#             )
#             await db.commit()
#             return cursor.lastrowid
#
#     async def get_lot(self, lot_id: int) -> Optional[Dict[str, Any]]:
#         """Get lot by id"""
#         async with aiosqlite.connect(self.db_path) as db:
#             db.row_factory = aiosqlite.Row
#             async with db.execute('SELECT * FROM lots WHERE id = ?', (lot_id,)) as cursor:
#                 row = await cursor.fetchone()
#                 return dict(row) if row else None
#
#     async def update_lot_status(self, lot_id: int, status: str) -> bool:
#         """Update lot status"""
#         async with aiosqlite.connect(self.db_path) as db:
#             await db.execute('UPDATE lots SET status = ? WHERE id = ?', (status, lot_id))
#             await db.commit()
#             return True
#
#     async def update_lot_field(self, lot_id: int, field: str, value: Any) -> bool:
#         """Update specific lot field"""
#         async with aiosqlite.connect(self.db_path) as db:
#             await db.execute(f'UPDATE lots SET {field} = ? WHERE id = ?', (value, lot_id))
#             await db.commit()
#             return True
#
#     async def get_pending_lots(self) -> List[Dict[str, Any]]:
#         """Get all pending lots for moderation"""
#         async with aiosqlite.connect(self.db_path) as db:
#             db.row_factory = aiosqlite.Row
#             async with db.execute('SELECT * FROM lots WHERE status = ?', ('pending',)) as cursor:
#                 rows = await cursor.fetchall()
#                 return [dict(row) for row in rows]
#
#     async def start_auction(self, lot_id: int, start_time: str, end_time: str) -> bool:
#         """Mark auction as started"""
#         async with aiosqlite.connect(self.db_path) as db:
#             await db.execute(
#                 '''UPDATE lots SET auction_started = 1, start_time = ?,
#                    end_time = ?, status = 'active' WHERE id = ?''',
#                 (start_time, end_time, lot_id)
#             )
#             await db.commit()
#             return True
#
#     async def get_active_auctions(self) -> List[Dict[str, Any]]:
#         """Get all active auctions"""
#         async with aiosqlite.connect(self.db_path) as db:
#             db.row_factory = aiosqlite.Row
#             async with db.execute(
#                 'SELECT * FROM lots WHERE status = ? AND auction_started = 1',
#                 ('active',)
#             ) as cursor:
#                 rows = await cursor.fetchall()
#                 return [dict(row) for row in rows]
#
#     async def get_all_active_lots(self) -> List[Dict[str, Any]]:
#         """Get all active and approved lots (for viewing in bot)"""
#         async with aiosqlite.connect(self.db_path) as db:
#             db.row_factory = aiosqlite.Row
#             async with db.execute(
#                 "SELECT * FROM lots WHERE status IN ('approved', 'active') ORDER BY created_at DESC"
#             ) as cursor:
#                 rows = await cursor.fetchall()
#                 return [dict(row) for row in rows]
#
#     # Bid methods
#     async def add_bid(self, lot_id: int, user_id: int, amount: float) -> bool:
#         """Add new bid"""
#         async with aiosqlite.connect(self.db_path) as db:
#             await db.execute(
#                 'INSERT INTO bids (lot_id, user_id, amount, timestamp) VALUES (?, ?, ?, ?)',
#                 (lot_id, user_id, amount, datetime.now().isoformat())
#             )
#             # Update lot current price and leader
#             await db.execute(
#                 'UPDATE lots SET current_price = ?, leader_id = ? WHERE id = ?',
#                 (amount, user_id, lot_id)
#             )
#             await db.commit()
#             return True
#
#     async def get_lot_bids(self, lot_id: int) -> List[Dict[str, Any]]:
#         """Get all bids for a lot"""
#         async with aiosqlite.connect(self.db_path) as db:
#             db.row_factory = aiosqlite.Row
#             async with db.execute(
#                 'SELECT * FROM bids WHERE lot_id = ? ORDER BY amount DESC',
#                 (lot_id,)
#             ) as cursor:
#                 rows = await cursor.fetchall()
#                 return [dict(row) for row in rows]
#
#     async def get_lot_participants(self, lot_id: int) -> List[int]:
#         """Get all unique participants of an auction"""
#         async with aiosqlite.connect(self.db_path) as db:
#             async with db.execute(
#                 'SELECT DISTINCT user_id FROM bids WHERE lot_id = ?',
#                 (lot_id,)
#             ) as cursor:
#                 rows = await cursor.fetchall()
#                 return [row[0] for row in rows]
#
#     async def delete_lot(self, lot_id: int) -> bool:
#         """Delete lot and its bids"""
#         async with aiosqlite.connect(self.db_path) as db:
#             await db.execute('DELETE FROM bids WHERE lot_id = ?', (lot_id,))
#             await db.execute('DELETE FROM lots WHERE id = ?', (lot_id,))
#             await db.commit()
#             return True
#
#     # Admin methods
#     async def add_admin(self, telegram_id: int, username: str = None) -> bool:
#         """Add user to admins"""
#         try:
#             async with aiosqlite.connect(self.db_path) as db:
#                 await db.execute(
#                     'INSERT INTO admins (telegram_id, username, auth_date) VALUES (?, ?, ?)',
#                     (telegram_id, username, datetime.now().isoformat())
#                 )
#                 await db.commit()
#                 return True
#         except aiosqlite.IntegrityError:
#             return False
#
#     async def is_admin(self, telegram_id: int) -> bool:
#         """Check if user is admin"""
#         async with aiosqlite.connect(self.db_path) as db:
#             async with db.execute(
#                 'SELECT * FROM admins WHERE telegram_id = ?',
#                 (telegram_id,)
#             ) as cursor:
#                 row = await cursor.fetchone()
#                 return row is not None
#
#     async def remove_admin(self, telegram_id: int) -> bool:
#         """Remove user from admins"""
#         async with aiosqlite.connect(self.db_path) as db:
#             await db.execute('DELETE FROM admins WHERE telegram_id = ?', (telegram_id,))
#             await db.commit()
#             return True
#
#     async def get_all_admin_ids(self) -> List[int]:
#         """Get all admin telegram IDs"""
#         async with aiosqlite.connect(self.db_path) as db:
#             async with db.execute('SELECT telegram_id FROM admins') as cursor:
#                 rows = await cursor.fetchall()
#                 return [row[0] for row in rows]
#
#     # History methods
#     async def get_lots_history(self, status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
#         """Get lots history with optional status filter"""
#         async with aiosqlite.connect(self.db_path) as db:
#             db.row_factory = aiosqlite.Row
#             if status:
#                 query = 'SELECT * FROM lots WHERE status = ? ORDER BY created_at DESC LIMIT ?'
#                 params = (status, limit)
#             else:
#                 query = 'SELECT * FROM lots ORDER BY created_at DESC LIMIT ?'
#                 params = (limit,)
#
#             async with db.execute(query, params) as cursor:
#                 rows = await cursor.fetchall()
#                 return [dict(row) for row in rows]
#
#     async def get_stats(self) -> Dict[str, Any]:
#         """Get general statistics"""
#         async with aiosqlite.connect(self.db_path) as db:
#             stats = {}
#
#             # Total users
#             async with db.execute('SELECT COUNT(*) FROM users') as cursor:
#                 stats['total_users'] = (await cursor.fetchone())[0]
#
#             # Total lots
#             async with db.execute('SELECT COUNT(*) FROM lots') as cursor:
#                 stats['total_lots'] = (await cursor.fetchone())[0]
#
#             # Lots by status
#             async with db.execute('SELECT status, COUNT(*) FROM lots GROUP BY status') as cursor:
#                 rows = await cursor.fetchall()
#                 stats['lots_by_status'] = {row[0]: row[1] for row in rows}
#
#             # Finished with bids
#             async with db.execute('SELECT COUNT(*) FROM lots WHERE status = ?', ('finished',)) as cursor:
#                 stats['finished_auctions'] = (await cursor.fetchone())[0]
#
#             # Total bids
#             async with db.execute('SELECT COUNT(*) FROM bids') as cursor:
#                 stats['total_bids'] = (await cursor.fetchone())[0]
#
#             # Average final price
#             async with db.execute(
#                 'SELECT AVG(current_price) FROM lots WHERE status = ? AND current_price IS NOT NULL',
#                 ('finished',)
#             ) as cursor:
#                 avg_price = (await cursor.fetchone())[0]
#                 stats['avg_final_price'] = avg_price if avg_price else 0
#
#             return stats
#
#
# # Global database instance
# db = Database()


import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
import config


class Database:
    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    name TEXT,
                    phone TEXT,
                    reg_date TEXT NOT NULL,
                    is_blocked INTEGER DEFAULT 0
                )
            ''')

            # Admins table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    auth_date TEXT NOT NULL
                )
            ''')

            # Lots table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS lots (
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

            # Bids table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lot_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (lot_id) REFERENCES lots(id),
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )
            ''')

            # Bid tokens table (for one-time bid sessions)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bid_tokens (
                    token TEXT PRIMARY KEY,
                    lot_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            ''')

            await db.commit()

    # User methods
    async def add_user(self, telegram_id: int, username: str, name: str, phone: str) -> bool:
        """Add new user to database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO users (telegram_id, username, name, phone, reg_date) VALUES (?, ?, ?, ?, ?)',
                    (telegram_id, username, name, phone, datetime.now().isoformat())
                )
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by telegram_id"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def is_user_registered(self, telegram_id: int) -> bool:
        """Check if user is registered"""
        user = await self.get_user(telegram_id)
        return user is not None

    # Lot methods
    async def create_lot(self, owner_id: int, photos: str, description: str,
                        city: str, size: str, wear: str, start_price: float,
                        ) -> int:
        """Create new lot and return its id"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO lots (owner_id, photos, description, city, size, wear, start_price, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (owner_id, photos, description, city, size, wear, start_price, datetime.now().isoformat())
            )
            await db.commit()
            return cursor.lastrowid

    async def get_lot(self, lot_id: int) -> Optional[Dict[str, Any]]:
        """Get lot by id"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM lots WHERE id = ?', (lot_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_lots(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of lots, optionally filtered by status"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                async with db.execute('SELECT * FROM lots WHERE status = ? ORDER BY created_at DESC', (status,)) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute('SELECT * FROM lots ORDER BY created_at DESC') as cursor:
                    rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_lot_bids(self, lot_id: int) -> List[Dict[str, Any]]:
        """Return all bids for a lot ordered by timestamp ascending"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM bids WHERE lot_id = ? ORDER BY timestamp ASC', (lot_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def add_bid(self, lot_id: int, user_id: int, amount: float) -> None:
        """Add bid and update lot's current_price and leader_id"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT INTO bids (lot_id, user_id, amount, timestamp) VALUES (?, ?, ?, ?)',
                (lot_id, user_id, amount, datetime.now().isoformat())
            )
            # Update lot current price and leader
            await db.execute(
                'UPDATE lots SET current_price = ?, leader_id = ? WHERE id = ?',
                (amount, user_id, lot_id)
            )
            await db.commit()

    async def start_auction(self, lot_id: int, start_time: str, end_time: str) -> None:
        """Mark auction as started and set start/end times"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE lots SET auction_started = 1, start_time = ?, end_time = ? WHERE id = ?',
                (start_time, end_time, lot_id)
            )
            await db.commit()

    async def update_lot_field(self, lot_id: int, field: str, value: Any) -> None:
        """Generic single-field updater for lots (safe-ish)"""
        if field not in {'owner_id', 'lot_type', 'photos', 'description', 'city', 'size', 'wear',
                         'start_price', 'current_price', 'leader_id', 'auction_started',
                         'start_time', 'end_time', 'status', 'channel_message_id'}:
            raise ValueError("Unsupported field for update")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f'UPDATE lots SET {field} = ? WHERE id = ?', (value, lot_id))
            await db.commit()

    async def update_lot_status(self, lot_id: int, status: str) -> None:
        """Update lot status"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE lots SET status = ? WHERE id = ?', (status, lot_id))
            await db.commit()

    async def get_active_auctions(self) -> List[Dict[str, Any]]:
        """Return lots that are active auctions"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM lots WHERE lot_type = 'auction' AND status = 'active'") as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # Bid token methods (one-time tokens for reply flow)
    async def create_bid_token(self, token: str, lot_id: int, user_id: int, expires_at: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR REPLACE INTO bid_tokens (token, lot_id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?)',
                (token, lot_id, user_id, datetime.now().isoformat(), expires_at)
            )
            await db.commit()

    async def get_bid_token(self, token: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM bid_tokens WHERE token = ?', (token,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def delete_bid_token(self, token: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM bid_tokens WHERE token = ?', (token,))
            await db.commit()


# Module-level instance expected by other parts of the project
db = Database()

__all__ = ["Database", "db"]