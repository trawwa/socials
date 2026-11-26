import unittest
from datetime import datetime

import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import get_session, setup

from app.server_aiohttp.handlers.base import LoginView
from utils.session import create_session_storage


class SessionStorageIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def make_app(self, secret: str) -> web.Application:
        app = web.Application()
        setup(app, create_session_storage(secret, environment="test"))

        async def write_session(request: web.Request) -> web.Response:
            session = await get_session(request)
            session["marker"] = "survives-restart"
            return web.Response(text="session written")

        async def read_session(request: web.Request) -> web.Response:
            session = await get_session(request)
            return web.Response(text=session.get("marker", "missing"))

        app.router.add_get("/write", write_session)
        app.router.add_get("/read", read_session)
        return app

    async def test_cookie_survives_app_restart_with_same_secret(self):
        first_client = TestClient(TestServer(self.make_app("stable-integration-secret")))
        await first_client.start_server()
        try:
            response = await first_client.get("/write")
            self.assertEqual(response.status, 200)
            cookie = response.cookies.get("AIOHTTP_SESSION")
            self.assertIsNotNone(cookie)
            cookie_header = f"AIOHTTP_SESSION={cookie.value}"
        finally:
            await first_client.close()

        # A new TestServer/TestClient models a process restart. Only the
        # browser cookie and configured secret are carried into the new app.
        restarted_client = TestClient(TestServer(self.make_app("stable-integration-secret")))
        await restarted_client.start_server()
        try:
            response = await restarted_client.get(
                "/read",
                headers={"Cookie": cookie_header},
            )
            self.assertEqual(response.status, 200)
            self.assertEqual(await response.text(), "survives-restart")
        finally:
            await restarted_client.close()

    async def test_cookie_is_not_readable_with_a_different_secret(self):
        first_client = TestClient(TestServer(self.make_app("first-integration-secret")))
        await first_client.start_server()
        try:
            response = await first_client.get("/write")
            cookie = response.cookies.get("AIOHTTP_SESSION")
            self.assertIsNotNone(cookie)
            cookie_header = f"AIOHTTP_SESSION={cookie.value}"
        finally:
            await first_client.close()

        other_client = TestClient(TestServer(self.make_app("different-integration-secret")))
        await other_client.start_server()
        try:
            response = await other_client.get("/read", headers={"Cookie": cookie_header})
            self.assertEqual(response.status, 200)
            self.assertEqual(await response.text(), "missing")
        finally:
            await other_client.close()


    async def test_login_view_persists_last_visit_in_session(self):
        app = web.Application()
        setup(app, create_session_storage("login-view-integration-secret", environment="test"))
        aiohttp_jinja2.setup(
            app,
            loader=jinja2.DictLoader({"login.html": "{{ last_visit }}"}),
        )
        app.router.add_view("/login", LoginView)

        async def read_last_visit(request: web.Request) -> web.Response:
            session = await get_session(request)
            return web.Response(text=str(session.get("last_visit", "")))

        app.router.add_get("/session", read_last_visit)

        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            login_response = await client.get("/login")
            self.assertEqual(login_response.status, 200)
            self.assertTrue(await login_response.text())
            self.assertIn("AIOHTTP_SESSION", login_response.cookies)

            session_response = await client.get("/session")
            self.assertEqual(session_response.status, 200)
            last_visit = await session_response.text()
            self.assertTrue(last_visit)

            parsed_last_visit = datetime.fromisoformat(last_visit)
            self.assertIsNotNone(parsed_last_visit.tzinfo)
            self.assertIsNotNone(parsed_last_visit.utcoffset())
        finally:
            await client.close()



if __name__ == "__main__":
    unittest.main()
