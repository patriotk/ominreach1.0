#!/usr/bin/env python3
"""
Ensure AI agent profile uniqueness by creating database index
Run this after cleanup to prevent future duplicates
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()


async def ensure_uniqueness():
    """Create unique index on ai_agent_profiles collection"""
    
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("🔧 Ensuring AI agent profile uniqueness...")
    
    # Drop existing index if it exists (in case we need to recreate)
    try:
        await db.ai_agent_profiles.drop_index("unique_user_profile_name")
        print("  🗑️  Dropped existing index")
    except Exception:
        pass
    
    # Create unique compound index on user_id + name
    try:
        result = await db.ai_agent_profiles.create_index(
            [("user_id", 1), ("name", 1)],
            unique=True,
            name="unique_user_profile_name"
        )
        print(f"  ✅ Created unique index: {result}")
        print("\n✨ Success! Database now enforces unique profile names per user.")
        print("  → Attempts to create duplicate profiles will be rejected")
        print("  → API will return existing profile instead of creating duplicate")
    except Exception as e:
        print(f"  ❌ Failed to create index: {str(e)}")
        print("  → Make sure there are no duplicate profiles first")
        print("  → Run cleanup_duplicate_profiles.py to remove duplicates")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(ensure_uniqueness())
