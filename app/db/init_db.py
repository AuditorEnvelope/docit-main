import asyncio
from sqlalchemy import text

from app.db.session import engine
from app.models.base import Base

async def init_models():
    """Initialize database tables (idempotent - safe to run multiple times)"""
    print("📊 Initializing database schema...")
    print("⏳ Connecting to database (this may take a moment if Neon is idle)...")
    try:
        # Add retry logic for Neon (it can be idle and needs time to wake up)
        max_retries = 3
        retry_delay = 3  # seconds
        
        for attempt in range(max_retries):
            try:
                async with engine.begin() as conn:
                    # Ensure connections operate in the public schema before creating objects
                    await conn.execute(text("SET search_path TO public"))

                    # Create all tables (idempotent - only creates if they don't exist)
                    await conn.run_sync(Base.metadata.create_all)

                    # Backfill docbook_repos schema for legacy databases (idempotent)
                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ADD COLUMN IF NOT EXISTS docbook_repo_id INTEGER
                            """
                        )
                    )

                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ADD COLUMN IF NOT EXISTS docbook_url VARCHAR(500)
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            UPDATE docbook_repos
                            SET docbook_url = ''
                            WHERE docbook_url IS NULL
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ALTER COLUMN docbook_url SET DEFAULT ''
                            """
                        )
                    )

                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ADD COLUMN IF NOT EXISTS staging_branch VARCHAR(100)
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            UPDATE docbook_repos
                            SET staging_branch = 'staging'
                            WHERE staging_branch IS NULL
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ALTER COLUMN staging_branch SET DEFAULT 'staging'
                            """
                        )
                    )

                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ADD COLUMN IF NOT EXISTS main_branch VARCHAR(100)
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            UPDATE docbook_repos
                            SET main_branch = 'main'
                            WHERE main_branch IS NULL
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ALTER COLUMN main_branch SET DEFAULT 'main'
                            """
                        )
                    )

                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ADD COLUMN IF NOT EXISTS auto_merge BOOLEAN
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            UPDATE docbook_repos
                            SET auto_merge = FALSE
                            WHERE auto_merge IS NULL
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ALTER COLUMN auto_merge SET DEFAULT FALSE
                            """
                        )
                    )

                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ADD COLUMN IF NOT EXISTS is_active BOOLEAN
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            UPDATE docbook_repos
                            SET is_active = TRUE
                            WHERE is_active IS NULL
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ALTER COLUMN is_active SET DEFAULT TRUE
                            """
                        )
                    )

                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ADD COLUMN IF NOT EXISTS last_published_at TIMESTAMP WITH TIME ZONE
                            """
                        )
                    )

                    # Ensure UUID columns use proper types
                    await conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                                IF EXISTS (
                                    SELECT 1 FROM information_schema.columns
                                    WHERE table_schema = 'public'
                                      AND table_name = 'docbook_repos'
                                      AND column_name = 'user_id'
                                      AND data_type <> 'uuid'
                                ) THEN
                                    ALTER TABLE docbook_repos
                                    ALTER COLUMN user_id TYPE UUID USING user_id::uuid;
                                END IF;
                            END
                            $$;
                            """
                        )
                    )

                    await conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                                IF EXISTS (
                                    SELECT 1 FROM information_schema.columns
                                    WHERE table_schema = 'public'
                                      AND table_name = 'docbook_reviews'
                                      AND column_name = 'user_id'
                                      AND data_type <> 'uuid'
                                ) THEN
                                    ALTER TABLE docbook_reviews
                                    ALTER COLUMN user_id TYPE UUID USING user_id::uuid;
                                END IF;
                            END
                            $$;
                            """
                        )
                    )

                    await conn.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                                IF EXISTS (
                                    SELECT 1 FROM information_schema.columns
                                    WHERE table_schema = 'public'
                                      AND table_name = 'docbook_reviews'
                                      AND column_name = 'approved_by'
                                      AND data_type <> 'uuid'
                                ) THEN
                                    ALTER TABLE docbook_reviews
                                    ALTER COLUMN approved_by TYPE UUID USING approved_by::uuid;
                                END IF;
                            END
                            $$;
                            """
                        )
                    )

                    await conn.execute(
                        text(
                            """
                            ALTER TABLE docbook_repos
                            ALTER COLUMN tracked_branch SET DEFAULT 'main'
                            """
                        )
                    )
                
                # Success - break out of retry loop
                break
                
            except (TimeoutError, asyncio.TimeoutError, asyncio.CancelledError) as e:
                if attempt < max_retries - 1:
                    print(f"⏳ Connection attempt {attempt + 1} failed (Neon may be waking up), retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"❌ All {max_retries} connection attempts failed")
                    raise

        print("✅ Database schema initialized!")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print("💡 Tip: Check your DATABASE_URL and ensure SSL is properly configured for Neon")
        print("💡 If using Neon, the database may need a moment to wake up from idle state")
        raise

if __name__ == "__main__":
    asyncio.run(init_models())
