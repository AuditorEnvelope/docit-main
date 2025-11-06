"""
GitHub App Installation Service
Stores which repos each GitHub App has access to in the database
"""

import asyncpg
from typing import List, Optional, Set
import json


class AppInstallationService:
    """
    Manages GitHub App installations and their accessible repositories
    
    When an app is installed, GitHub sends a webhook with the list of repos
    the app has access to. We store this in the database so we can query it
    later without needing to call GitHub API (which requires App JWT).
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def store_app_installation(
        self,
        org_id: str,
        app_id: int,
        installation_id: int,
        repository_selection: str,  # "all" or "selected"
        repositories: List[dict],  # List of repo dicts with id, name, full_name
        user_id: Optional[str] = None
    ) -> bool:
        """
        Store app installation and its accessible repositories
        
        Args:
            org_id: Organization ID
            app_id: GitHub App ID
            installation_id: GitHub Installation ID
            repository_selection: "all" or "selected"
            repositories: List of accessible repositories
            user_id: User who owns this installation
        
        Returns:
            True if successful
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Store installation record
                await conn.execute("""
                    INSERT INTO app_installations 
                    (org_id, app_id, installation_id, repository_selection, user_id, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (org_id, app_id) DO UPDATE SET
                        installation_id = $3,
                        repository_selection = $4,
                        updated_at = NOW()
                """, org_id, app_id, installation_id, repository_selection, user_id)
                
                # Clear old repo records for this app
                await conn.execute("""
                    DELETE FROM app_installation_repos
                    WHERE org_id = $1 AND app_id = $2
                """, org_id, app_id)
                
                # Store repo records
                for repo in repositories:
                    await conn.execute("""
                        INSERT INTO app_installation_repos
                        (org_id, app_id, repo_id, repo_name, repo_full_name, created_at)
                        VALUES ($1, $2, $3, $4, $5, NOW())
                    """, org_id, app_id, repo.get('id'), repo.get('name'), repo.get('full_name'))
                
                print(f"✅ Stored app installation: org={org_id}, app={app_id}, repos={len(repositories)}")
                return True
                
        except Exception as e:
            print(f"❌ Error storing app installation: {e}")
            return False
    
    async def get_app_accessible_repos(
        self,
        org_id: str,
        app_id: int
    ) -> Set[str]:
        """
        Get list of repos the app can access (from database)
        
        Args:
            org_id: Organization ID
            app_id: GitHub App ID
        
        Returns:
            Set of full repo names (e.g., {"org/repo1", "org/repo2"})
        """
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT repo_full_name
                    FROM app_installation_repos
                    WHERE org_id = $1 AND app_id = $2
                """, org_id, app_id)
                
                repos = {row['repo_full_name'] for row in rows}
                print(f"✅ Got {len(repos)} accessible repos for app {app_id} from DB")
                return repos
                
        except Exception as e:
            print(f"❌ Error getting app accessible repos: {e}")
            return set()
    
    async def get_app_installation_id(
        self,
        org_id: str,
        app_id: int
    ) -> Optional[int]:
        """
        Get installation ID for an app in an org
        
        Args:
            org_id: Organization ID
            app_id: GitHub App ID
        
        Returns:
            Installation ID or None
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT installation_id
                    FROM app_installations
                    WHERE org_id = $1 AND app_id = $2
                """, org_id, app_id)
                
                return row['installation_id'] if row else None
                
        except Exception as e:
            print(f"❌ Error getting app installation ID: {e}")
            return None
