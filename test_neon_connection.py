#!/usr/bin/env python3
"""Test script to diagnose Neon database connection issues"""
import asyncio
import asyncpg
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    """Test different connection methods to find what works"""
    database_url = os.getenv("DATABASE_URL", "")
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    print(f"🔍 Testing connection to: {database_url.split('@')[1] if '@' in database_url else 'N/A'}")
    
    # Parse connection string
    # Format: postgresql+asyncpg://user:pass@host:port/db
    url_parts = database_url.replace("postgresql+asyncpg://", "").split("@")
    if len(url_parts) != 2:
        print("❌ Invalid DATABASE_URL format")
        return
    
    user_pass = url_parts[0].split(":")
    user = user_pass[0]
    password = ":".join(user_pass[1:]) if len(user_pass) > 1 else ""
    
    host_db = url_parts[1].split("/")
    host_port = host_db[0].split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 5432
    database = host_db[1] if len(host_db) > 1 else "postgres"
    
    # Remove -pooler for direct connection
    if "-pooler" in host:
        host_direct = host.replace("-pooler", "")
        print(f"📡 Testing direct endpoint: {host_direct}")
    else:
        host_direct = host
        print(f"📡 Testing endpoint: {host_direct}")
    
    # Test 1: Direct connection with SSL context (CERT_NONE)
    print("\n🧪 Test 1: SSL context with CERT_NONE...")
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        conn = await asyncpg.connect(
            host=host_direct,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl=ssl_context,
            timeout=60
        )
        result = await conn.fetchval("SELECT version()")
        print(f"✅ Test 1 SUCCESS: {result[:50]}...")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Test 1 FAILED: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Direct connection with ssl=True
    print("\n🧪 Test 2: ssl=True (simple)...")
    try:
        conn = await asyncpg.connect(
            host=host_direct,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl=True,
            timeout=60
        )
        result = await conn.fetchval("SELECT version()")
        print(f"✅ Test 2 SUCCESS: {result[:50]}...")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
    
    # Test 3: Direct connection with CERT_REQUIRED
    print("\n🧪 Test 3: SSL context with CERT_REQUIRED...")
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        conn = await asyncpg.connect(
            host=host_direct,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl=ssl_context,
            timeout=60
        )
        result = await conn.fetchval("SELECT version()")
        print(f"✅ Test 3 SUCCESS: {result[:50]}...")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}")
    
    # Test 4: Pooler endpoint (original)
    if "-pooler" in host:
        print("\n🧪 Test 4: Pooler endpoint with CERT_NONE...")
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                ssl=ssl_context,
                timeout=60
            )
            result = await conn.fetchval("SELECT version()")
            print(f"✅ Test 4 SUCCESS: {result[:50]}...")
            await conn.close()
            return True
        except Exception as e:
            print(f"❌ Test 4 FAILED: {e}")
    
    print("\n❌ All connection tests failed!")
    return False

if __name__ == "__main__":
    asyncio.run(test_connection())

