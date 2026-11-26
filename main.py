import logging

import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp_session import setup

from app.server_aiohttp.handlers.base import session_context_processor
from app.server_aiohttp.routes.base import setup_routes
from config.common import BaseConfig
from config.config import settings
from utils.database import Database
from utils.session import create_session_storage


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def init_db(app: web.Application):
    """Create the PostgreSQL connection pool on startup and close it on cleanup."""
    db = Database(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        min_size=settings.DB_POOL_MIN,
        max_size=settings.DB_POOL_MAX,
    )
    await db.connect()
    app["db"] = db
    logger.info("Подключение к PostgreSQL установлено")
    try:
        await db.apply_schema()
        logger.info("Схема PostgreSQL применена")
        yield
    finally:
        await db.disconnect()
        logger.info("Подключение к PostgreSQL закрыто")


def main():
    app = web.Application()
    setup(
        app,
        create_session_storage(
            secret_key=settings.SECRET_KEY,
            environment=settings.ENVIRONMENT,
        ),
    )

    aiohttp_jinja2.setup(
        app=app,
        loader=jinja2.PackageLoader(
            package_name="main",
            package_path="templates",
        ),
        context_processors=[session_context_processor],
    )

    setup_routes(app)
    app["config"] = BaseConfig
    app["settings"] = settings
    app.cleanup_ctx.append(init_db)

    web.run_app(app, host=settings.HOST, port=settings.PORT)


if __name__ == "__main__":
    main()
