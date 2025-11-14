"""
Event Consumer Worker

Background worker that processes events from the commit bus.
Runs independently from the main API server.

Usage:
    python -m app.worker
"""

import asyncio
import signal
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

import asyncpg
import httpx

from app.core.config import settings
from app.services.event.smart_processor import handle_push_event
from app.utils.github_sync import GitHubSync


class EventConsumerWorker:
    """
    Background worker that processes events from commit bus
    
    Architecture (like old codebase):
    1. Poll for unprocessed events (every 5 seconds)
    2. Process each event (call smart_processor directly)
    3. Mark as processed or failed
    4. Log processing attempts
    5. Uses asyncpg pool directly (no SQLAlchemy) to avoid greenlet_spawn errors
    """
    
    def __init__(self):
        self.is_running = False
        self.interval = settings.EVENT_PROCESSOR_INTERVAL_SECONDS
        self.batch_size = settings.MAX_EVENTS_PER_BATCH
        self.pool = None  # asyncpg pool (like old codebase)
        self.db_url = None
        
    async def init(self):
        """Initialize database connections (like old codebase)"""
        # Convert SQLAlchemy URL to asyncpg format
        self.db_url = settings.DATABASE_URL
        if self.db_url.startswith("postgresql+asyncpg://"):
            self.db_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
        elif self.db_url.startswith("postgresql://"):
            pass  # Already correct
        else:
            print(f"⚠️  Unexpected database URL format: {self.db_url}")
            return
        
        async def _set_search_path(conn):
            await conn.execute("SET search_path TO public")

        self.pool = await asyncpg.create_pool(
            self.db_url,
            min_size=2,
            max_size=10,
            init=_set_search_path
        )
        print("✅ Event Consumer initialized")
        print(f"   Batch size: {self.batch_size}")
        print(f"   Poll interval: {self.interval}s")
        
        # Check for missed commits on startup (like old codebase)
        await self.check_missed_commits()
    
    async def get_unprocessed_events(self, limit: int = 100) -> List[dict]:
        """Get unprocessed events using asyncpg pool (like old codebase)"""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    event_id, repo_id, commit_sha, parent_sha, author_name,
                    author_email, timestamp, branch, files_changed, commit_message,
                    push_id, source, metadata, created_at,
                    user_id, org_id, github_token_id, installation_id
                FROM commit_events
                WHERE processed = FALSE
                ORDER BY timestamp ASC
                LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            return [dict(row) for row in rows]
    
    async def mark_processed(self, event_id: str, success: bool = True, error: str = None):
        """Mark event as processed using asyncpg pool (like old codebase)"""
        async with self.pool.acquire() as conn:
            if success:
                await conn.execute("""
                    UPDATE commit_events
                    SET processed = TRUE, processed_at = NOW()
                    WHERE event_id = $1
                """, event_id)
            else:
                await conn.execute("""
                    UPDATE commit_events
                    SET processed = TRUE, processed_at = NOW(), 
                        metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{error}',
                            to_jsonb($2::text)
                        )
                    WHERE event_id = $1
                """, event_id, error)
    
    async def get_event_stats(self) -> dict:
        """Get statistics about events using asyncpg pool (like old codebase)"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE processed = TRUE) as processed,
                    COUNT(*) FILTER (WHERE processed = FALSE) as pending
                FROM commit_events
            """)
            return dict(row)
    
    def convert_to_webhook_payload(self, event: dict) -> dict:
        """
        Convert event store format to webhook payload format (like old codebase)
        """
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
                "timestamp": event["timestamp"].isoformat() if hasattr(event["timestamp"], 'isoformat') else str(event["timestamp"]),
                "author": {
                    "name": event["author_name"],
                    "email": event["author_email"]
                },
                "added": [f["path"] for f in files_changed if f.get("status") == "added"],
                "modified": [f["path"] for f in files_changed if f.get("status") == "modified"],
                "removed": [f["path"] for f in files_changed if f.get("status") == "deleted"]
            }],
            "ref": f"refs/heads/{event['branch']}",
            "after": event["commit_sha"],
            "before": event["parent_sha"][0] if event.get("parent_sha") and len(event.get("parent_sha", [])) > 0 else None
        }
        
        # Add installation if available (for GitHub App)
        if event.get("installation_id"):
            payload["installation"] = {"id": event["installation_id"]}
        
        return payload
    
    async def get_github_token(self, user_id: str, token_id: Optional[str] = None) -> Optional[str]:
        """
        Get GitHub token for user from database using asyncpg pool (like old codebase)
        Prefers user's main token (most reliable), falls back to org-specific token
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
                if token_id and token_id != '00000000-0000-0000-0000-000000000000':
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
        Fetch doc_persona for a repository from database using asyncpg pool (like old codebase)
        """
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT doc_persona FROM repositories
                    WHERE full_name = $1 OR repo_id = $1
                    LIMIT 1
                """, repo_full_name)
                
                if result:
                    # Handle enum or string
                    if hasattr(result, 'value'):
                        return result.value
                    return str(result) if result else "internal"
                
                # Default to internal if not found
                return "internal"
                
        except Exception as e:
            print(f"⚠️  Error getting doc_persona: {e}")
            return "internal"  # Safe default
    
    async def process_event(self, event: dict) -> bool:
        """
        Process a single event (like old codebase)
        
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

            repo_id = event.get("repo_id", "") or ""
            commit_message = event.get("commit_message", "") or ""

            # Skip commits generated by docbook writer to prevent processing loops
            if "pustak-docbook" in repo_id or commit_message.lower().startswith("docs: auto-generated documentation"):
                print("⚠️  Skipping docbook publication commit to avoid feedback loop")
                await self.mark_processed(event_id, success=True)
                return True

            # Extract context (multi-org mode)
            user_id = event.get("user_id")
            org_id = event.get("org_id")
            token_id = event.get("github_token_id")
            installation_id = event.get("installation_id")  # GitHub App installation ID
            
            # Get GitHub token (like old codebase)
            github_token = None
            
            # Try multi-org mode first (get user token from database)
            if user_id:
                github_token = await self.get_github_token(user_id, token_id)
                
                if github_token:
                    print(f"✅ Got GitHub token for user {user_id} org {org_id}")
            
            # If no user token, try GitHub App installation token (like old codebase)
            if not github_token and installation_id:
                try:
                    from app.utils.github_dual_app import GitHubDualAppHelper
                    dual_app = GitHubDualAppHelper()
                    github_token = await dual_app.get_reader_token(installation_id)
                    if github_token:
                        print(f"✅ Using GitHub App installation token (Reader) for installation {installation_id}")
                except Exception as e:
                    print(f"⚠️  Failed to get GitHub App token: {e}")
            
            
            if not github_token:
                error_msg = f"No GitHub token available (user_id={user_id}, installation_id={installation_id})"
                print(f"❌ {error_msg}")
                await self.mark_processed(event_id, success=False, error=error_msg)
                return False
            
            # Convert to webhook format
            payload = self.convert_to_webhook_payload(event)
            
            # ⭐ Add user_id and db_pool to payload for docbook publisher (like old codebase)
            payload['_user_id'] = user_id
            payload['_org_id'] = org_id
            payload['_db_pool'] = self.pool  # Pass asyncpg pool (like old codebase)
            
            # ⭐ Fetch doc_persona for this repository (like old codebase)
            doc_persona = await self._get_repo_doc_persona(event["repo_id"], user_id)
            print(f"📚 Doc Persona: {doc_persona}")
            
            # Process using smart_processor directly (like old codebase)
            # This generates docs and publishes to docbook
            await handle_push_event(
                payload,
                github_token=github_token,
                doc_persona=doc_persona
            )
            
            print(f"✅ Documentation generated and auto-published to docbook/staging")
            print(f"   User can review & approve in Pending Reviews tab")
            
            # Mark as processed
            await self.mark_processed(event_id, success=True)
            
            print(f"✅ Event {event_id} processed successfully")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error processing event {event_id}: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # Mark as failed
            await self.mark_processed(event_id, success=False, error=error_msg)
            
            return False
    
    async def consume_batch(self):
        """
        Consume a batch of events (like old codebase)
        Processes events one at a time
        """
        try:
            # Get unprocessed events
            events = await self.get_unprocessed_events(limit=self.batch_size)
            
            if not events:
                return 0
            
            print(f"\n🔄 Processing batch of {len(events)} events")
            
            # Process events one at a time (like old codebase)
            processed_count = 0
            for event in events:
                if not self.is_running:
                    print("⏸️  Consumer stopped, breaking batch")
                    break
                
                success = await self.process_event(event)
                if success:
                    processed_count += 1
            
            return processed_count
            
        except Exception as e:
            print(f"❌ Error in consume_batch: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    async def get_orgs_with_activity(self) -> List[Dict[str, Any]]:
        """
        Get all organizations that have been registered (for multi-org support)
        Returns: List of {user_id, org_id, github_token_id} dicts (like old codebase)
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        r.user_id, 
                        r.org_id,
                        COALESCE((
                            SELECT token_id::text FROM user_github_tokens 
                            WHERE user_id = r.user_id AND is_active = TRUE 
                            LIMIT 1
                        ), '00000000-0000-0000-0000-000000000000') as github_token_id
                    FROM org_registrations r
                    GROUP BY r.user_id, r.org_id
                    ORDER BY r.org_id
                """)
                return [
                    {
                        "user_id": str(row['user_id']),
                        "org_id": row['org_id'],
                        "github_token_id": row['github_token_id'] if row['github_token_id'] != '00000000-0000-0000-0000-000000000000' else None
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"⚠️  Error getting orgs with activity: {e}")
            return []
    
    async def get_org_repositories(self, github_token: str, org_id: str) -> List[str]:
        """
        Get all repositories for an organization from GitHub (like old codebase)
        Uses user/repos endpoint with org affiliation filter
        """
        try:
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get all repos user has access to (including org repos)
            repos = []
            page = 1
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                while True:
                    url = "https://api.github.com/user/repos"
                    params = {
                        "page": page,
                        "per_page": 100,
                        "affiliation": "owner,collaborator,organization_member",
                        "sort": "updated"
                    }
                    
                    response = await client.get(url, headers=headers, params=params)
                    
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
    
    async def get_last_processed_sha(self, repo_id: str) -> Optional[str]:
        """Get the last processed commit SHA for a repo from database (like old codebase)"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT last_processed_sha FROM repo_sync_state
                    WHERE repo_id = $1
                """, repo_id)
                return result
        except Exception as e:
            return None
    
    async def mark_repo_processed(self, repo_id: str, org_id: str, processed_sha: str):
        """Mark a repo as processed up to a specific commit SHA (like old codebase)"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO repo_sync_state (repo_id, org_id, last_processed_sha)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (repo_id) DO UPDATE
                    SET last_processed_sha = $3, updated_at = NOW()
                """, repo_id, org_id, processed_sha)
        except Exception as e:
            pass  # Non-critical
    
    async def check_missed_commits(self) -> int:
        """
        Check for missed commits on startup (MULTI-ORG SUPPORT) - like old codebase
        This queries GitHub for recent commits across ALL registered organizations
        and compares with our database to find any commits that were missed during downtime.
        """
        try:
            print("\n🔍 Checking for missed commits (MULTI-ORG)...")
            
            # Get unprocessed events from database
            stats = await self.get_event_stats()
            
            if stats["pending"] > 0:
                print(f"📊 Found {stats['pending']} unprocessed events in database")
                print(f"   These will be processed automatically")
            
            # STEP 1: Get all organizations with activity
            orgs_with_activity = await self.get_orgs_with_activity()
            
            if not orgs_with_activity:
                print(f"⚠️  No organizations found in database")
                print(f"   Relying on GitHub webhook retries instead")
                return 0
            
            print(f"\n📋 Found {len(orgs_with_activity)} organization(s) with activity:")
            for org_context in orgs_with_activity:
                print(f"   - {org_context['org_id']}")
            
            # STEP 2: For each org, check for missed commits
            total_missed = 0
            
            for org_context in orgs_with_activity:
                user_id = org_context['user_id']
                org_id = org_context['org_id']
                token_id = org_context.get('github_token_id')
                
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
                                async with self.pool.acquire() as conn:
                                    for event_dict in missed:
                                        try:
                                            # Add multi-org context (like old codebase)
                                            if user_id:
                                                event_dict['user_id'] = user_id
                                            else:
                                                event_dict['user_id'] = None
                                            
                                            event_dict['org_id'] = org_id
                                            
                                            # Only set token_id if it's valid (not zero UUID)
                                            if token_id and token_id != '00000000-0000-0000-0000-000000000000':
                                                event_dict['github_token_id'] = token_id
                                            else:
                                                event_dict['github_token_id'] = None
                                            
                                            # Store event in commit bus using asyncpg
                                            parent_shas = event_dict.get("parent_sha", []) or []
                                            if isinstance(parent_shas, str):
                                                parent_shas = [parent_shas]
                                            
                                            metadata_payload = event_dict.get("metadata", {}) or {}
                                            
                                            await conn.execute("""
                                                INSERT INTO commit_events (
                                                    repo_id, commit_sha, parent_sha, author_name, author_email,
                                                    timestamp, branch, files_changed, commit_message, push_id,
                                                    source, metadata, user_id, org_id, github_token_id, installation_id, processed
                                                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, FALSE)
                                                ON CONFLICT (repo_id, commit_sha) DO UPDATE
                                                SET metadata = EXCLUDED.metadata, updated_at = NOW()
                                            """,
                                                event_dict.get("repo_id"),
                                                event_dict.get("commit_sha"),
                                                parent_shas,
                                                event_dict.get("author_name"),
                                                event_dict.get("author_email"),
                                                event_dict.get("timestamp"),
                                                event_dict.get("branch"),
                                                json.dumps(event_dict.get("files_changed", [])),
                                                event_dict.get("commit_message"),
                                                event_dict.get("push_id"),
                                                event_dict.get("source", "github_sync"),
                                                json.dumps(metadata_payload),
                                                event_dict.get("user_id"),
                                                event_dict.get("org_id"),
                                                event_dict.get("github_token_id"),
                                                event_dict.get("installation_id")
                                            )
                                            
                                            print(f"      ✅ Stored: {event_dict['commit_sha'][:8]} ({repo_full_name})")
                                            total_missed += 1
                                        
                                        except Exception as e:
                                            print(f"      ⚠️  Failed to store {event_dict.get('commit_sha', 'unknown')[:8]}: {e}")
                                
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
            
            # SUMMARY
            if total_missed > 0:
                print(f"\n{'='*60}")
                print(f"🎉 Successfully recovered {total_missed} missed commit(s)!")
                print(f"   They will be processed automatically")
                print(f"{'='*60}")
            else:
                print(f"\n✅ No missed commits found across all organizations")
                print(f"   Last processed: {stats.get('processed', 0)} events")
            
            return total_missed
        
        except Exception as e:
            print(f"❌ Error checking missed commits: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    async def display_org_summary(self):
        """Display registered organizations (like old codebase)"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT DISTINCT org_id, user_id 
                    FROM org_registrations 
                    ORDER BY org_id
                """)
                
                if not rows:
                    print("⚠️  No registered organizations found")
                    return
                
                print(f"\n{'='*70}")
                print(f"🏢 REGISTERED ORGANIZATIONS & REPOSITORIES")
                print(f"{'='*70}")
                
                for row in rows:
                    print(f"\n  🔷 {row['org_id']}")
                    print(f"     └─ User ID: {row['user_id']}")
                
                print(f"\n📊 Summary: {len(rows)} organization(s) registered")
                print(f"{'='*70}\n")
            
        except Exception as e:
            print(f"⚠️  Could not display org summary: {e}")
    
    async def run(self):
        """
        Main consumer loop (like old codebase)
        Continuously polls for events and processes them
        """
        self.is_running = True
        print(f"\n🚀 Event Consumer started")
        print(f"   Batch size: {self.batch_size}")
        print(f"   Poll interval: {self.interval}s")
        print(f"   Database: {self.db_url.split('@')[-1] if '@' in self.db_url else 'local'}")
        print(f"\n{'='*60}\n")
        
        # Display org summary on startup
        await self.display_org_summary()
        
        # Process any pending events from startup immediately
        stats = await self.get_event_stats()
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
                stats = await self.get_event_stats()
                print(f"   Stats after batch: {stats['pending']} pending")
            print(f"✅ Startup processing complete\n")
        
        while self.is_running:
            try:
                # Get stats
                stats = await self.get_event_stats()
                
                if stats["pending"] > 0:
                    print(f"\n📊 Stats: {stats['pending']} pending, {stats['processed']} processed")
                    
                    # Process batch
                    processed = await self.consume_batch()
                    
                    if processed > 0:
                        print(f"✅ Processed {processed} events in this batch")
                    else:
                    # No events, wait longer
                        print(".", end="", flush=True)
                
                # Wait before next poll
                await asyncio.sleep(self.interval)
                
            except KeyboardInterrupt:
                print("\n⏹️  Received interrupt signal")
                break
            except Exception as e:
                print(f"\n❌ Error in consumer loop: {e}")
                # Wait before retrying
                await asyncio.sleep(self.interval * 2)
        
        print("\n👋 Event Consumer stopped")
    
    async def stop(self):
        """Graceful shutdown (like old codebase)"""
        print("\n⏹️  Stopping consumer...")
        self.is_running = False
        
        if self.pool:
            await self.pool.close()
        
        print("✅ Consumer stopped gracefully")


async def main():
    """Main entry point (like old codebase)"""
    worker = EventConsumerWorker()
    
    # Handle shutdown signals (like old codebase)
    def signal_handler(signum, frame):
        print(f"\n⚠️  Received signal {signum}")
        worker.is_running = False  # Signal handler sets flag, run() loop will exit
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize and run worker
    try:
        await worker.init()
        await worker.run()
    except KeyboardInterrupt:
        pass
    finally:
        await worker.stop()


if __name__ == "__main__":
    """
    Run the event consumer worker
    
    Usage:
        python -m app.worker
    """
    
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║           🔄 Pustak AI Event Consumer Worker            ║
║                                                          ║
║  Processes commit events from the commit bus             ║
║  Generates documentation in the background               ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
