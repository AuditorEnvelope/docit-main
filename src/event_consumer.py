"""
Event Consumer - Processes commit events from the Commit Bus

This worker continuously polls for unprocessed events and triggers
the documentation generation pipeline.

Key Features:
- Processes events in chronological order
- Handles failures with retry logic
- Logs all processing attempts
- Graceful shutdown
"""

import asyncio
import os
import signal
import sys
from datetime import datetime
from typing import Optional
import asyncpg
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from commit_bus import CommitBusService, CommitEvent
from smart_processor import handle_push_event
from github_sync import GitHubSync

load_dotenv()

class EventConsumer:
    """
    Event Consumer - Processes commit events from the event store
    
    Architecture:
    1. Poll for unprocessed events (every 5 seconds)
    2. Process each event (call smart_processor)
    3. Mark as processed or failed
    4. Log processing attempts
    5. Retry failed events (up to 3 times)
    """
    
    def __init__(self, db_url: str, batch_size: int = 10, poll_interval: int = 5):
        self.db_url = db_url
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.bus = None
        self.running = False
        self.pool = None
    
    async def init(self):
        """Initialize database connections"""
        self.bus = CommitBusService(self.db_url)
        await self.bus.init_pool()
        self.pool = self.bus.pool
        print("✅ Event Consumer initialized")
        
        # Check for missed commits on startup
        await self.check_missed_commits()
    
    async def log_processing(
        self, 
        event_id: str, 
        status: str, 
        started_at: datetime,
        error: Optional[str] = None
    ):
        """Log processing attempt to audit table"""
        completed_at = datetime.now()
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO event_processing_log (
                    event_id, status, started_at, completed_at, duration_ms, error
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, event_id, status, started_at, completed_at, duration_ms, error)
    
    def convert_to_webhook_payload(self, event: dict) -> dict:
        """
        Convert event store format to webhook payload format
        
        This allows us to reuse the existing smart_processor without changes
        """
        return {
            "repository": {
                "full_name": event["repo_id"],
                "name": event["repo_id"].split("/")[-1] if "/" in event["repo_id"] else event["repo_id"]
            },
            "commits": [{
                "id": event["commit_sha"],
                "message": event["commit_message"],
                "timestamp": event["timestamp"].isoformat(),
                "author": {
                    "name": event["author_name"],
                    "email": event["author_email"]
                },
                "added": [],
                "modified": [f["path"] for f in event.get("files_changed", []) if f.get("status") == "modified"],
                "removed": [f["path"] for f in event.get("files_changed", []) if f.get("status") == "deleted"]
            }],
            "ref": f"refs/heads/{event['branch']}",
            "after": event["commit_sha"],
            "before": event["parent_sha"][0] if event.get("parent_sha") else None
        }
    
    async def process_event(self, event: dict) -> bool:
        """
        Process a single event
        
        Returns: True if successful, False if failed
        """
        event_id = str(event["event_id"])
        started_at = datetime.now()
        
        try:
            print(f"\n{'='*60}")
            print(f"📝 Processing event: {event_id}")
            print(f"   Repo: {event['repo_id']}")
            print(f"   Commit: {event['commit_sha'][:8]}")
            print(f"   Message: {event['commit_message'][:50]}...")
            print(f"{'='*60}")
            
            # Log start
            await self.log_processing(event_id, "started", started_at)
            
            # Convert to webhook format
            payload = self.convert_to_webhook_payload(event)
            
            # Process using existing smart_processor
            # This is synchronous, so we run it in executor to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, 
                handle_push_event, 
                payload
            )
            
            # Mark as processed
            await self.bus.mark_processed(event_id, success=True)
            
            # Log completion
            await self.log_processing(event_id, "completed", started_at)
            
            print(f"✅ Event {event_id} processed successfully")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error processing event {event_id}: {error_msg}")
            
            # Mark as failed (increments retry_count)
            await self.bus.mark_processed(event_id, success=False, error=error_msg)
            
            # Log failure
            await self.log_processing(event_id, "failed", started_at, error=error_msg)
            
            return False
    
    async def check_missed_commits(self):
        """
        Check for missed commits on startup
        
        This queries GitHub for recent commits and compares with our database
        to find any commits that were missed during downtime.
        """
        try:
            print("\n🔍 Checking for missed commits...")
            
            # Get unprocessed events from database
            stats = await self.bus.get_event_stats()
            
            if stats["pending"] > 0:
                print(f"📊 Found {stats['pending']} unprocessed events in database")
                print(f"   These will be processed automatically")
            
            # Check GitHub for missed commits
            github_token = os.getenv("GITHUB_TOKEN")
            github_org = os.getenv("GITHUB_ORG", "AuditorEnvelope")
            enable_github_sync = os.getenv("ENABLE_GITHUB_SYNC", "false").lower() == "true"
            
            if github_token and enable_github_sync:
                try:
                    sync = GitHubSync(github_token)
                    
                    # Get last processed commit SHA
                    last_sha = await self.get_last_processed_sha()
                    
                    # Find missed commits from GitHub
                    missed = await sync.find_missed_commits(
                        f"{github_org}/lekhak_ai",
                        last_processed_sha=last_sha
                    )
                    
                    # Store missed commits in database
                    if missed:
                        print(f"\n💾 Storing {len(missed)} missed commits in database...")
                        for event_dict in missed:
                            try:
                                # Convert dict to CommitEvent object
                                event = CommitEvent(**event_dict)
                                await self.bus.store_event(event)
                                print(f"   ✅ Stored: {event.commit_sha[:8]}")
                            except Exception as e:
                                print(f"   ⚠️  Failed to store {event_dict['commit_sha'][:8]}: {e}")
                        
                        print(f"\n🎉 Successfully recovered {len(missed)} missed commits!")
                        print(f"   They will be processed automatically")
                    
                except Exception as e:
                    print(f"⚠️  Error syncing with GitHub: {e}")
                    print(f"   Relying on GitHub webhook retries instead")
            else:
                print(f"⚠️  GITHUB_TOKEN not set, skipping GitHub sync")
                print(f"   Relying on GitHub webhook retries instead")
            
            if stats["pending"] == 0 and (not github_token or not missed):
                print(f"\n✅ No missed commits found")
                print(f"   Last processed: {stats['processed']} events")
            
        except Exception as e:
            print(f"⚠️  Error checking missed commits: {e}")
    
    async def get_last_processed_sha(self) -> Optional[str]:
        """Get SHA of last successfully processed commit"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT commit_sha FROM commit_events
                    WHERE processed = TRUE
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                return result["commit_sha"] if result else None
        except:
            return None
    
    async def consume_batch(self):
        """
        Consume a batch of events
        
        Processes events in order, one at a time
        """
        try:
            # Get unprocessed events
            events = await self.bus.get_unprocessed_events(limit=self.batch_size)
            
            if not events:
                return 0
            
            print(f"\n🔄 Processing batch of {len(events)} events")
            
            processed_count = 0
            for event in events:
                if not self.running:
                    print("⏸️  Consumer stopped, breaking batch")
                    break
                
                success = await self.process_event(event)
                if success:
                    processed_count += 1
            
            return processed_count
            
        except Exception as e:
            print(f"❌ Error in consume_batch: {e}")
            return 0
    
    async def run(self):
        """
        Main consumer loop
        
        Continuously polls for events and processes them
        """
        self.running = True
        print(f"\n🚀 Event Consumer started")
        print(f"   Batch size: {self.batch_size}")
        print(f"   Poll interval: {self.poll_interval}s")
        print(f"   Database: {self.db_url.split('@')[-1] if '@' in self.db_url else 'local'}")
        print(f"\n{'='*60}\n")
        
        while self.running:
            try:
                # Get stats
                stats = await self.bus.get_event_stats()
                
                if stats["pending"] > 0:
                    print(f"\n📊 Stats: {stats['pending']} pending, {stats['processed']} processed, {stats['failed']} failed")
                    
                    # Process batch
                    processed = await self.consume_batch()
                    
                    if processed > 0:
                        print(f"✅ Processed {processed} events in this batch")
                else:
                    # No events, wait longer
                    print(".", end="", flush=True)
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                print("\n⏹️  Received interrupt signal")
                break
            except Exception as e:
                print(f"\n❌ Error in consumer loop: {e}")
                # Wait before retrying
                await asyncio.sleep(self.poll_interval * 2)
        
        print("\n👋 Event Consumer stopped")
    
    async def stop(self):
        """Graceful shutdown"""
        print("\n⏹️  Stopping consumer...")
        self.running = False
        
        if self.pool:
            await self.pool.close()
        
        print("✅ Consumer stopped gracefully")

# Global consumer instance
consumer = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n⚠️  Received signal {signum}")
    if consumer:
        asyncio.create_task(consumer.stop())

async def main():
    """Main entry point"""
    global consumer
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Get configuration
    batch_size = int(os.getenv("CONSUMER_BATCH_SIZE", "10"))
    poll_interval = int(os.getenv("CONSUMER_POLL_INTERVAL", "5"))
    
    # Create consumer
    consumer = EventConsumer(db_url, batch_size, poll_interval)
    await consumer.init()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run consumer
    try:
        await consumer.run()
    except KeyboardInterrupt:
        pass
    finally:
        await consumer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
