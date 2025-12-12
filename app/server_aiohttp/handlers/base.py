from datetime import datetime

from aiohttp import web
from aiohttp_session import get_session


class Index(web.View):

    async def get(self) -> web.Response:
        config = self.request.app["config"]
        return web.Response(text=f"Welcome to the index page!\nCONFIG_TYPE: {config}\nProject Name: {config.APP_NAME}")


class Login(web.View):

    async def get(self) -> web.Response | None:
        pass

    async def post(self) -> web.Response:
        return web.Response(text="Login page")


class Signup(web.View):

    async def get(self) -> web.Response:
        return web.Response(text="Signup page")
