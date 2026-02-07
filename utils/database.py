import asyncpg
import asyncio
from typing import Optional

class Database:
    def __init__(self, host: str, database: str, user: str, password: str, port: int = 5432):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Создание пула соединений"""
        self.pool = await asyncpg.create_pool(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password,
            port=self.port,
            min_size=5,
            max_size=10,
            command_timeout=60
        )
        print("✅ Подключение к базе данных установлено")

    async def disconnect(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()
            print("🔌 Подключение к базе данных закрыто")

    async def execute(self, query: str, *args):
        """Выполнение запроса без возврата данных (INSERT, UPDATE, DELETE)"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """Получение списка строк"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """Получение одной строки"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Получение одного значения"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def fetch_all(self, query: str, *args) -> list[dict[str, any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetch_one(self, query: str, *args) -> dict[str, any] | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    def users(self):
        return UserCollection(self)


class UserCollection:
    """Аналог коллекции в MongoDB"""

    def __init__(self, db: Database):
        self.db = db

    async def find(self, **filters) -> list[dict[str, any]]:
        where_clauses = [f"{k} = ${i+1}" for i, k in enumerate(filters.keys())]
        query = f"SELECT * FROM users WHERE {' AND '.join(where_clauses)}"
        return await self.db.fetch_all(query, *filters.values())

    async def insert_one(self, **data) -> int:
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f"${i+1}" for i in range(len(data)))
        query = f"INSERT INTO users ({columns}) VALUES ({placeholders}) RETURNING id"
        result = await self.db.fetch_one(query, *data.values())
        return result["id"]

    async def find_one(self, **filters) -> dict[str, any] | None:
        """Найти одну запись по фильтрам (аналог MongoDB find_one)"""
        if not filters:
            query = "SELECT * FROM users LIMIT 1"
            return await self.db.fetch_one(query)

        where_clauses = [f"{k} = ${i+1}" for i, k in enumerate(filters.keys())]
        query = f"SELECT * FROM users WHERE {' AND '.join(where_clauses)} LIMIT 1"
        return await self.db.fetch_one(query, *filters.values())

