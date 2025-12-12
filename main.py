import logging

from aiohttp import web

from app.server_aiohttp.routes.base import setup_routes
from config.common import BaseConfig


def main():
    app = web.Application()
    app["config"] = BaseConfig
    setup_routes(app)
    logging.basicConfig(level=logging.INFO)
    web.run_app(app)


if __name__ == "__main__":
    main()
