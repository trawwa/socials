import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import get_session, setup

from app.server_aiohttp.routes.base import setup_routes
from utils.session import create_session_storage


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"


class Jinja2RenderingTests(unittest.IsolatedAsyncioTestCase):
    def make_app(self) -> web.Application:
        app = web.Application()
        app["db"] = type("DB", (), {"_get_pool": lambda _self: object()})()
        setup(app, create_session_storage("jinja2-rendering-test-secret", environment="test"))
        aiohttp_jinja2.setup(
            app,
            loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        )
        setup_routes(app)

        async def session_user(request: web.Request) -> web.Response:
            session = await get_session(request)
            return web.json_response({"user_id": session.get("user_id")})

        app.router.add_get("/test-session-user", session_user)
        return app

    async def asyncSetUp(self) -> None:
        self.client = TestClient(TestServer(self.make_app()))
        await self.client.start_server()

    async def asyncTearDown(self) -> None:
        await self.client.close()

    async def test_index_route_renders_html_template(self):
        response = await self.client.get("/")
        self.assertEqual(response.status, 200)
        body = await response.text()
        self.assertIn("<h1>Главная</h1>", body)
        self.assertIn('href="/login"', body)

    async def test_login_route_renders_email_form_and_last_visit(self):
        response = await self.client.get("/login")
        self.assertEqual(response.status, 200)
        body = await response.text()
        self.assertIn('name="email"', body)
        self.assertIn('type="email"', body)
        self.assertIn('name="password"', body)
        self.assertIn('id="last-visit"', body)
        self.assertIn("Последнее посещение:", body)
        self.assertIn("AIOHTTP_SESSION", response.cookies)

    async def test_login_rejects_missing_email_or_password(self):
        response = await self.client.post("/login", data={"email": "", "password": "secret"})
        self.assertEqual(response.status, 400)
        self.assertIn("Email and password are required", await response.text())

    async def test_login_stores_database_user_id_in_session(self):
        user = {"id": 73, "password_hash": "stored-hash"}
        with patch(
            "app.server_aiohttp.handlers.base.UserModel.get_by_email",
            new=AsyncMock(return_value=user),
        ), patch(
            "app.server_aiohttp.handlers.base.verify_password",
            return_value=True,
        ):
            response = await self.client.post(
                "/login",
                data={"email": "person@example.com", "password": "secret"},
                allow_redirects=False,
            )
        self.assertEqual(response.status, 302)
        self.assertEqual(response.headers["Location"], "/")
        session_response = await self.client.get("/test-session-user")
        self.assertEqual(await session_response.json(), {"user_id": 73})


if __name__ == "__main__":
    unittest.main()
