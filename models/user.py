from utils.database import Database


class User:

    collection = None

    def __init__(self):
        pass

    @classmethod
    async def get_user(cls, db: Database, uid: int):
        """Возвращает пользователя по id, используя переданный `db` объект."""
        users_collection = db.users()
        return await users_collection.find_one(id=uid)

    @staticmethod
    async def create_new_user(db: Database, data: dict):
        email = data['email']
        users_collection = db.users()
        user = await users_collection.find_one(email=email)
        if user:
            return user
        # Простейшая вставка — вернёт id вставленного пользователя
        new_id = await users_collection.insert_one(**data)
        return await users_collection.find_one(id=new_id)
