#!/usr/bin/env python3
"""
Cleanup script to remove failed events from database
This is needed because old events have the wrong org_id before the fix
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def cleanup():
    """Remove failed events with wrong org"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set")
        return
    
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)
    
    try:
        async with pool.acquire() as conn:
            # Get stats before cleanup
            stats_before = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE processed = TRUE) as processed,
                    COUNT(*) FILTER (WHERE processed = FALSE) as pending,
                    COUNT(*) FILTER (WHERE retry_count > 0) as failed
                FROM commit_events
            """)
            
            print("📊 Stats BEFORE cleanup:")
            print(f"   Total: {stats_before['total']}")
            print(f"   Processed: {stats_before['processed']}")
            print(f"   Pending: {stats_before['pending']}")
            print(f"   Failed: {stats_before['failed']}")
            
            # Delete failed events (retry_count > 0)
            result = await conn.execute("""
                DELETE FROM commit_events
                WHERE retry_count > 0
            """)
            
            deleted_count = int(result.split()[-1])
            print(f"\n🗑️  Deleted {deleted_count} failed events")
            
            # Get stats after cleanup
            stats_after = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE processed = TRUE) as processed,
                    COUNT(*) FILTER (WHERE processed = FALSE) as pending,
                    COUNT(*) FILTER (WHERE retry_count > 0) as failed
                FROM commit_events
            """)
            
            print("\n📊 Stats AFTER cleanup:")
            print(f"   Total: {stats_after['total']}")
            print(f"   Processed: {stats_after['processed']}")
            print(f"   Pending: {stats_after['pending']}")
            print(f"   Failed: {stats_after['failed']}")
            
            print("\n✅ Cleanup complete!")
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(cleanup())
