#!/usr/bin/env python3
"""
Cleanup old failed events to unblock event consumer
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def cleanup():
    """Delete old failed events"""
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
            
            # Delete old events from AuditorEnvelope (not your repo)
            result = await conn.execute("""
                DELETE FROM commit_events
                WHERE repo_id LIKE 'AuditorEnvelope/%'
                AND (processed = FALSE OR retry_count > 0)
            """)
            
            deleted_count = int(result.split()[-1])
            print(f"\n🗑️  Deleted {deleted_count} old AuditorEnvelope events")
            
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
            
            # Show remaining events
            remaining = await conn.fetch("""
                SELECT repo_id, commit_sha, processed, retry_count
                FROM commit_events
                WHERE processed = FALSE OR retry_count > 0
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            if remaining:
                print("\n📋 Remaining unprocessed events:")
                for event in remaining:
                    print(f"   - {event['repo_id']}: {event['commit_sha'][:8]} (processed={event['processed']}, retries={event['retry_count']})")
            else:
                print("\n✅ No unprocessed events remaining!")
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(cleanup())
