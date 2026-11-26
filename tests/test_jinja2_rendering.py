import unittest
from pathlib import Path

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
        setup(app, create_session_storage("jinja2-rendering-test-secret", environment="test"))
        aiohttp_jinja2.setup(
            app,
            loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        )
        setup_routes(app)

        async def session_user(request: web.Request) -> web.Response:
            session = await get_session(request)
            user = session.get("user", {})
            return web.json_response(user)

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

    async def test_login_accepts_email_and_stores_user_in_session(self):
        response = await self.client.post(
            "/login",
            data={"email": "person@example.com", "password": "secret"},
            allow_redirects=False,
        )
        self.assertEqual(response.status, 302)
        self.assertEqual(response.headers["Location"], "/")

        session_response = await self.client.get("/test-session-user")
        self.assertEqual(session_response.status, 200)
        self.assertEqual(await session_response.json(), {"email": "person@example.com"})


if __name__ == "__main__":
    unittest.main()
