"""
lekhak ai - Complete Integration
Connects all services: Commit Bus → Doc Generator → Indexer → Agent
"""

import os
import asyncio
from pathlib import Path
from typing import Dict
import tempfile
import shutil
from git import Repo

from core.commit_bus import CommitBusService
from processors.hierarchical_doc_generator import HierarchicalDocGenerator
from services.indexer_service import IndexerService
from services.agent_service import AgentService
from services.overlay_service import OverlayService
from services.subscription_service import SubscriptionService

class LekhakKiPipeline:
    """
    Complete lekhak ai Pipeline
    
    Flow:
    1. Receive commit event
    2. Clone repo at commit SHA
    3. Generate hierarchical docs
    4. Index in vector DB
    5. Generate changelog
    6. Store everything
    """
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.github_token = os.getenv("GITHUB_TOKEN")
        
        # Initialize services
        self.commit_bus = CommitBusService(self.db_url)
        self.indexer = IndexerService()
        self.overlay_service = OverlayService(self.db_url)
        self.subscription_service = SubscriptionService(self.db_url)
        
        print("🚀 lekhak ai Pipeline initialized")
    
    async def init(self):
        """Initialize all services"""
        await self.commit_bus.init_pool()
        self.indexer.connect()
        await self.overlay_service.init_db()
        await self.subscription_service.init_db()
        
        # Initialize agent
        self.agent = AgentService(self.indexer, self.db_url)
        await self.agent.init_db()
        
        print("✅ All services initialized")
    
    def clone_repo(self, repo_url: str, commit_sha: str) -> Path:
        """Clone repository at specific commit"""
        temp_dir = Path(tempfile.mkdtemp())
        
        print(f"📥 Cloning {repo_url} at {commit_sha[:8]}...")
        
        # Add GitHub token to URL if available
        if self.github_token and 'github.com' in repo_url:
            repo_url = repo_url.replace('https://', f'https://{self.github_token}@')
        
        # Clone
        repo = Repo.clone_from(repo_url, temp_dir)
        repo.git.checkout(commit_sha)
        
        print(f"✅ Cloned to {temp_dir}")
        return temp_dir
    
    async def process_commit(self, event: Dict):
        """
        Process a single commit event
        
        Complete flow from commit to indexed docs
        """
        repo_id = event['repo_id']
        commit_sha = event['commit_sha']
        
        print(f"\n{'='*60}")
        print(f"🔄 Processing commit: {commit_sha[:8]}")
        print(f"   Repo: {repo_id}")
        print(f"{'='*60}\n")
        
        try:
            # 1. Clone repository
            repo_url = f"https://github.com/{repo_id}.git"
            repo_dir = self.clone_repo(repo_url, commit_sha)
            
            # 2. Generate hierarchical documentation
            print(f"\n📊 Generating hierarchical documentation...")
            doc_generator = HierarchicalDocGenerator(
                repo_dir, repo_id, commit_sha, self.db_url
            )
            root_node = await doc_generator.generate()
            
            # 3. Index all nodes in vector DB
            print(f"\n🔍 Indexing in vector DB...")
            await self.index_tree(root_node)
            
            # 4. Generate changelog
            print(f"\n📝 Generating changelog...")
            await self.generate_changelog(event, root_node)
            
            # 5. Cleanup
            shutil.rmtree(repo_dir)
            
            print(f"\n✅ Successfully processed commit {commit_sha[:8]}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error processing commit: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def index_tree(self, node):
        """Recursively index all nodes in tree"""
        # Index current node
        node_dict = node.to_dict()
        await self.indexer.index_node(node_dict)
        
        # Index children
        for child in node.children:
            await self.index_tree(child)
    
    async def generate_changelog(self, event: Dict, root_node):
        """Generate changelog entry for commit"""
        # Analyze changes
        files_changed = event.get('files_changed', [])
        
        # Classify change type
        change_type = 'feature'  # Default
        if any('fix' in event['commit_message'].lower() for _ in [1]):
            change_type = 'bugfix'
        elif any('break' in event['commit_message'].lower() for _ in [1]):
            change_type = 'breaking'
        
        # Generate summary
        summary = event['commit_message'].split('\n')[0]  # First line
        
        # Store changelog
        async with self.commit_bus.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO changelogs (
                    repo_id, commit_sha, type, title, summary, details,
                    breaking, author_name, author_email, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (repo_id, commit_sha) DO NOTHING
            """,
                event['repo_id'], event['commit_sha'], change_type,
                summary[:500], summary, event['commit_message'],
                change_type == 'breaking',
                event.get('author_name'), event.get('author_email'),
                event['timestamp']
            )
        
        print(f"✅ Generated changelog entry")
    
    async def query(self, question: str, repo_id: str = None):
        """Query the agent"""
        return await self.agent.query(question, repo_id)
    
    async def get_merged_doc(self, node_id: str):
        """Get doc with overlays merged"""
        return await self.overlay_service.get_merged_doc(node_id)


# CLI for testing
if __name__ == "__main__":
    import sys
    
    async def main():
        pipeline = LekhakKiPipeline()
        await pipeline.init()
        
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "process":
                # Process a commit
                if len(sys.argv) < 4:
                    print("Usage: python lekhak_ai_integration.py process <repo_id> <commit_sha>")
                    return
                
                repo_id = sys.argv[2]
                commit_sha = sys.argv[3]
                
                # Create fake event
                event = {
                    'repo_id': repo_id,
                    'commit_sha': commit_sha,
                    'author_name': 'Test',
                    'author_email': 'test@example.com',
                    'timestamp': '2025-10-15T00:00:00Z',
                    'commit_message': 'Test commit',
                    'files_changed': []
                }
                
                success = await pipeline.process_commit(event)
                print(f"\n{'✅ Success' if success else '❌ Failed'}")
            
            elif command == "query":
                # Query agent
                if len(sys.argv) < 3:
                    print("Usage: python lekhak_ai_integration.py query 'Your question'")
                    return
                
                question = " ".join(sys.argv[2:])
                response = await pipeline.query(question)
                
                print(f"\n{'='*60}")
                print(f"💡 Answer:")
                print(f"{'='*60}")
                print(response.answer)
                print(f"\n📚 Sources: {len(response.sources)}")
            
            else:
                print(f"Unknown command: {command}")
                print("Available commands: process, query")
        else:
            print("lekhak ai Pipeline")
            print("Commands:")
            print("  process <repo_id> <commit_sha>  - Process a commit")
            print("  query '<question>'               - Query the agent")
    
    asyncio.run(main())
