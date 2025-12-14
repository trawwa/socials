from datetime import datetime, timezone

from aiohttp import web
from aiohttp_session import get_session


class Index(web.View):

    async def get(self) -> web.Response:
        config = self.app["config"]
        return web.Response(text=f"Welcome to the index page!\nCONFIG_TYPE: {config}\nProject Name: {config.APP_NAME}")


class Login(web.View):

    async def get(self) -> web.Response | None:
        session = await get_session(self)
        session["last_visit"] = str(datetime.now(timezone.utc))
        last_visit = session["last_visit"]
        text = f"Last visited: {last_visit}"
        return web.Response(text=f"Login Page\n {text}")

    async def post(self) -> web.Response:
        return web.Response(text="Login page")


class Signup(web.View):

    async def get(self) -> web.Response:
        return web.Response(text="Signup page")
