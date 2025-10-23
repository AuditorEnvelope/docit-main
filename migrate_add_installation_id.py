#!/usr/bin/env python3
"""
Migration script to add installation_id column to commit_events table
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    """Add installation_id column to commit_events table"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set")
        return
    
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)
    
    try:
        async with pool.acquire() as conn:
            # Check if column already exists
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='commit_events' AND column_name='installation_id'
                )
            """)
            
            if result:
                print("✅ Column installation_id already exists")
                return
            
            # Add the column
            print("🔄 Adding installation_id column to commit_events table...")
            await conn.execute("""
                ALTER TABLE commit_events
                ADD COLUMN installation_id INTEGER
            """)
            
            print("✅ Successfully added installation_id column")
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(migrate())
