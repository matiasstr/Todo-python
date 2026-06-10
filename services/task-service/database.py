import os

from pymongo import MongoClient


def _use_mock_database():
    value = os.getenv("USE_MOCK_DB", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_database():
    database_name = os.getenv("TASK_DB_NAME", "task_db")

    if _use_mock_database():
        import mongomock

        client = mongomock.MongoClient()
        return client[database_name]

    mongo_uri = os.getenv("TASK_MONGO_URI", os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    client = MongoClient(mongo_uri)
    return client[database_name]


def configure_indexes(db):
    db.tasks.create_index([("user_id", 1)])
