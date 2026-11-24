import base64
import hashlib

from aiohttp_session.cookie_storage import EncryptedCookieStorage


_INSECURE_DEFAULT_SECRET = "change-in-production"


def create_session_storage(secret_key: str, environment: str = "production"):
    """Create cookie storage using a stable Fernet key derived from config.

    aiohttp-session accepts a URL-safe Base64 Fernet key as a string. Passing
    the encoded value as bytes is interpreted as a raw 32-byte key by its
    storage constructor, which leads to an invalid Fernet key.
    """
    if not secret_key:
        raise RuntimeError("SECRET_KEY must be configured for session storage")

    if environment.lower() == "production" and secret_key == _INSECURE_DEFAULT_SECRET:
        raise RuntimeError(
            "Set a unique SECRET_KEY in the environment before starting in production"
        )

    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest).decode("ascii")
    return EncryptedCookieStorage(key)
