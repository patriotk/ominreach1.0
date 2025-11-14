#!/usr/bin/env python3
import asyncio
import os
import uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_login():
    mongo_url = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    email = "patriot@liquidsmarts.com"
    
    # Get or create user
    user = await db.users.find_one({"email": email})
    if not user:
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email,
            "name": "Patriot",
            "role": "admin",
            "picture": None,
            "created_at": datetime.now(timezone.utc),
            "credits": 10000
        }
        await db.users.insert_one(user)
        print(f"✅ Created user: {email}")
    else:
        user_id = user['id']
        print(f"✅ User exists: {email}")
    
    # Delete old sessions
    await db.user_sessions.delete_many({"user_id": user_id})
    print("🗑️  Deleted old sessions")
    
    # Create new session
    session_token = f"patriot_session_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=365)
    
    session = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await db.user_sessions.insert_one(session)
    print(f"✅ Created new session")
    
    # Verify it's there
    check = await db.user_sessions.find_one({"session_token": session_token})
    print(f"\n✅ Verification: Session found = {check is not None}")
    
    print(f"\n{'='*70}")
    print(f"WORKING LOGIN CREDENTIALS")
    print(f"{'='*70}")
    print(f"Session Token: {session_token}")
    print(f"User ID: {user_id}")
    print(f"Email: {email}")
    print(f"Expires: {expires_at}")
    print(f"\n🚀 USE THIS IN BROWSER CONSOLE:")
    print(f"\nlocalStorage.setItem('session_token', '{session_token}');")
    print(f"localStorage.setItem('user', JSON.stringify({{")
    print(f"  id: '{user_id}',")
    print(f"  email: '{email}',")
    print(f"  name: 'Patriot',")
    print(f"  role: 'admin'")
    print(f"}}));")
    print(f"window.location.href = '/dashboard';")
    print(f"{'='*70}\n")
    
    client.close()

asyncio.run(fix_login())
