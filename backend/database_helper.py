"""
Unified Database Helper for Crypto Arbitrage Bot
Supports both MongoDB and MySQL with automatic fallback
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import uuid
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables first
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Check which database to use based on env var availability
MONGO_URL = os.environ.get('MONGO_URL')
USE_MONGODB = MONGO_URL is not None and MONGO_URL.strip() != ''

if USE_MONGODB:
    from motor.motor_asyncio import AsyncIOMotorClient
    logger.info("Using MongoDB for database operations")
else:
    import aiomysql
    logger.info("Using MySQL for database operations")


class MongoDBDatabase:
    """MongoDB Database wrapper using Motor (async)"""
    
    def __init__(self, mongo_url: str, db_name: str):
        self.mongo_url = mongo_url
        self.db_name = db_name
        self.client = None
        self.db = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.client[self.db_name]
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"MongoDB connected: {self.db_name}")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


class MySQLDatabase:
    """Async MySQL database wrapper"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool = None
    
    async def connect(self):
        """Create connection pool"""
        try:
            self.pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                charset='utf8mb4',
                autocommit=True,
                minsize=5,
                maxsize=20
            )
            logger.info(f"MySQL connection pool created: {self.database}")
        except Exception as e:
            logger.error(f"Failed to create MySQL pool: {e}")
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("MySQL connection pool closed")
    
    async def execute(self, query: str, params: tuple = None) -> int:
        """Execute INSERT/UPDATE/DELETE query"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params or ())
                return cur.rowcount
    
    async def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch single row as dictionary"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params or ())
                return await cur.fetchone()
    
    async def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows as list of dictionaries"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params or ())
                return await cur.fetchall()


class MongoCollection:
    """MongoDB collection wrapper with familiar API"""
    
    def __init__(self, collection):
        self._collection = collection
    
    async def insert_one(self, document: Dict):
        """Insert document"""
        if 'id' not in document:
            document['id'] = str(uuid.uuid4())
        result = await self._collection.insert_one(document)
        return type('InsertResult', (), {'inserted_id': document['id']})()
    
    async def insert_many(self, documents: List[Dict]):
        """Insert multiple documents"""
        for doc in documents:
            if 'id' not in doc:
                doc['id'] = str(uuid.uuid4())
        if documents:
            await self._collection.insert_many(documents)
        return type('InsertManyResult', (), {'inserted_ids': [d['id'] for d in documents]})()
    
    async def find_one(self, filter_dict: Dict = None, projection: Dict = None):
        """Find one document"""
        if filter_dict is None:
            filter_dict = {}
        # Handle MongoDB operators
        filter_dict = self._convert_filter(filter_dict)
        doc = await self._collection.find_one(filter_dict, projection)
        if doc and '_id' in doc:
            del doc['_id']
        return doc
    
    def find(self, filter_dict: Dict = None, projection: Dict = None):
        """Find documents - returns cursor wrapper"""
        if filter_dict is None:
            filter_dict = {}
        filter_dict = self._convert_filter(filter_dict)
        return MongoCursor(self._collection, filter_dict, projection)
    
    async def update_one(self, filter_dict: Dict, update_dict: Dict, upsert: bool = False):
        """Update one document"""
        filter_dict = self._convert_filter(filter_dict)
        if '$set' not in update_dict:
            update_dict = {'$set': update_dict}
        result = await self._collection.update_one(filter_dict, update_dict, upsert=upsert)
        return type('UpdateResult', (), {'modified_count': result.modified_count})()
    
    async def delete_one(self, filter_dict: Dict):
        """Delete one document"""
        filter_dict = self._convert_filter(filter_dict)
        result = await self._collection.delete_one(filter_dict)
        return type('DeleteResult', (), {'deleted_count': result.deleted_count})()
    
    async def delete_many(self, filter_dict: Dict):
        """Delete documents"""
        filter_dict = self._convert_filter(filter_dict)
        result = await self._collection.delete_many(filter_dict)
        return type('DeleteResult', (), {'deleted_count': result.deleted_count})()
    
    async def count_documents(self, filter_dict: Dict = None):
        """Count documents"""
        if filter_dict is None:
            filter_dict = {}
        filter_dict = self._convert_filter(filter_dict)
        return await self._collection.count_documents(filter_dict)
    
    def _convert_filter(self, filter_dict: Dict) -> Dict:
        """Convert filter dict - handle special operators"""
        # MongoDB already supports $in, $regex etc
        return filter_dict


class MongoCursor:
    """MongoDB cursor wrapper"""
    
    def __init__(self, collection, filter_dict, projection):
        self._collection = collection
        self._filter = filter_dict
        self._projection = projection
        self._sort_key = None
        self._sort_direction = None
        self._limit_value = None
    
    def sort(self, key: str, direction: int):
        """Sort results"""
        self._sort_key = key
        self._sort_direction = direction
        return self
    
    def limit(self, count: int):
        """Limit results"""
        self._limit_value = count
        return self
    
    async def to_list(self, length: int = None):
        """Convert to list"""
        cursor = self._collection.find(self._filter, self._projection)
        
        if self._sort_key:
            cursor = cursor.sort(self._sort_key, self._sort_direction)
        
        limit = length or self._limit_value
        if limit:
            cursor = cursor.limit(limit)
        
        results = []
        async for doc in cursor:
            if '_id' in doc:
                del doc['_id']
            results.append(doc)
        
        return results


class Database:
    """Unified database interface"""
    
    def __init__(self, db_instance, is_mongo: bool = True):
        self._db = db_instance
        self._is_mongo = is_mongo
        self._collections = {}
    
    def __getattr__(self, name: str):
        """Get collection by attribute access"""
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        
        if name not in self._collections:
            if self._is_mongo:
                self._collections[name] = MongoCollection(self._db.db[name])
            else:
                # MySQL collection wrapper would go here
                pass
        return self._collections[name]
    
    def __getitem__(self, name: str):
        """Get collection by subscript access"""
        return self.__getattr__(name)


def create_database():
    """Factory function to create appropriate database instance"""
    if USE_MONGODB:
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'crypto_arbitrage')
        db_instance = MongoDBDatabase(mongo_url, db_name)
        return db_instance, Database(db_instance, is_mongo=True), True
    else:
        mysql_config = {
            'host': os.environ.get('MYSQL_HOST', 'localhost'),
            'port': int(os.environ.get('MYSQL_PORT', 3307)),
            'user': os.environ.get('MYSQL_USER', 'root'),
            'password': os.environ.get('MYSQL_PASSWORD', ''),
            'database': os.environ.get('MYSQL_DATABASE', 'crypto_arbitrage')
        }
        db_instance = MySQLDatabase(**mysql_config)
        return db_instance, Database(db_instance, is_mongo=False), False
