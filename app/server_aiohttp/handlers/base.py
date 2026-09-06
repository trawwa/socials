from datetime import datetime, timezone

import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session

from models.user import User


class Index(web.View):

    @aiohttp_jinja2.template("index.html")
    async def get(self):
        config = self.app["config"]
        return dict(config=config)


class Login(web.View):

    @aiohttp_jinja2.template("login.html")
    async def get(self):
        session = await get_session(self)
        session["last_visit"] = str(datetime.now(timezone.utc))
        last_visit = session["last_visit"]

        db = self.app["db"]
        user = await User.get_user(db=db, uid=1)
        # Используем коллекцию пользователей из Database
        document = await db.users().find_one()

        text = f"Last visited: {last_visit}"
        return dict(text=f"Login Page\n {text}")

    async def post(self):
        data = await self.post()
        login = data["login"]
        password = data["password"]

        session = await get_session(self)
        session["user"] = {"login": login}

        location = self.app.router["index"].url_for()

        return web.HTTPFound(location=location)


class Signup(web.View):

    async def get(self) -> web.Response:
        return web.Response(text="Signup page")
