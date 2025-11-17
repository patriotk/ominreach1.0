#!/usr/bin/env python3
"""
Cleanup script to remove duplicate AI agent profiles
Keeps only the first occurrence of each profile name per user
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()


async def cleanup_duplicates():
    """Remove duplicate AI agent profiles from database"""
    
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("🔍 Finding duplicate AI agent profiles...")
    
    # Get all profiles
    all_profiles = await db.ai_agent_profiles.find().to_list(None)
    
    print(f"📊 Total profiles found: {len(all_profiles)}")
    
    # Group by user_id and name
    profiles_by_user_and_name = defaultdict(list)
    
    for profile in all_profiles:
        user_id = profile.get("user_id", "unknown")
        name = profile.get("name", "unnamed")
        key = f"{user_id}|{name}"
        profiles_by_user_and_name[key].append(profile)
    
    # Find duplicates
    duplicates_to_remove = []
    profiles_to_keep = []
    
    for key, profiles in profiles_by_user_and_name.items():
        if len(profiles) > 1:
            # Keep the first one (oldest), remove the rest
            profiles_to_keep.append(profiles[0])
            duplicates_to_remove.extend(profiles[1:])
            
            user_id, name = key.split("|", 1)
            print(f"  ⚠️  Found {len(profiles)} duplicates of '{name}' for user {user_id}")
        else:
            profiles_to_keep.append(profiles[0])
    
    print(f"\n📋 Summary:")
    print(f"  ✅ Profiles to keep: {len(profiles_to_keep)}")
    print(f"  🗑️  Duplicates to remove: {len(duplicates_to_remove)}")
    
    if len(duplicates_to_remove) == 0:
        print("\n✨ No duplicates found! Database is clean.")
        client.close()
        return
    
    # Remove duplicates
    print(f"\n🧹 Removing {len(duplicates_to_remove)} duplicate profiles...")
    
    for duplicate in duplicates_to_remove:
        profile_id = duplicate.get("id")
        if profile_id:
            result = await db.ai_agent_profiles.delete_one({"id": profile_id})
            if result.deleted_count > 0:
                print(f"  🗑️  Removed duplicate: {duplicate.get('name')} (ID: {profile_id[:8]}...)")
    
    # Verify cleanup
    remaining = await db.ai_agent_profiles.count_documents({})
    print(f"\n✅ Cleanup complete! Remaining profiles: {remaining}")
    
    # Create index to prevent future duplicates
    print("\n🔧 Creating unique index on (user_id, name)...")
    try:
        # Note: This will fail if there are still duplicates, but we've cleaned them
        await db.ai_agent_profiles.create_index(
            [("user_id", 1), ("name", 1)],
            unique=True,
            name="unique_user_profile_name"
        )
        print("✅ Index created successfully")
    except Exception as e:
        print(f"⚠️  Index creation failed (may already exist): {str(e)}")
    
    client.close()
    print("\n🎉 All done!")


if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
