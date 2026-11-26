from datetime import datetime, timezone

import aiohttp_jinja2
import asyncpg
from aiohttp import web
from aiohttp_session import get_session

from models.user import UserModel


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
        return web.HTTPFound(location=self.request.app.router["index"].url_for())


class SignupView(web.View):
    """Register a user and redirect to the login page."""

    @aiohttp_jinja2.template("signup.html")
    async def get(self) -> dict:
        return {"error": None}

    async def post(self) -> web.Response:
        data = await self.request.post()
        email = str(data.get("email", "")).strip()
        first_name = str(data.get("first_name", "")).strip()
        last_name = str(data.get("last_name", "")).strip()
        password = data.get("password", "")

        if not email or "@" not in email or not password:
            return aiohttp_jinja2.render_template(
                "signup.html", self.request,
                {"error": "Укажите корректный email и пароль."}, status=400,
            )

        try:
            await UserModel.create_user(
                self.request.app["db"]._get_pool(),
                email, first_name, last_name, password,
            )
        except asyncpg.UniqueViolationError:
            return aiohttp_jinja2.render_template(
                "signup.html", self.request,
                {"error": "Пользователь с таким email уже зарегистрирован."},
                status=409,
            )
        except ValueError as exc:
            return aiohttp_jinja2.render_template(
                "signup.html", self.request, {"error": str(exc)}, status=400,
            )

        raise web.HTTPFound(location=self.request.app.router["login"].url_for())
