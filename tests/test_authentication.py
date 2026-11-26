import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import get_session, setup

from app.server_aiohttp.handlers.base import session_context_processor
from app.server_aiohttp.routes.base import setup_routes
from utils.session import create_session_storage


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"


class AuthenticationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pool = object()
        self.db = type("DB", (), {"_get_pool": lambda _self: self.pool})()
        self.app = web.Application()
        self.app["db"] = self.db
        setup(self.app, create_session_storage("auth-test-secret", environment="test"))
        aiohttp_jinja2.setup(
            self.app,
            loader=jinja2.DictLoader({
                "login.html": "login",
                "index.html": "{{ current_user.email if current_user else 'anonymous' }}|{{ is_anonymous }}",
                "signup.html": "signup",
            }),
            context_processors=[session_context_processor],
        )
        setup_routes(self.app)

        async def session_data(request):
            session = await get_session(request)
            return web.json_response(dict(session))

        self.app.router.add_get("/test-session", session_data)
        self.client = TestClient(TestServer(self.app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_login_rejects_unknown_or_invalid_credentials(self):
        with patch(
            "app.server_aiohttp.handlers.base.UserModel.get_by_email",
            new=AsyncMock(return_value=None),
        ):
            response = await self.client.post(
                "/login", data={"email": "missing@example.test", "password": "wrong"}
            )
        self.assertEqual(response.status, 401)
        self.assertEqual(await (await self.client.get("/test-session")).json(), {})

    async def test_login_stores_user_id_and_context_is_global(self):
        user = {
            "id": 42,
            "email": "person@example.test",
            "password_hash": "stored-hash",
        }
        with patch(
            "app.server_aiohttp.handlers.base.UserModel.get_by_email",
            new=AsyncMock(return_value=user),
        ), patch(
            "app.server_aiohttp.handlers.base.verify_password",
            return_value=True,
        ), patch(
            "app.server_aiohttp.handlers.base.UserModel.get_by_id",
            new=AsyncMock(return_value={"id": 42, "email": "person@example.test"}),
        ):
            response = await self.client.post(
                "/login",
                data={"email": " Person@Example.Test ", "password": "secret"},
                allow_redirects=False,
            )
            self.assertEqual(response.status, 302)
            self.assertEqual(response.headers["Location"], "/")
            session = await (await self.client.get("/test-session")).json()
            self.assertEqual(session["user_id"], 42)

            index = await self.client.get("/")
            self.assertEqual(index.status, 200)
            self.assertEqual(await index.text(), "person@example.test|False")

    async def test_wrong_password_does_not_create_authenticated_session(self):
        user = {"id": 42, "email": "person@example.test", "password_hash": "stored-hash"}
        with patch(
            "app.server_aiohttp.handlers.base.UserModel.get_by_email",
            new=AsyncMock(return_value=user),
        ), patch(
            "app.server_aiohttp.handlers.base.verify_password",
            return_value=False,
        ):
            response = await self.client.post(
                "/login", data={"email": "person@example.test", "password": "wrong"}
            )
        self.assertEqual(response.status, 401)
        self.assertEqual(await (await self.client.get("/test-session")).json(), {})

    async def test_logout_clears_session_and_redirects_to_login(self):
        async def seed_session(request):
            session = await get_session(request)
            session["user_id"] = 42
            session["last_visit"] = "yesterday"
            return web.Response(text="ok")

        self.app.router.add_get("/test-seed", seed_session)
        await self.client.get("/test-seed")
        response = await self.client.get("/logout", allow_redirects=False)
        self.assertEqual(response.status, 302)
        self.assertEqual(response.headers["Location"], "/login")
        self.assertEqual(await (await self.client.get("/test-session")).json(), {})

    async def test_context_processor_marks_anonymous_and_removes_stale_user_id(self):
        async def seed_session(request):
            session = await get_session(request)
            session["user_id"] = 999
            return web.Response(text="ok")

        self.app.router.add_get("/test-stale-session", seed_session)
        with patch(
            "app.server_aiohttp.handlers.base.UserModel.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            await self.client.get("/test-stale-session")
            response = await self.client.get("/")
            self.assertEqual(await response.text(), "anonymous|True")
            self.assertEqual(await (await self.client.get("/test-session")).json(), {})


if __name__ == "__main__":
    unittest.main()
