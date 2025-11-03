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
        Get GitHub token for user from database
        Prefers user's main token (most reliable), falls back to org-specific token
        
        Args:
            user_id: UUID of user
            token_id: UUID of token record (ignored - always use main token)
        
        Returns:
            GitHub token string or None if not found
        """
        try:
            async with self.pool.acquire() as conn:
                # Always prefer user's main GitHub token (most reliable)
                result = await conn.fetchval("""
                    SELECT github_access_token FROM users
                    WHERE id = $1
                """, user_id)
                
                if result:
                    return result
                
                # Fallback to org-specific token if main token not available
                if token_id and str(token_id) != '00000000-0000-0000-0000-000000000000':
                    result = await conn.fetchval("""
                        SELECT github_token FROM user_github_tokens
                        WHERE user_id = $1 AND token_id = $2 AND is_active = TRUE
                    """, user_id, token_id)
                    if result:
                        return result
                
                return None
        except Exception as e:
            print(f"⚠️  Error getting GitHub token: {e}")
            return None
    
    async def _get_repo_doc_persona(self, repo_full_name: str, user_id: Optional[str]) -> str:
        """
        Fetch doc_persona for a repository from database
        
        Args:
            repo_full_name: Repository full name (e.g., "org/repo")
            user_id: User UUID (optional, for multi-org lookup)
            
        Returns:
            Doc persona: "internal" or "developer" (defaults to "internal")
        """
        try:
            async with self.pool.acquire() as conn:
                # Try to find repo in repositories table
                result = await conn.fetchval("""
                    SELECT doc_persona FROM repositories
                    WHERE full_name = $1
                    LIMIT 1
                """, repo_full_name)
                
                if result:
                    print(f"✅ Found doc_persona in DB: {result}")
                    return result
                
                # Default to internal if not found
                print(f"⚠️  Doc persona not found for {repo_full_name}, using default: internal")
                return "internal"
                
        except Exception as e:
            print(f"⚠️  Error getting doc_persona: {e}")
            return "internal"  # Safe default
    
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
            if user_id:
                github_token = await self.get_github_token(user_id, token_id)
                
                if github_token:
                    print(f"✅ Got GitHub token for user {user_id} org {org_id}")
                else:
                    print(f"⚠️  No GitHub token found for user {user_id} org {org_id}")
            
            # IMPORTANT: Only fall back to env var if NO user context at all
            # This prevents using wrong token for multi-org repos
            if not github_token and not user_id:
                github_token = os.getenv("GITHUB_TOKEN")
                
                if github_token:
                    print(f"⚠️  Using GITHUB_TOKEN from env (legacy single-org mode)")
                else:
                    print(f"❌ No GitHub token available")
                    await self.bus.mark_failed(event_id, "No GitHub token available")
                    return False
            
            # If we have user_id but no token, this is a critical error
            if user_id and not github_token:
                error_msg = f"No valid GitHub token for user {user_id} org {org_id}"
                print(f"❌ {error_msg}")
                await self.bus.mark_failed(event_id, error_msg)
                return False
            
            # Convert to webhook format
            payload = self.convert_to_webhook_payload(event)
            
            # ⭐ NEW: Add user_id and db_pool to payload for docbook publisher
            payload['_user_id'] = user_id
            payload['_org_id'] = org_id
            payload['_db_pool'] = self.pool
            
            # ⭐ NEW: Fetch doc_persona for this repository
            doc_persona = await self._get_repo_doc_persona(event["repo_id"], user_id)
            print(f"📚 Doc Persona: {doc_persona}")
            
            # Process using existing smart_processor (NOW ASYNC!)
            # V4: Call async handle_push_event directly
            # This generates docs in a tmpdir
            await handle_push_event(
                payload,
                github_token,
                doc_persona  # ⭐ NEW: Pass doc_persona
            )
            
            # ⭐ NOTE: Docbook publishing now happens in smart_processor.push_to_docbook_v4()
            # It publishes BEFORE tmpdir is deleted, so docs are available
            print(f"✅ Documentation generated and auto-published to docbook/staging")
            print(f"   User can review & approve in Pending Reviews tab")
            
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
    
    async def get_orgs_with_activity(self) -> list:
        """
        Get all organizations that have been registered (for multi-org support)
        
        Returns: List of {user_id, org_id, github_token_id} dicts
        """
        try:
            async with self.pool.acquire() as conn:
                # Get all registered orgs with their first active token
                # This ensures we check newly registered orgs on startup
                rows = await conn.fetch("""
                    SELECT 
                        r.user_id, 
                        r.org_id,
                        COALESCE((
                            SELECT token_id FROM user_github_tokens 
                            WHERE user_id = r.user_id AND is_active = TRUE 
                            LIMIT 1
                        ), '00000000-0000-0000-0000-000000000000'::uuid) as github_token_id
                    FROM org_registrations r
                    GROUP BY r.user_id, r.org_id
                    ORDER BY r.org_id
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"⚠️  Error getting orgs with activity: {e}")
            return []
    
    async def get_org_repositories(self, github_token: str, org_id: str) -> list:
        """
        Get all repositories for an organization from GitHub
        Uses user/repos endpoint with org affiliation filter (same as frontend)
        
        Args:
            github_token: GitHub token for authentication
            org_id: Organization ID (e.g., "microsoft")
        
        Returns: List of repo full names (e.g., ["microsoft/vscode", "microsoft/typescript"])
        """
        try:
            import requests
            
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get all repos user has access to (including org repos)
            # This is the same method the frontend uses
            repos = []
            page = 1
            
            while True:
                url = "https://api.github.com/user/repos"
                params = {
                    "page": page,
                    "per_page": 100,
                    "affiliation": "owner,collaborator,organization_member",
                    "sort": "updated"
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 401:
                    print(f"⚠️  Unauthorized: GitHub token may be invalid or expired")
                    return []
                
                if response.status_code != 200:
                    print(f"⚠️  Error fetching repos: {response.status_code}")
                    return repos
                
                page_repos = response.json()
                if not page_repos:
                    break
                
                repos.extend([r["full_name"] for r in page_repos])
                page += 1
            
            # Filter repos by org_id (since we fetched all user repos)
            org_repos = [r for r in repos if r.startswith(f"{org_id}/")]
            return org_repos
        
        except Exception as e:
            print(f"⚠️  Error getting repos for {org_id}: {e}")
            return []
    
    async def get_last_processed_sha(self, repo_id: str) -> str:
        """Get the last processed commit SHA for a repo from database"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT last_processed_sha FROM repo_sync_state
                    WHERE repo_id = $1
                """, repo_id)
                return result
        except Exception as e:
            print(f"⚠️  Error getting last processed SHA for {repo_id}: {e}")
            return None
    
    async def update_repo_sync_state(self, repo_id: str, org_id: str, latest_sha: str):
        """Update repo sync state with latest commit SHA from GitHub"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO repo_sync_state (repo_id, org_id, latest_sha_on_github, last_checked_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (repo_id) DO UPDATE
                    SET latest_sha_on_github = $3, last_checked_at = NOW()
                """, repo_id, org_id, latest_sha)
        except Exception as e:
            print(f"⚠️  Error updating sync state for {repo_id}: {e}")
    
    async def mark_repo_processed(self, repo_id: str, org_id: str, processed_sha: str):
        """Mark a repo as processed up to a specific commit SHA"""
        try:
            async with self.pool.acquire() as conn:
                # Upsert: Insert if not exists, update if exists
                await conn.execute("""
                    INSERT INTO repo_sync_state (repo_id, org_id, last_processed_sha)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (repo_id) DO UPDATE
                    SET last_processed_sha = $3, updated_at = NOW()
                """, repo_id, org_id, processed_sha)
        except Exception as e:
            print(f"⚠️  Error marking repo as processed: {e}")
    
    async def check_missed_commits(self) -> int:
        """
        Check for missed commits on startup (MULTI-ORG SUPPORT)
        
        This queries GitHub for recent commits across ALL registered organizations
        and compares with our database to find any commits that were missed during downtime.
        
        FLOW:
        1. Get all organizations with activity from database
        2. For each org, get their GitHub token
        3. Get all repositories in that org
        4. For each repo, check GitHub for missed commits
        5. Store missed commits with proper org context
        """
        try:
            print("\n🔍 Checking for missed commits (MULTI-ORG)...")
            
            # Get unprocessed events from database
            stats = await self.bus.get_event_stats()
            
            if stats["pending"] > 0:
                print(f"📊 Found {stats['pending']} unprocessed events in database")
                print(f"   These will be processed automatically")
            
            # ================================================================
            # STEP 1: Get all organizations with activity
            # ================================================================
            
            orgs_with_activity = await self.get_orgs_with_activity()
            
            if not orgs_with_activity:
                print(f"⚠️  No organizations found in database")
                print(f"   Relying on GitHub webhook retries instead")
                return
            
            print(f"\n📋 Found {len(orgs_with_activity)} organization(s) with activity:")
            for org_context in orgs_with_activity:
                print(f"   - {org_context['org_id']}")
            
            # ================================================================
            # STEP 2: For each org, check for missed commits
            # ================================================================
            
            total_missed = 0
            
            for org_context in orgs_with_activity:
                user_id = org_context['user_id']
                org_id = org_context['org_id']
                token_id = org_context['github_token_id']
                
                print(f"\n{'='*60}")
                print(f"🔍 Checking org: {org_id}")
                print(f"{'='*60}")
                
                # Get GitHub token for this org
                github_token = await self.get_github_token(user_id, token_id)
                
                if not github_token:
                    print(f"⚠️  No GitHub token found for {org_id}")
                    print(f"   💡 Please register this organization with a valid GitHub token")
                    continue
                
                print(f"✅ Using GitHub token for {org_id}")
                
                # Get all repositories in this org
                print(f"📚 Fetching repositories for {org_id}...")
                repos = await self.get_org_repositories(github_token, org_id)
                
                if not repos:
                    print(f"⚠️  No repositories found for {org_id}")
                    continue
                
                print(f"✅ Found {len(repos)} repository(ies) in {org_id}")
                
                # Check each repository for missed commits (OPTIMIZED)
                try:
                    sync = GitHubSync(github_token)
                    
                    for repo_full_name in repos:
                        print(f"\n   📦 Checking {repo_full_name}...")
                        
                        try:
                            # OPTIMIZATION: Check if repo has changed since last check
                            last_processed_sha = await self.get_last_processed_sha(repo_full_name)
                            latest_sha = await sync.get_latest_commit_sha(repo_full_name)
                            
                            # If nothing changed, skip this repo
                            if last_processed_sha and last_processed_sha == latest_sha:
                                print(f"   ✅ No changes since {last_processed_sha[:8]}")
                                continue
                            
                            # Find missed commits for this repo
                            missed = await sync.find_missed_commits(repo_full_name, since_sha=last_processed_sha)
                            
                            if missed:
                                print(f"   🎯 Found {len(missed)} missed commit(s)")
                                
                                # Store each missed commit with org context
                                for event_dict in missed:
                                    try:
                                        # Add multi-org context
                                        # Only set user_id if it's not None
                                        if user_id:
                                            event_dict['user_id'] = str(user_id)
                                        else:
                                            event_dict['user_id'] = None
                                        
                                        event_dict['org_id'] = org_id
                                        
                                        # Only set token_id if it's valid (not zero UUID)
                                        if token_id and str(token_id) != '00000000-0000-0000-0000-000000000000':
                                            event_dict['github_token_id'] = str(token_id)
                                        else:
                                            event_dict['github_token_id'] = None
                                        
                                        # Convert to CommitEvent and store
                                        event = CommitEvent(**event_dict)
                                        await self.bus.store_event(event)
                                        
                                        print(f"      ✅ Stored: {event.commit_sha[:8]} ({repo_full_name})")
                                        total_missed += 1
                                    
                                    except Exception as e:
                                        print(f"      ⚠️  Failed to store {event_dict['commit_sha'][:8]}: {e}")
                                
                                # OPTIMIZATION: Mark repo as processed up to latest SHA
                                if missed and latest_sha:
                                    await self.mark_repo_processed(repo_full_name, org_id, latest_sha)
                            else:
                                print(f"   ✅ No missed commits")
                                # Even if no missed commits, update sync state with latest SHA
                                if latest_sha:
                                    await self.mark_repo_processed(repo_full_name, org_id, latest_sha)
                        
                        except Exception as e:
                            print(f"   ⚠️  Error checking {repo_full_name}: {e}")
                
                except Exception as e:
                    print(f"⚠️  Error syncing with GitHub for {org_id}: {e}")
            
            # ================================================================
            # SUMMARY
            # ================================================================
            
            if total_missed > 0:
                print(f"\n{'='*60}")
                print(f"🎉 Successfully recovered {total_missed} missed commit(s)!")
                print(f"   They will be processed automatically")
                print(f"{'='*60}")
            else:
                print(f"\n✅ No missed commits found across all organizations")
                print(f"   Last processed: {stats['processed']} events")
            
            # Display summary of all orgs and repos
            await self.display_org_summary()
        
        except Exception as e:
            print(f"❌ Error checking missed commits: {e}")
            import traceback
            traceback.print_exc()
    
    async def display_org_summary(self):
        """
        Display a clean CLI summary of all organizations and their repositories
        """
        try:
            orgs_with_activity = await self.get_orgs_with_activity()
            
            if not orgs_with_activity:
                return
            
            print(f"\n{'='*70}")
            print(f"📊 ORGANIZATION & REPOSITORY SUMMARY")
            print(f"{'='*70}")
            
            # Group repos by org
            org_repos = {}
            for org_context in orgs_with_activity:
                org_id = org_context['org_id']
                user_id = org_context['user_id']
                
                if org_id not in org_repos:
                    org_repos[org_id] = {'user_id': user_id, 'repos': []}
            
            # Fetch repos for each org
            for org_context in orgs_with_activity:
                user_id = org_context['user_id']
                org_id = org_context['org_id']
                
                # Get token
                github_token = await self.get_github_token(user_id, None)
                if not github_token:
                    github_token = os.getenv("GITHUB_TOKEN")
                
                if github_token:
                    repos = await self.get_org_repositories(github_token, org_id)
                    org_repos[org_id]['repos'] = repos
            
            # Display summary
            total_orgs = len(org_repos)
            total_repos = sum(len(org['repos']) for org in org_repos.values())
            
            print(f"\n🏢 Total Organizations: {total_orgs}")
            print(f"📦 Total Repositories: {total_repos}\n")
            
            for org_id, org_data in sorted(org_repos.items()):
                repos = org_data['repos']
                print(f"  🔷 {org_id}")
                print(f"     └─ Repositories: {len(repos)}")
                for repo in repos:
                    repo_name = repo.split('/')[-1]
                    print(f"        ├─ {repo_name}")
                print()
            
            print(f"{'='*70}\n")
        
        except Exception as e:
            print(f"⚠️  Error displaying org summary: {e}")
    
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
        
        # Process any pending events from startup immediately
        stats = await self.bus.get_event_stats()
        if stats["pending"] > 0:
            print(f"\n⚡ Processing {stats['pending']} pending events from startup...")
            startup_attempts = 0
            while stats["pending"] > 0 and startup_attempts < 5:
                startup_attempts += 1
                print(f"   Attempt {startup_attempts}: Processing batch...")
                processed = await self.consume_batch()
                print(f"   Processed {processed} events")
                if processed == 0:
                    print(f"   No events processed, breaking")
                    break
                stats = await self.bus.get_event_stats()
                print(f"   Stats after batch: {stats['pending']} pending")
            print(f"✅ Startup processing complete\n")
        
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
