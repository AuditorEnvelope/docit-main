"""
GitHub Sync - Fetch missed commits from GitHub
Ensures no commits are lost by comparing GitHub with our database
"""

import os
import requests
from typing import List, Dict, Optional
from datetime import datetime
from dateutil import parser as date_parser
from dotenv import load_dotenv

load_dotenv()


class GitHubSync:
    """
    Syncs with GitHub to find missed commits
    
    On startup, compares GitHub's commit history with our database
    to find any commits that were missed during downtime.
    """
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def get_latest_commit_sha(self, repo: str) -> Optional[str]:
        """
        Get the latest commit SHA for a repo (OPTIMIZATION)
        
        This is a lightweight check that only fetches the latest commit
        to compare with our cached version. Much faster than fetching 50 commits.
        
        Args:
            repo: Repository in format "owner/repo"
        
        Returns:
            Latest commit SHA or None if error
        """
        url = f"{self.base_url}/repos/{repo}/commits"
        params = {"per_page": 1}  # Only get 1 commit
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                commits = response.json()
                if commits:
                    return commits[0].get("sha")
            
            return None
        except Exception as e:
            print(f"⚠️  Error getting latest commit SHA for {repo}: {e}")
            return None
    
    def get_recent_commits(self, repo: str, since: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Get recent commits from GitHub
        
        Args:
            repo: Repository in format "owner/repo"
            since: ISO 8601 timestamp to get commits after
            limit: Maximum number of commits to fetch
        
        Returns:
            List of commit dictionaries
        """
        url = f"{self.base_url}/repos/{repo}/commits"
        params = {"per_page": limit}
        
        if since:
            params["since"] = since
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching commits from GitHub: {e}")
            return []
    
    def get_commit_details(self, repo: str, sha: str) -> Optional[Dict]:
        """
        Get detailed information about a specific commit
        
        Args:
            repo: Repository in format "owner/repo"
            sha: Commit SHA
        
        Returns:
            Commit details dictionary
        """
        url = f"{self.base_url}/repos/{repo}/commits/{sha}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching commit {sha}: {e}")
            return None
    
    def convert_to_event(self, commit: Dict, repo: str) -> Dict:
        """
        Convert GitHub commit to our event format
        
        Args:
            commit: GitHub commit object
            repo: Repository name
        
        Returns:
            Event dictionary ready for commit bus
        """
        commit_data = commit.get("commit", {})
        author_data = commit_data.get("author", {})
        
        # Extract files changed
        files_changed = []
        for file in commit.get("files", []):
            files_changed.append({
                "path": file.get("filename"),
                "status": file.get("status"),
                "additions": file.get("additions", 0),
                "deletions": file.get("deletions", 0),
                "patch": file.get("patch", "")
            })
        
        # Parse timestamp to datetime object (convert to naive for database)
        timestamp_str = author_data.get("date")
        if timestamp_str:
            # Parse the timestamp
            timestamp = date_parser.parse(timestamp_str)
            # Convert to naive datetime (remove timezone info for database)
            if timestamp.tzinfo is not None:
                timestamp = timestamp.replace(tzinfo=None)
        else:
            timestamp = datetime.now()
        
        return {
            "repo_id": repo,
            "commit_sha": commit.get("sha"),
            "parent_sha": [p.get("sha") for p in commit.get("parents", [])],
            "author_name": author_data.get("name", "Unknown"),
            "author_email": author_data.get("email", "unknown@example.com"),
            "timestamp": timestamp,  # Now a datetime object, not string
            "branch": "main",  # Default, can be improved
            "files_changed": files_changed,
            "commit_message": commit_data.get("message", ""),
            "push_id": None,
            "source": "github_sync",
            "metadata": {
                "synced_at": datetime.now().isoformat(),
                "url": commit.get("html_url")
            }
        }
    
    async def find_missed_commits(self, repo: str, last_processed_sha: Optional[str] = None, since_sha: Optional[str] = None) -> List[Dict]:
        """
        Find commits that were missed during downtime
        
        Args:
            repo: Repository in format "owner/repo"
            last_processed_sha: SHA of last successfully processed commit (legacy parameter)
            since_sha: SHA to find commits after (new optimized parameter)
        
        Returns:
            List of missed commits as events
        """
        # Support both parameter names for backward compatibility
        if since_sha:
            last_processed_sha = since_sha
        print(f"\n🔍 Checking GitHub for missed commits in {repo}...")
        
        # Get recent commits from GitHub
        commits = self.get_recent_commits(repo, limit=50)
        
        if not commits:
            print("✅ No commits found on GitHub")
            return []
        
        print(f"📊 Found {len(commits)} recent commits on GitHub")
        
        # If we have a last processed SHA, find commits after it
        missed = []
        for commit in commits:
            sha = commit.get("sha")
            
            # Stop when we reach the last processed commit
            if sha == last_processed_sha:
                break
            
            # Get full commit details (includes files)
            details = self.get_commit_details(repo, sha)
            if details:
                event = self.convert_to_event(details, repo)
                missed.append(event)
        
        if missed:
            print(f"🎯 Found {len(missed)} missed commits!")
            for event in missed:
                print(f"   - {event['commit_sha'][:8]}: {event['commit_message'][:50]}")
        else:
            print("✅ No missed commits (all up to date)")
        
        return missed

