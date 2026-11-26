import unittest
from unittest.mock import AsyncMock, patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from main import init_db
from utils.database import Database


class DatabasePoolTests(unittest.IsolatedAsyncioTestCase):
    async def test_pool_uses_configured_connection_and_pool_settings(self):
        fake_pool = AsyncMock()
        with patch("utils.database.asyncpg.create_pool", new=AsyncMock(return_value=fake_pool)) as create_pool:
            db = Database(
                host="db.example",
                port=5544,
                database="social_network",
                user="socials",
                password="secret",
                min_size=2,
                max_size=7,
            )
            pool = await db.connect()

        self.assertIs(pool, fake_pool)
        create_pool.assert_awaited_once_with(
            host="db.example",
            port=5544,
            database="social_network",
            user="socials",
            password="secret",
            min_size=2,
            max_size=7,
            command_timeout=60,
        )

        await db.disconnect()
        fake_pool.close.assert_awaited_once()
        self.assertIsNone(db.pool)

    async def test_invalid_pool_size_is_rejected(self):
        with self.assertRaises(ValueError):
            Database("localhost", "social_network", "postgres", "postgres", min_size=0)
        with self.assertRaises(ValueError):
            Database("localhost", "social_network", "postgres", "postgres", min_size=5, max_size=4)

    async def test_pool_must_be_initialized_before_queries(self):
        db = Database("localhost", "social_network", "postgres", "postgres")
        with self.assertRaisesRegex(RuntimeError, "not initialized"):
            await db.fetchval("SELECT 1")

    async def test_app_lifecycle_exposes_db_and_closes_pool(self):
        fake_db = AsyncMock()
        app = web.Application()
        app.cleanup_ctx.append(init_db)

        async def db_health(request):
            return web.Response(text="available" if request.app.get("db") is fake_db else "missing")

        app.router.add_get("/db-health", db_health)

        settings_patch = (
            patch("main.settings.DB_HOST", "postgres"),
            patch("main.settings.DB_PORT", 5432),
            patch("main.settings.DB_NAME", "social_network"),
            patch("main.settings.DB_USER", "postgres"),
            patch("main.settings.DB_PASSWORD", "postgres"),
            patch("main.settings.DB_POOL_MIN", 1),
            patch("main.settings.DB_POOL_MAX", 4),
        )
        with patch("main.Database", return_value=fake_db) as database_factory:
            for item in settings_patch:
                item.start()
            client = TestClient(TestServer(app))
            try:
                await client.start_server()
                response = await client.get("/db-health")
                self.assertEqual(response.status, 200)
                self.assertEqual(await response.text(), "available")
                database_factory.assert_called_once_with(
                    host="postgres",
                    port=5432,
                    database="social_network",
                    user="postgres",
                    password="postgres",
                    min_size=1,
                    max_size=4,
                )
                fake_db.connect.assert_awaited_once()
            finally:
                await client.close()
                for item in reversed(settings_patch):
                    item.stop()

        fake_db.disconnect.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
