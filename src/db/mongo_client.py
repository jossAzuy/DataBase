from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from src.config import settings


mongo_client = MongoClient(settings.mongo_uri)


def get_database() -> Database:
    return mongo_client[settings.mongo_db]


def get_games_collection() -> Collection:
    return get_database()[settings.mongo_collection]
