from utils.database import Database

class User:

    collection = None

    def __init__(self):
        pass

    @classmethod
    async def get_user(cls, uid):
        pass
        #returncls.collection.find_one(uid)

    @staticmethod
    async def create_new_user(db: Database, data):
        email = data['email']
        user = await db.users.find_one(
            {
                'email': email
            }
        )
