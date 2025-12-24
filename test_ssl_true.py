#!/usr/bin/env python3
"""Test with ssl=True (boolean)"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    database_url = os.getenv("DATABASE_URL", "")
    url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    parts = url.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    user = user_pass[0]
    password = ":".join(user_pass[1:])
    
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 5432
    database = host_db[1] if len(host_db) > 1 else "postgres"
    
    print(f"Testing: {host}:{port} with ssl=True")
    
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                ssl=True,  # Simple boolean
                timeout=10
            ),
            timeout=15
        )
        version = await conn.fetchval("SELECT version()")
        print(f"✅ SUCCESS: {version[:60]}")
        await conn.close()
        return True
    except asyncio.TimeoutError:
        print("❌ TIMEOUT")
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {str(e)[:100]}")

if __name__ == "__main__":
    asyncio.run(test())

