import base64
import hashlib
import secrets

import asyncpg


_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_SIZE = 16
_KEY_LENGTH = 32


def hash_password(password: str) -> str:
    """Hash a password with a random salt using scrypt."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string")
    salt = secrets.token_bytes(_SALT_SIZE)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"), salt=salt,
        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_KEY_LENGTH,
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii")
    return "scrypt$" + "$".join(map(str, (_SCRYPT_N, _SCRYPT_R, _SCRYPT_P))) + "$" + encode(salt) + "$" + encode(derived_key)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a value produced by hash_password."""
    try:
        algorithm, n, r, p, salt, expected = password_hash.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt_bytes = base64.urlsafe_b64decode(salt.encode("ascii"))
        expected_bytes = base64.urlsafe_b64decode(expected.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt_bytes,
            n=int(n), r=int(r), p=int(p), dklen=len(expected_bytes),
        )
        return secrets.compare_digest(actual, expected_bytes)
    except (AttributeError, TypeError, ValueError):
        return False


class UserModel:
    """Persistence operations for PostgreSQL users."""

    @staticmethod
    async def create_user(db_pool, email, first_name, last_name, password):
        if not isinstance(email, str) or not email.strip():
            raise ValueError("Email is required")
        if not isinstance(password, str) or not password:
            raise ValueError("Password is required")
        normalized_email = email.strip().lower()
        password_hash = hash_password(password)
        async with db_pool.acquire() as connection:
            return await connection.fetchrow(
                """
                INSERT INTO users (email, first_name, last_name, password_hash)
                VALUES ($1, $2, $3, $4)
                RETURNING id, email, first_name, last_name, created_at
                """,
                normalized_email,
                first_name.strip() if isinstance(first_name, str) else first_name,
                last_name.strip() if isinstance(last_name, str) else last_name,
                password_hash,
            )

    @staticmethod
    async def get_by_email(db_pool, email):
        """Return an authentication record for a normalized email address."""
        if not isinstance(email, str) or not email.strip():
            return None
        async with db_pool.acquire() as connection:
            return await connection.fetchrow(
                """
                SELECT id, email, first_name, last_name, password_hash, created_at
                FROM users
                WHERE email = $1
                """,
                email.strip().lower(),
            )

    @staticmethod
    async def get_by_id(db_pool, user_id):
        """Return a public user profile without password credentials."""
        async with db_pool.acquire() as connection:
            return await connection.fetchrow(
                """
                SELECT id, email, first_name, last_name, created_at
                FROM users
                WHERE id = $1
                """,
                user_id,
            )


class User:
    """Legacy compatibility facade; new registration code uses UserModel."""

    collection = None

    def __init__(self):
        pass

    @classmethod
    async def get_user(cls, db, uid: int):
        return await db.users().find_one(id=uid)

    @staticmethod
    async def create_new_user(db, data: dict):
        users_collection = db.users()
        user = await users_collection.find_one(email=data["email"])
        if user:
            return user
        new_id = await users_collection.insert_one(**data)
        return await users_collection.find_one(id=new_id)
