import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiohttp_jinja2
import asyncpg
import jinja2
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.server_aiohttp.routes.base import setup_routes
from models.user import UserModel, hash_password, verify_password


class PasswordHashTests(unittest.TestCase):
    def test_hash_uses_unique_salts_and_verifies_password(self):
        first = hash_password("correct horse battery staple")
        second = hash_password("correct horse battery staple")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("correct horse battery staple", first))
        self.assertFalse(verify_password("wrong password", first))

    def test_empty_password_is_rejected(self):
        with self.assertRaises(ValueError):
            hash_password("")


class Acquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class Pool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return Acquire(self.connection)


class UserModelTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_user_inserts_normalized_email_and_hash_only(self):
        connection = AsyncMock()
        connection.fetchrow.return_value = {"id": 42, "email": "person@example.test"}
        result = await UserModel.create_user(
            Pool(connection), " Person@Example.Test ", " Ada ", " Lovelace ", "secret"
        )
        self.assertEqual(result["id"], 42)
        args = connection.fetchrow.await_args.args
        self.assertEqual(args[1:4], ("person@example.test", "Ada", "Lovelace"))
        self.assertNotEqual(args[4], "secret")
        self.assertTrue(verify_password("secret", args[4]))

    async def test_duplicate_email_error_is_propagated(self):
        connection = AsyncMock()
        connection.fetchrow.side_effect = asyncpg.UniqueViolationError("duplicate")
        with self.assertRaises(asyncpg.UniqueViolationError):
            await UserModel.create_user(
                Pool(connection), "person@example.test", "", "", "secret"
            )


class SignupViewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = object()
        self.db = type("DB", (), {"_get_pool": lambda _self: self.pool})()
        self.app = web.Application()
        self.app["db"] = self.db
        aiohttp_jinja2.setup(
            self.app,
            loader=jinja2.FileSystemLoader(str(Path(__file__).resolve().parent.parent / "templates")),
        )
        setup_routes(self.app)
        self.client = TestClient(TestServer(self.app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_signup_redirects_to_login_after_success(self):
        with patch(
            "app.server_aiohttp.handlers.base.UserModel.create_user",
            new=AsyncMock(return_value={"id": 1}),
        ):
            response = await self.client.post(
                "/signup",
                data={"email": "person@example.test", "first_name": "Ada",
                      "last_name": "Lovelace", "password": "secret"},
                allow_redirects=False,
            )
        self.assertEqual(response.status, 302)
        self.assertEqual(response.headers["Location"], "/login")

    async def test_signup_shows_conflict_for_duplicate_email(self):
        with patch(
            "app.server_aiohttp.handlers.base.UserModel.create_user",
            new=AsyncMock(side_effect=asyncpg.UniqueViolationError("duplicate")),
        ):
            response = await self.client.post(
                "/signup",
                data={"email": "person@example.test", "password": "secret"},
            )
        self.assertEqual(response.status, 409)
        self.assertIn("Пользователь с таким email уже зарегистрирован.", await response.text())

    async def test_signup_form_is_available(self):
        response = await self.client.get("/signup")
        self.assertEqual(response.status, 200)
        self.assertIn("Зарегистрироваться", await response.text())


if __name__ == "__main__":
    unittest.main()
