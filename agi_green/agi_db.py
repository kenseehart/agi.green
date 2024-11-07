from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import os

_db = None

def get_collection(collection_name) -> AsyncIOMotorCollection:
    global _db

    # Establish a connection to MongoDB
    db_uri = os.getenv('AGI_GREEN_URI')
    client = AsyncIOMotorClient(db_uri)

    if db_uri is None:
        raise ValueError("Please set the AGI_GREEN_URI environment variable")

    # Select your database
    db_name = os.getenv('AGI_GREEN_DB')
    _db = client[db_name]

    if db_name is None:
        raise ValueError("Please set the AGI_GREEN_DB environment variable")

    return _db[collection_name]

