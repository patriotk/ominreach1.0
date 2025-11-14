#!/usr/bin/env python3
"""
Quick script to create a user account directly in MongoDB
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def create_user(email: str, name: str):
    """Create a user and session directly"""
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client['omnireach']
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": email})
    
    if existing_user:
        print(f"✅ User already exists: {email}")
        user_id = existing_user['id']
    else:
        # Create new user
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email,
            "name": name,
            "role": "admin",
            "picture": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "credits": 1000
        }
        await db.users.insert_one(user)
        print(f"✅ Created new user: {email}")
    
    # Create session token
    session_token = f"session_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    
    session = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.user_sessions.insert_one(session)
    print(f"✅ Created session token")
    
    print(f"\n{'='*60}")
    print(f"LOGIN CREDENTIALS FOR: {email}")
    print(f"{'='*60}")
    print(f"Session Token: {session_token}")
    print(f"Expires: {expires_at}")
    print(f"\nTo use this session:")
    print(f"1. Open browser DevTools (F12)")
    print(f"2. Go to Console tab")
    print(f"3. Paste and run:")
    print(f"\n   localStorage.setItem('session_token', '{session_token}');")
    print(f"   localStorage.setItem('user', JSON.stringify({{")
    print(f"       id: '{user_id}',")
    print(f"       email: '{email}',")
    print(f"       name: '{name}',")
    print(f"       role: 'admin'")
    print(f"   }}));")
    print(f"   window.location.href = '/dashboard';")
    print(f"\n4. Or use Quick Access URL: /quick-access.html")
    print(f"{'='*60}\n")
    
    client.close()

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "patriot@liquidsmarts.com"
    name = sys.argv[2] if len(sys.argv) > 2 else "Patriot User"
    
    asyncio.run(create_user(email, name))
