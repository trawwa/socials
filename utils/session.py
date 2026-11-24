import base64
import hashlib

from aiohttp_session.cookie_storage import EncryptedCookieStorage


_INSECURE_DEFAULT_SECRET = "change-in-production"


def create_session_storage(secret_key: str, environment: str = "production"):
    """Create cookie storage using a stable key derived from application config.

    The configured secret must remain unchanged between application restarts.
    In production, the placeholder default is rejected rather than silently
    encrypting session cookies with a publicly known key.
    """
    if not secret_key:
        raise RuntimeError("SECRET_KEY must be configured for session storage")

    if environment.lower() == "production" and secret_key == _INSECURE_DEFAULT_SECRET:
        raise RuntimeError(
            "Set a unique SECRET_KEY in the environment before starting in production"
        )

    key = base64.urlsafe_b64encode(
        hashlib.sha256(secret_key.encode("utf-8")).digest()
    )
    return EncryptedCookieStorage(key)
