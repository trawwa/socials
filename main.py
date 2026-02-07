import base64
import logging

import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet

from app.server_aiohttp.routes.base import setup_routes
from config.common import BaseConfig
from utils.database import Database
from config.config import settings


# Настройка логирования ДО создания приложения
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def init_db(app: web.Application):
    """Инициализация подключения к БД при старте"""
    db = Database(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
    await db.connect()
    app["db"] = db
    logger.info("✅ Подключение к PostgreSQL установлено")
    yield  # Приложение работает
    # Закрытие подключения при остановке
    await db.disconnect()
    logger.info("🔌 Подключение к PostgreSQL закрыто")


def main():
    app = web.Application()

    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    setup(app, EncryptedCookieStorage(secret_key))

    aiohttp_jinja2.setup(
        app=app,
        loader=jinja2.PackageLoader(
            package_name="main",
            package_path="templates",
        ),
    )

    setup_routes(app)
    app["config"] = BaseConfig
    app.cleanup_ctx.append(init_db)

    logging.basicConfig(level=logging.INFO)
    web.run_app(app)

if __name__ == "__main__":
    main()
