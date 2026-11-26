from pathlib import Path
from typing import Any, Optional

import asyncpg


class Database:
    def __init__(
        self,
        host: str,
        database: str,
        user: str,
        password: str,
        port: int = 5432,
        min_size: int = 5,
        max_size: int = 10,
    ):
        if min_size < 1 or max_size < min_size:
            raise ValueError("Pool size must satisfy 1 <= min_size <= max_size")

        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.min_size = min_size
        self.max_size = max_size
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Создать пул асинхронных соединений."""
        if self.pool is not None:
            return self.pool

        self.pool = await asyncpg.create_pool(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password,
            port=self.port,
            min_size=self.min_size,
            max_size=self.max_size,
            command_timeout=60,
        )
        return self.pool

    async def apply_schema(self):
        """Применить идемпотентную начальную SQL-схему к подключённой БД."""
        schema_path = Path(__file__).resolve().parent.parent / "models" / "schema.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")

        async with self._get_pool().acquire() as conn:
            await conn.execute(schema_sql)

    async def disconnect(self):
        """Закрыть пул соединений."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    def _get_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized")
        return self.pool

    async def execute(self, query: str, *args):
        async with self._get_pool().acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        async with self._get_pool().acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self._get_pool().acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        async with self._get_pool().acquire() as conn:
            return await conn.fetchval(query, *args)

    async def fetch_all(self, query: str, *args) -> list[dict[str, Any]]:
        async with self._get_pool().acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def fetch_one(self, query: str, *args) -> dict[str, Any] | None:
        async with self._get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    def users(self):
        return UserCollection(self)


class UserCollection:
    """Аналог коллекции MongoDB."""

    def __init__(self, db: Database):
        self.db = db

    async def find(self, **filters) -> list[dict[str, Any]]:
        if not filters:
            return await self.db.fetch_all("SELECT * FROM users")
        where_clauses = [
            f"{key} = ${index}" for index, key in enumerate(filters, start=1)
        ]
        query = f"SELECT * FROM users WHERE {' AND '.join(where_clauses)}"
        return await self.db.fetch_all(query, *filters.values())

    async def insert_one(self, **data) -> int:
        if not data:
            raise ValueError("At least one field is required")
        columns = ", ".join(data)
        placeholders = ", ".join(
            f"${index}" for index in range(1, len(data) + 1)
        )
        query = (
            f"INSERT INTO users ({columns}) VALUES ({placeholders}) RETURNING id"
        )
        result = await self.db.fetch_one(query, *data.values())
        return result["id"]

    async def find_one(self, **filters) -> dict[str, Any] | None:
        if not filters:
            return await self.db.fetch_one("SELECT * FROM users LIMIT 1")
        where_clauses = [
            f"{key} = ${index}" for index, key in enumerate(filters, start=1)
        ]
        query = f"SELECT * FROM users WHERE {' AND '.join(where_clauses)} LIMIT 1"
        return await self.db.fetch_one(query, *filters.values())
