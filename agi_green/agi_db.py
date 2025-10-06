from pymongo import AsyncMongoClient
from pymongo.collection import Collection as AsyncCollection
import os

_db = None

def get_collection(collection_name) -> AsyncCollection:
    global _db

    # Establish a connection to MongoDB
    db_uri = os.getenv('AGI_GREEN_URI')
    client = AsyncMongoClient(db_uri)

    if db_uri is None:
        raise ValueError("Please set the AGI_GREEN_URI environment variable")

    # Select your database
    db_name = os.getenv('AGI_GREEN_DB')
    _db = client[db_name]

    if db_name is None:
        raise ValueError("Please set the AGI_GREEN_DB environment variable")

    return _db[collection_name]
