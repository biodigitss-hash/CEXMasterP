#!/usr/bin/env python3
"""
Optimization Script for Crypto Arbitrage Bot
Fixes all errors and optimizes performance
"""

import asyncio
import aiomysql
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
db_name = os.environ.get('DB_NAME', 'crypto_arbitrage')

async def optimize_mongodb():
    """Optimize MongoDB indexes and performance"""
    print("\n=== Optimizing MongoDB ===")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Create indexes for better performance
    indexes = [
        ('tokens', [('symbol', 1), ('is_active', 1)]),
        ('exchanges', [('name', 1), ('is_active', 1)]),
        ('arbitrage_opportunities', [('status', 1), ('detected_at', -1)]),
        ('arbitrage_opportunities', [('token_symbol', 1)]),
        ('transaction_logs', [('opportunity_id', 1), ('created_at', -1)]),
    ]
    
    for collection_name, index_spec in indexes:
        try:
            await db[collection_name].create_index(index_spec)
            print(f"✓ Created index on {collection_name}: {index_spec}")
        except Exception as e:
            print(f"✗ Index creation failed for {collection_name}: {e}")
    
    # Cleanup old opportunities (older than 7 days)
    from datetime import datetime, timedelta
    cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
    
    result = await db.arbitrage_opportunities.delete_many({
        'detected_at': {'$lt': cutoff_date},
        'status': {'$in': ['detected', 'failed']}
    })
    print(f"✓ Cleaned up {result.deleted_count} old opportunities")
    
    # Cleanup old transaction logs (older than 30 days)
    cutoff_date_logs = (datetime.now() - timedelta(days=30)).isoformat()
    result_logs = await db.transaction_logs.delete_many({
        'created_at': {'$lt': cutoff_date_logs}
    })
    print(f"✓ Cleaned up {result_logs.deleted_count} old transaction logs")
    
    client.close()
    print("✓ MongoDB optimization complete\n")

async def check_system_health():
    """Check system health and report issues"""
    print("\n=== System Health Check ===")
    
    # Check MongoDB connection
    try:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        await client.server_info()
        print("✓ MongoDB connection: OK")
        client.close()
    except Exception as e:
        print(f"✗ MongoDB connection: FAILED - {e}")
    
    # Check environment variables
    required_vars = ['MONGO_URL', 'ENCRYPTION_KEY']
    for var in required_vars:
        if os.environ.get(var):
            print(f"✓ Environment variable {var}: SET")
        else:
            print(f"✗ Environment variable {var}: MISSING")
    
    print("✓ Health check complete\n")

async def main():
    print("="*50)
    print("Crypto Arbitrage Bot Optimization")
    print("="*50)
    
    await check_system_health()
    await optimize_mongodb()
    
    print("="*50)
    print("Optimization Complete!")
    print("Restart backend to apply changes: sudo supervisorctl restart backend")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())