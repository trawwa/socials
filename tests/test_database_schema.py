import os
import unittest

import asyncpg

from utils.database import Database


@unittest.skipUnless(os.getenv("TEST_POSTGRES") == "1", "requires PostgreSQL service")
class DatabaseSchemaIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_schema_is_idempotent_and_enforces_relations(self):
        db = Database(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "social_network"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            min_size=1,
            max_size=2,
        )
        await db.connect()
        try:
            # Applying the schema twice must be safe for application restarts.
            await db.apply_schema()
            await db.apply_schema()

            async with db._get_pool().acquire() as conn:
                user_indexes = await conn.fetch(
                    """
                    SELECT indexdef
                    FROM pg_indexes
                    WHERE schemaname = current_schema()
                      AND tablename = 'users'
                    """
                )
                self.assertTrue(
                    any("UNIQUE" in row["indexdef"].upper() for row in user_indexes),
                    "users.email must be backed by a unique index",
                )

                alice_id = await conn.fetchval(
                    """
                    INSERT INTO users (email, password_hash, first_name)
                    VALUES ($1, $2, $3)
                    RETURNING id
                    """,
                    "alice@example.test",
                    "hash-a",
                    "Alice",
                )
                bob_id = await conn.fetchval(
                    """
                    INSERT INTO users (email, password_hash, first_name)
                    VALUES ($1, $2, $3)
                    RETURNING id
                    """,
                    "bob@example.test",
                    "hash-b",
                    "Bob",
                )

                with self.assertRaises(asyncpg.UniqueViolationError):
                    await conn.execute(
                        "INSERT INTO users (email, password_hash) VALUES ($1, $2)",
                        "alice@example.test",
                        "another-hash",
                    )

                await conn.execute(
                    "INSERT INTO posts (user_id, message) VALUES ($1, $2)",
                    alice_id,
                    "Hello",
                )
                await conn.execute(
                    "INSERT INTO friends (user_id, friend_id) VALUES ($1, $2)",
                    alice_id,
                    bob_id,
                )
                await conn.execute(
                    """
                    INSERT INTO messages (sender_id, recipient_id, text)
                    VALUES ($1, $2, $3)
                    """,
                    alice_id,
                    bob_id,
                    "Hi Bob",
                )

                with self.assertRaises(asyncpg.ForeignKeyViolationError):
                    await conn.execute(
                        "INSERT INTO posts (user_id, message) VALUES ($1, $2)",
                        999999999,
                        "Orphan post",
                    )

                with self.assertRaises(asyncpg.CheckViolationError):
                    await conn.execute(
                        "INSERT INTO friends (user_id, friend_id) VALUES ($1, $1)",
                        alice_id,
                    )

                self.assertEqual(
                    await conn.fetchval("SELECT count(*) FROM posts WHERE user_id = $1", alice_id),
                    1,
                )
                self.assertEqual(
                    await conn.fetchval(
                        "SELECT count(*) FROM messages WHERE sender_id = $1 AND recipient_id = $2",
                        alice_id,
                        bob_id,
                    ),
                    1,
                )
        finally:
            await db.execute(
                "DROP TABLE IF EXISTS messages, friends, posts, users CASCADE"
            )
            await db.disconnect()


if __name__ == "__main__":
    unittest.main()
