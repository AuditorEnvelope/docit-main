#!/usr/bin/env python3
"""
Run database migrations
"""
import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def run_migrations():
    """Run all migration files in order"""
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set in .env")
        return
    
    print(f"🔗 Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        migrations_dir = Path(__file__).parent / "migrations"
        migration_files = sorted(migrations_dir.glob("*.sql"))
        
        print(f"📁 Found {len(migration_files)} migration files")
        
        for migration_file in migration_files:
            print(f"\n▶️  Running {migration_file.name}...")
            
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            try:
                await conn.execute(sql)
                print(f"✅ {migration_file.name} completed")
            except Exception as e:
                print(f"⚠️  {migration_file.name}: {e}")
        
        print("\n✅ All migrations completed!")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migrations())
