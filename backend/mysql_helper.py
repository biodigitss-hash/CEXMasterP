"""
MySQL Database Helper for Crypto Arbitrage Bot
Replaces MongoDB with MySQL using aiomysql
"""

import aiomysql
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


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
    
    async def insert_one(self, table: str, data: Dict) -> str:
        """Insert single document, returns inserted ID"""
        # Generate UUID if not present
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        
        # Convert Python objects to JSON strings for JSON columns
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                data[key] = json.dumps(value)
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        await self.execute(query, tuple(data.values()))
        return data['id']
    
    async def find_one(self, table: str, filter_dict: Dict, projection: Dict = None) -> Optional[Dict]:
        """Find single document"""
        where_clause = ' AND '.join([f"{k} = %s" for k in filter_dict.keys()])
        query = f"SELECT * FROM {table} WHERE {where_clause} LIMIT 1"
        
        result = await self.fetch_one(query, tuple(filter_dict.values()))
        
        if result:
            # Parse JSON fields back to Python objects
            result = self._parse_json_fields(table, result)
        
        return result
    
    async def find(self, table: str, filter_dict: Dict = None, projection: Dict = None, 
                   sort: List[tuple] = None, limit: int = None) -> List[Dict]:
        """Find multiple documents"""
        query = f"SELECT * FROM {table}"
        params = []
        
        if filter_dict:
            where_clause = ' AND '.join([f"{k} = %s" for k in filter_dict.keys()])
            query += f" WHERE {where_clause}"
            params.extend(filter_dict.values())
        
        if sort:
            order_clause = ', '.join([f"{col} {direction}" for col, direction in sort])
            query += f" ORDER BY {order_clause}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        results = await self.fetch_all(query, tuple(params) if params else None)
        
        # Parse JSON fields
        return [self._parse_json_fields(table, row) for row in results]
    
    async def update_one(self, table: str, filter_dict: Dict, update_dict: Dict, upsert: bool = False):
        """Update single document"""
        # Convert Python objects to JSON
        for key, value in update_dict.items():
            if isinstance(value, (dict, list)):
                update_dict[key] = json.dumps(value)
        
        set_clause = ', '.join([f"{k} = %s" for k in update_dict.keys()])
        where_clause = ' AND '.join([f"{k} = %s" for k in filter_dict.keys()])
        
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = list(update_dict.values()) + list(filter_dict.values())
        
        rows_affected = await self.execute(query, tuple(params))
        
        # Handle upsert
        if rows_affected == 0 and upsert:
            merged_data = {**filter_dict, **update_dict}
            await self.insert_one(table, merged_data)
    
    async def delete_many(self, table: str, filter_dict: Dict) -> int:
        """Delete multiple documents"""
        where_clause = ' AND '.join([f"{k} = %s" for k in filter_dict.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"
        
        return await self.execute(query, tuple(filter_dict.values()))
    
    async def count_documents(self, table: str, filter_dict: Dict = None) -> int:
        """Count documents"""
        query = f"SELECT COUNT(*) as count FROM {table}"
        params = []
        
        if filter_dict:
            where_clause = ' AND '.join([f"{k} = %s" for k in filter_dict.keys()])
            query += f" WHERE {where_clause}"
            params.extend(filter_dict.values())
        
        result = await self.fetch_one(query, tuple(params) if params else None)
        return result['count'] if result else 0
    
    def _parse_json_fields(self, table: str, row: Dict) -> Dict:
        """Parse JSON string fields back to Python objects"""
        # Define which fields are JSON for each table
        json_fields_map = {
            'tokens': ['monitored_exchanges'],
            'arbitrage_opportunities': [],
            'transaction_logs': ['details'],
            'settings': [],
            'wallet': [],
            'exchanges': []
        }
        
        if table in json_fields_map:
            for field in json_fields_map[table]:
                if field in row and isinstance(row[field], str):
                    try:
                        row[field] = json.loads(row[field])
                    except:
                        pass
        
        return row


# Collection-like wrappers for compatibility with MongoDB code
class Collection:
    """MongoDB collection compatibility wrapper"""
    
    def __init__(self, db: MySQLDatabase, table_name: str):
        self.db = db
        self.table_name = table_name
    
    async def insert_one(self, document: Dict):
        """Insert document"""
        doc_id = await self.db.insert_one(self.table_name, document)
        return type('InsertResult', (), {'inserted_id': doc_id})()
    
    async def find_one(self, filter_dict: Dict = None, projection: Dict = None):
        """Find one document"""
        if filter_dict is None:
            filter_dict = {}
        return await self.db.find_one(self.table_name, filter_dict, projection)
    
    async def find(self, filter_dict: Dict = None, projection: Dict = None):
        """Find documents - returns cursor-like object"""
        if filter_dict is None:
            filter_dict = {}
        
        class Cursor:
            def __init__(self, db, table, filter_dict):
                self.db = db
                self.table = table
                self.filter_dict = filter_dict
                self._sort = None
                self._limit = None
            
            def sort(self, key: str, direction: int):
                """Sort results"""
                order = 'DESC' if direction == -1 else 'ASC'
                self._sort = [(key, order)]
                return self
            
            def limit(self, count: int):
                """Limit results"""
                self._limit = count
                return self
            
            async def to_list(self, length: int = None):
                """Convert to list"""
                limit = length or self._limit
                return await self.db.find(
                    self.table, 
                    self.filter_dict, 
                    sort=self._sort, 
                    limit=limit
                )
        
        return Cursor(self.db, self.table_name, filter_dict)
    
    async def update_one(self, filter_dict: Dict, update_dict: Dict, upsert: bool = False):
        """Update one document"""
        # Handle MongoDB $set syntax
        if '$set' in update_dict:
            update_dict = update_dict['$set']
        
        await self.db.update_one(self.table_name, filter_dict, update_dict, upsert)
        return type('UpdateResult', (), {'modified_count': 1})()
    
    async def delete_many(self, filter_dict: Dict):
        """Delete documents"""
        deleted_count = await self.db.delete_many(self.table_name, filter_dict)
        return type('DeleteResult', (), {'deleted_count': deleted_count})()
    
    async def count_documents(self, filter_dict: Dict = None):
        """Count documents"""
        if filter_dict is None:
            filter_dict = {}
        return await self.db.count_documents(self.table_name, filter_dict)


class Database:
    """MongoDB database compatibility wrapper"""
    
    def __init__(self, mysql_db: MySQLDatabase):
        self.mysql_db = mysql_db
        self._collections = {}
    
    def __getattr__(self, name: str):
        """Get collection by attribute access"""
        if name not in self._collections:
            self._collections[name] = Collection(self.mysql_db, name)
        return self._collections[name]
    
    def __getitem__(self, name: str):
        """Get collection by subscript access"""
        return self.__getattr__(name)
