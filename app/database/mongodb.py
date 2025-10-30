from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

mongodb = MongoDB()

async def connect_to_mongo():
    try:
        # SIMPLE CONNECTION - NO TLS, NO CERTIFI
        mongodb.client = AsyncIOMotorClient(settings.MONGODB_URL)
        mongodb.database = mongodb.client[settings.MONGODB_DB_NAME]
        
        # Test connection
        await mongodb.client.admin.command('ping')
        
        # Create indexes
        await create_indexes()
        
        logger.info("✅ Connected to MongoDB successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    if mongodb.client:
        mongodb.client.close()
        logger.info("✅ MongoDB connection closed")

async def create_indexes():
    try:
        # Projects indexes
        await mongodb.database.projects.create_index([("featured", DESCENDING)])
        await mongodb.database.projects.create_index([("category", ASCENDING)])
        await mongodb.database.projects.create_index([("technologies", ASCENDING)])
        await mongodb.database.projects.create_index([("created_at", DESCENDING)])
        
        # Skills indexes
        await mongodb.database.skills.create_index([("category", ASCENDING)])
        await mongodb.database.skills.create_index([("featured", DESCENDING)])
        await mongodb.database.skills.create_index([("order", ASCENDING)])
        
        # Contacts indexes
        await mongodb.database.contacts.create_index([("created_at", DESCENDING)])
        await mongodb.database.contacts.create_index([("status", ASCENDING)])
        
        logger.info("✅ Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to create indexes: {e}")
        raise

def get_database():
    return mongodb.database

def get_collection(collection_name: str):
    return mongodb.database[collection_name]