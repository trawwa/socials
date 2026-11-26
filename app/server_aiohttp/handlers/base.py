from datetime import datetime, timezone

import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session


class IndexView(web.View):
    """Render the main page."""

    @aiohttp_jinja2.template("index.html")
    async def get(self) -> dict:
        return {"config": self.request.app.get("config")}


class LoginView(web.View):
    """Render the login page and manage the user's session."""

    @aiohttp_jinja2.template("login.html")
    async def get(self) -> dict:
        session = await get_session(self.request)
        last_visit = datetime.now(timezone.utc).isoformat()
        session["last_visit"] = last_visit
        return {"last_visit": last_visit}

    async def post(self) -> web.HTTPFound:
        data = await self.request.post()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            raise web.HTTPBadRequest(text="Email and password are required")

        session = await get_session(self.request)
        session["user"] = {"email": str(email)}

        return web.HTTPFound(
            location=self.request.app.router["index"].url_for()
        )


class SignupView(web.View):
    """Render the signup page."""

    async def get(self) -> web.Response:
        return web.Response(text="Signup page", content_type="text/plain")
