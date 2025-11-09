"""
Event Consumer Worker

Background worker that processes events from the commit bus.
Runs independently from the main API server.

Usage:
    python -m app.worker
"""

import asyncio
import logging
import signal
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session
from app.services.commit_bus import CommitBusService
from app.services.event.processor import EventProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EventConsumerWorker:
    """
    Background worker that processes events from commit bus
    """
    
    def __init__(self):
        self.is_running = False
        self.interval = settings.EVENT_PROCESSOR_INTERVAL_SECONDS
        self.batch_size = settings.MAX_EVENTS_PER_BATCH
        
    async def process_batch(self, db: AsyncSession) -> int:
        """Process a batch of unprocessed events"""
        try:
            # Get unprocessed events
            commit_bus = CommitBusService(db)
            events = await commit_bus.get_unprocessed_events(limit=self.batch_size)
            
            if not events:
                return 0
            
            logger.info(f"📦 Processing {len(events)} events...")
            
            processor = EventProcessor(db)
            processed_count = 0

            for event in events:
                try:
                    logger.info(
                        "  ⚙️  Processing event %s - %s@%s",
                        event.event_id,
                        event.repo_id,
                        event.commit_sha[:8],
                    )

                    # Convert commit bus event into a pseudo webhook payload
                    payload = self._commit_event_to_payload(event)

                    success = await processor._handle_push(
                        type("CommitEventWrapper", (), {"payload": payload})
                    )

                    if success:
                        await commit_bus.mark_processed(event.event_id)
                        processed_count += 1
                        logger.info("  ✅ Event %s processed successfully", event.event_id)
                    else:
                        logger.warning("  ⚠️ Event %s not processed", event.event_id)

                except Exception as e:
                    logger.error(f"  ❌ Failed to process event {event.event_id}: {e}", exc_info=True)
                    continue
            
            logger.info(f"✅ Batch complete: {processed_count}/{len(events)} events processed")
            return processed_count
            
        except Exception as e:
            logger.error(f"❌ Batch processing error: {e}")
            return 0
    
    def _commit_event_to_payload(self, event) -> Dict[str, Any]:
        return {
            "repository": {
                "full_name": event.repo_id,
            },
            "after": event.commit_sha,
            "head_commit": {"message": event.commit_message},
            "installation": {"id": event.installation_id} if event.installation_id else {},
            "_user_id": event.user_id,
        }

    async def display_org_summary(self, db: AsyncSession):
        """Display registered organizations and repositories"""
        try:
            from sqlalchemy import text
            
            # Query registered orgs from org_registrations table
            result = await db.execute(text("""
                SELECT DISTINCT org_id, user_id 
                FROM org_registrations 
                ORDER BY org_id
            """))
            orgs = result.fetchall()
            
            if not orgs:
                logger.info("⚠️  No registered organizations found")
                return
            
            logger.info(f"\n{'='*70}")
            logger.info(f"🏢 REGISTERED ORGANIZATIONS & REPOSITORIES")
            logger.info(f"{'='*70}")
            
            total_repos = 0
            for org_id, user_id in orgs:
                logger.info(f"\n  🔷 {org_id}")
                logger.info(f"     └─ User ID: {user_id}")
                total_repos += 1
            
            logger.info(f"\n📊 Summary: {len(orgs)} organization(s) registered")
            logger.info(f"{'='*70}\n")
            
        except Exception as e:
            logger.warning(f"⚠️  Could not display org summary: {e}")
    
    async def run_forever(self):
        """Run the worker continuously"""
        self.is_running = True
        logger.info("🚀 Event consumer worker started")
        logger.info(f"⏰ Processing interval: {self.interval} seconds")
        logger.info(f"📊 Batch size: {self.batch_size} events")
        
        # Display org summary on startup
        try:
            async with async_session() as db:
                await self.display_org_summary(db)
        except Exception as e:
            logger.warning(f"⚠️  Could not display initial org summary: {e}")
        
        iteration = 0
        
        while self.is_running:
            iteration += 1
            try:
                logger.info(f"\n{'='*70}")
                logger.info(f"🔄 Iteration {iteration} - {datetime.utcnow().isoformat()}")
                logger.info(f"{'='*70}")
                
                # Create DB session
                async with async_session() as db:
                    # Get stats
                    commit_bus = CommitBusService(db)
                    stats = await commit_bus.get_stats()
                    
                    # Display beautiful stats
                    logger.info(f"\n📊 EVENT STATISTICS:")
                    logger.info(f"   Total Events: {stats.get('total_events', 0)}")
                    logger.info(f"   Processed: {stats.get('processed_events', 0)}")
                    logger.info(f"   Pending: {stats.get('pending_events', 0)}")
                    logger.info(f"   Processing Rate: {stats.get('processing_rate', 'N/A')}")
                    
                    # Process batch
                    if stats.get('pending_events', 0) > 0:
                        logger.info(f"\n🔄 Processing batch of {stats['pending_events']} events...")
                        processed = await self.process_batch(db)
                        logger.info(f"✅ Processed {processed} events in this iteration")
                    else:
                        logger.info("💤 No pending events, sleeping...")
                
                # Wait before next iteration
                await asyncio.sleep(self.interval)
                
            except KeyboardInterrupt:
                logger.info("\n⚠️  Received interrupt signal, shutting down...")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"❌ Worker error: {e}", exc_info=True)
                logger.info(f"⏳ Waiting {self.interval} seconds before retry...")
                await asyncio.sleep(self.interval)
        
        logger.info("👋 Event consumer worker stopped")
    
    def stop(self):
        """Stop the worker gracefully"""
        logger.info("🛑 Stopping worker...")
        self.is_running = False


async def main():
    """Main entry point"""
    worker = EventConsumerWorker()
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"\n⚠️  Received signal {signum}")
        worker.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run worker
    try:
        await worker.run_forever()
    except Exception as e:
        logger.error(f"❌ Worker crashed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    """
    Run the event consumer worker
    
    Usage:
        python -m app.worker
    
    or with custom settings:
        EVENT_PROCESSOR_INTERVAL_SECONDS=30 python -m app.worker
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
    
    exit_code = asyncio.run(main())
    exit(exit_code)
