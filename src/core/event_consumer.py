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

from core.commit_bus import CommitBusService, CommitEvent
from processors.smart_processor import handle_push_event
from utilities.github_sync import GitHubSync

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
    
    def __init__(self, db_url: str, batch_size: int = 10, poll_interval: int = 5, max_concurrent: int = 3):
        self.db_url = db_url
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.max_concurrent = max_concurrent  # Max parallel processing
        self.bus = None
        self.running = False
        self.pool = None
        self.semaphore = None  # Will be created in init()
    
    async def init(self):
        """Initialize database connections"""
        self.bus = CommitBusService(self.db_url)
        await self.bus.init_pool()
        self.pool = self.bus.pool
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        print("✅ Event Consumer initialized")
        print(f"   Max concurrent processing: {self.max_concurrent}")
        
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
        import json
        
        # Parse files_changed if it's a JSON string
        files_changed = event.get("files_changed", [])
        if isinstance(files_changed, str):
            try:
                files_changed = json.loads(files_changed)
            except:
                files_changed = []
        
        payload = {
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
                "modified": [f["path"] for f in files_changed if f.get("status") == "modified"],
                "removed": [f["path"] for f in files_changed if f.get("status") == "deleted"]
            }],
            "ref": f"refs/heads/{event['branch']}",
            "after": event["commit_sha"],
            "before": event["parent_sha"][0] if event.get("parent_sha") else None
        }
        
        # Add installation if available (for GitHub App)
        if event.get("installation_id"):
            payload["installation"] = {"id": event["installation_id"]}
        
        return payload
    
    async def get_github_token(self, user_id: str, token_id: str) -> Optional[str]:
        """
        Get decrypted GitHub token for user/org
        
        Args:
            user_id: UUID of user
            token_id: UUID of token record
        
        Returns:
            GitHub token string or None if not found
        """
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT github_token FROM user_github_tokens
                    WHERE user_id = $1 AND token_id = $2 AND is_active = TRUE
                """, user_id, token_id)
                
                if result:
                    token = result['github_token']
                    # TODO: Decrypt token here if encrypted in database
                    return token
                
                return None
        except Exception as e:
            print(f"⚠️  Error getting GitHub token: {e}")
            return None
    
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
            
            # Extract context (multi-org mode)
            user_id = event.get("user_id")
            org_id = event.get("org_id")
            token_id = event.get("github_token_id")
            
            # Get GitHub token
            github_token = None
            
            # Try multi-org mode first (get token for this user/org)
            if user_id and token_id:
                github_token = await self.get_github_token(user_id, token_id)
                
                if github_token:
                    print(f"✅ Got GitHub token for user {user_id} org {org_id}")
                else:
                    print(f"⚠️  No GitHub token found for user {user_id} org {org_id}")
            
            # Fall back to env var (single-org mode)
            if not github_token:
                github_token = os.getenv("GITHUB_TOKEN")
                
                if github_token:
                    print(f"⚠️  Using GITHUB_TOKEN from env (single-org mode)")
                else:
                    print(f"❌ No GitHub token available (multi-org or env)")
                    raise Exception(f"No GitHub token for user {user_id}")
            
            # Convert to webhook format
            payload = self.convert_to_webhook_payload(event)
            
            # Process using existing smart_processor
            # This is synchronous, so we run it in executor to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, 
                handle_push_event, 
                payload,
                github_token
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
    
    async def process_event_with_limit(self, event):
        """Process single event with concurrency limit"""
        async with self.semaphore:
            return await self.process_event(event)
    
    async def consume_batch(self):
        """
        Consume a batch of events
        
        Processes events concurrently (up to max_concurrent at a time)
        """
        try:
            # Get unprocessed events
            events = await self.bus.get_unprocessed_events(limit=self.batch_size)
            
            if not events:
                return 0
            
            print(f"\n🔄 Processing batch of {len(events)} events")
            
            # Process events concurrently with semaphore limit
            tasks = []
            for event in events:
                if not self.running:
                    print("⏸️  Consumer stopped, breaking batch")
                    break
                tasks.append(self.process_event_with_limit(event))
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes
            processed_count = sum(1 for r in results if r is True)
            
            return processed_count
            
        except Exception as e:
            print(f"❌ Error in consume_batch: {e}")
            import traceback
            traceback.print_exc()
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
