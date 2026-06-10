import os

from pymongo import MongoClient


def _use_mock_database():
    value = os.getenv("USE_MOCK_DB", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_database():
    database_name = os.getenv("AUTH_DB_NAME", "auth_db")

    if _use_mock_database():
        import mongomock

        client = mongomock.MongoClient()
        return client[database_name]

    mongo_uri = os.getenv("AUTH_MONGO_URI", os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    client = MongoClient(mongo_uri)
    return client[database_name]


def configure_indexes(db):
    db.users.create_index("email", unique=True)
