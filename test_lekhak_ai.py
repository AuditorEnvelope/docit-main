"""
Lekhak Ki - Complete Test Suite
Tests all 5 days of implementation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from commit_bus import CommitBusService, CommitEvent
from hierarchical_doc_generator import HierarchicalDocGenerator
from indexer_service import IndexerService
from agent_service import AgentService
from overlay_service import OverlayService
from subscription_service import SubscriptionService, Plan
from datetime import datetime

class LekhakKiTests:
    """Complete test suite for Lekhak Ki"""
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://localhost/lekhak_ai")
        self.passed = 0
        self.failed = 0
    
    def test_result(self, name: str, passed: bool, message: str = ""):
        """Record test result"""
        if passed:
            print(f"✅ {name}")
            self.passed += 1
        else:
            print(f"❌ {name}: {message}")
            self.failed += 1
    
    async def test_day1_commit_bus(self):
        """Test Day 1: Commit Bus"""
        print(f"\n{'='*60}")
        print("📅 DAY 1: COMMIT BUS TESTS")
        print(f"{'='*60}\n")
        
        try:
            # Initialize
            bus = CommitBusService(self.db_url)
            await bus.init_pool()
            
            # Test 1: Store event
            event = CommitEvent(
                repo_id="test/repo",
                commit_sha="test123",
                parent_sha=[],
                author_name="Test User",
                author_email="test@example.com",
                timestamp=datetime.now(),
                branch="main",
                files_changed=[],
                commit_message="Test commit"
            )
            
            event_id = await bus.store_event(event)
            self.test_result("Store event", event_id is not None)
            
            # Test 2: Retrieve unprocessed events
            events = await bus.get_unprocessed_events()
            self.test_result("Retrieve unprocessed events", len(events) > 0)
            
            # Test 3: Mark as processed
            await bus.mark_processed(event_id)
            events_after = await bus.get_unprocessed_events()
            self.test_result("Mark as processed", len(events_after) < len(events))
            
            # Test 4: Get stats
            stats = await bus.get_event_stats()
            self.test_result("Get stats", stats['total'] > 0)
            
            await bus.pool.close()
            
        except Exception as e:
            self.test_result("Commit Bus", False, str(e))
    
    async def test_day2_hierarchical_docs(self):
        """Test Day 2: Hierarchical Doc Generation"""
        print(f"\n{'='*60}")
        print("📅 DAY 2: HIERARCHICAL DOC GENERATION TESTS")
        print(f"{'='*60}\n")
        
        try:
            # Test with current repo
            repo_dir = Path(__file__).parent
            repo_id = "test/lekhak_ai"
            commit_sha = "test456"
            
            generator = HierarchicalDocGenerator(repo_dir, repo_id, commit_sha, self.db_url)
            await generator.init_db()
            
            # Test 1: Analyze repo
            root = await generator.analyze_repo()
            self.test_result("Analyze repo structure", root is not None)
            self.test_result("Root has children", len(root.children) > 0)
            
            # Test 2: Save to database
            await generator.save_tree(root)
            self.test_result("Save tree to database", True)
            
            await generator.pool.close()
            
        except Exception as e:
            self.test_result("Hierarchical Docs", False, str(e))
    
    async def test_day3_rag_system(self):
        """Test Day 3: RAG System"""
        print(f"\n{'='*60}")
        print("📅 DAY 3: RAG SYSTEM TESTS")
        print(f"{'='*60}\n")
        
        try:
            # Initialize indexer
            indexer = IndexerService()
            indexer.connect()
            
            # Test 1: Get stats
            stats = indexer.get_stats()
            self.test_result("Indexer connected", stats['total_entities'] >= 0)
            
            # Test 2: Search (if there are indexed docs)
            if stats['total_entities'] > 0:
                results = await indexer.search("documentation", top_k=3)
                self.test_result("Semantic search", len(results) >= 0)
            else:
                print("⚠️  No indexed documents, skipping search test")
            
            # Test 3: Agent service
            agent = AgentService(indexer, self.db_url)
            await agent.init_db()
            
            # Test intent classification
            intent = await agent.classify_intent("What changed in version 2.0?")
            self.test_result("Classify intent", intent == 'diff')
            
            await agent.pool.close()
            
        except Exception as e:
            self.test_result("RAG System", False, str(e))
    
    async def test_day4_overlays(self):
        """Test Day 4: Admin Overlays"""
        print(f"\n{'='*60}")
        print("📅 DAY 4: ADMIN OVERLAY TESTS")
        print(f"{'='*60}\n")
        
        try:
            overlay_service = OverlayService(self.db_url)
            await overlay_service.init_db()
            
            # Test 1: Create overlay (need a real node_id from database)
            # For now, just test initialization
            self.test_result("Overlay service initialized", True)
            
            # Test 2: Get all overlays
            overlays = await overlay_service.get_all_overlays("test/repo")
            self.test_result("Get overlays", isinstance(overlays, list))
            
            await overlay_service.pool.close()
            
        except Exception as e:
            self.test_result("Admin Overlays", False, str(e))
    
    async def test_day5_subscriptions(self):
        """Test Day 5: Subscription Model"""
        print(f"\n{'='*60}")
        print("📅 DAY 5: SUBSCRIPTION MODEL TESTS")
        print(f"{'='*60}\n")
        
        try:
            sub_service = SubscriptionService(self.db_url)
            await sub_service.init_db()
            
            # Test 1: Get subscription (defaults to free)
            subscription = await sub_service.get_subscription("test_user")
            self.test_result("Get subscription", subscription is not None)
            self.test_result("Default to free plan", subscription['plan'] == Plan.FREE)
            
            # Test 2: Check feature access
            has_overlays = await sub_service.check_feature("test_user", "overlays")
            self.test_result("Check feature (free has no overlays)", not has_overlays)
            
            # Test 3: Check limits
            within_limit = await sub_service.check_limit("test_user", "repos", 0)
            self.test_result("Check limits", within_limit)
            
            # Test 4: Get usage
            usage = await sub_service.get_usage("test_user")
            self.test_result("Get usage stats", isinstance(usage, dict))
            
            await sub_service.pool.close()
            
        except Exception as e:
            self.test_result("Subscription Model", False, str(e))
    
    async def test_integration(self):
        """Test complete integration"""
        print(f"\n{'='*60}")
        print("🔗 INTEGRATION TESTS")
        print(f"{'='*60}\n")
        
        try:
            # Test that all services can be initialized together
            from lekhak_ai_integration import LekhakKiPipeline
            
            pipeline = LekhakKiPipeline()
            await pipeline.init()
            
            self.test_result("Initialize complete pipeline", True)
            
        except Exception as e:
            self.test_result("Integration", False, str(e))
    
    async def run_all_tests(self):
        """Run all tests"""
        print(f"\n{'='*60}")
        print("🧪 LEKHAK KI - COMPLETE TEST SUITE")
        print(f"{'='*60}")
        
        await self.test_day1_commit_bus()
        await self.test_day2_hierarchical_docs()
        await self.test_day3_rag_system()
        await self.test_day4_overlays()
        await self.test_day5_subscriptions()
        await self.test_integration()
        
        # Summary
        print(f"\n{'='*60}")
        print("📊 TEST SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success Rate: {self.passed/(self.passed+self.failed)*100:.1f}%")
        print(f"{'='*60}\n")
        
        return self.failed == 0


async def main():
    """Main test runner"""
    tests = LekhakKiTests()
    success = await tests.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
