import unittest

from cryptography.fernet import Fernet, InvalidToken

from utils.session import create_session_storage


class SessionStorageTests(unittest.TestCase):
    def test_key_is_stable_for_same_secret(self):
        first = create_session_storage("a-long-test-secret", "development")
        second = create_session_storage("a-long-test-secret", "development")

        token = first._fernet.encrypt(b"session-data")
        self.assertEqual(second._fernet.decrypt(token), b"session-data")

    def test_different_secrets_cannot_decrypt_each_others_cookies(self):
        first = create_session_storage("first-secret", "development")
        second = create_session_storage("second-secret", "development")

        token = first._fernet.encrypt(b"session-data")
        with self.assertRaises(InvalidToken):
            second._fernet.decrypt(token)

    def test_production_rejects_placeholder_secret(self):
        with self.assertRaises(RuntimeError):
            create_session_storage("change-in-production", "production")

    def test_generated_key_is_accepted_by_fernet(self):
        storage = create_session_storage("test-secret", "development")
        self.assertIsInstance(storage._fernet, Fernet)


if __name__ == "__main__":
    unittest.main()
