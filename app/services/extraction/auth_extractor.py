"""
Auth Extractor - Phase 3

Detects authentication and authorization patterns.
Lightweight keyword and pattern matching.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Set

from .base_extractor import BaseExtractor, ExtractionResult


class AuthExtractor(BaseExtractor):
    """
    Extracts authentication patterns from repository.

    Detects:
    - JWT tokens
    - OAuth/OAuth2
    - Session-based auth
    - API keys
    - Auth middleware
    """

    # Auth pattern keywords
    AUTH_KEYWORDS = {
        "jwt": ["jwt", "jsonwebtoken", "pyjwt", "jose"],
        "oauth": ["oauth", "oauth2", "openid", "sso"],
        "session": ["session", "cookie", "flask_login", "django.contrib.auth"],
        "api_key": ["api_key", "apikey", "x-api-key", "authorization"],
        "basic_auth": ["basicauth", "basic_auth", "htpasswd"],
    }

    # Middleware patterns
    MIDDLEWARE_PATTERNS = [
        r'@.*\.require_auth',
        r'@login_required',
        r'@jwt_required',
        r'@auth_required',
        r'auth_middleware',
        r'authenticate',
        r'authorize',
    ]

    # Auth-related file paths
    AUTH_PATHS = [
        "auth", "authentication", "authorization",
        "login", "logout", "signup", "register",
        "middleware", "guards", "permissions",
        "security", "oauth", "jwt"
    ]

    def can_run(self, repo_analysis: Dict[str, Any]) -> bool:
        """Always run - auth detection is lightweight."""
        return True

    def extract(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
    ) -> ExtractionResult:
        """Extract auth signals from repository."""
        signals = {
            "auth_patterns": [],
            "auth_middleware": [],
        }

        files_scanned = 0
        found_patterns: Set[str] = set()
        found_middleware: Set[str] = set()

        # Scan auth-related files first
        auth_files = self._find_auth_files(repo_path)

        for file_path in auth_files[:10]:  # Limit to 10 files
            patterns, middleware = self._scan_file_for_auth(file_path)
            found_patterns.update(patterns)
            found_middleware.update(middleware)
            files_scanned += 1

        # Also scan requirements/package files for auth libraries
        deps_patterns = self._scan_dependencies(repo_path)
        found_patterns.update(deps_patterns)

        # Convert to sorted lists
        signals["auth_patterns"] = sorted(found_patterns)
        signals["auth_middleware"] = sorted(found_middleware)

        return ExtractionResult(
            success=True,
            signals=signals,
            files_scanned=files_scanned,
        )

    def _find_auth_files(self, repo_path: Path) -> List[Path]:
        """Find files likely to contain auth logic."""
        files = []

        # Look in auth-related directories
        for auth_path in self.AUTH_PATHS:
            for path in repo_path.rglob(f"*{auth_path}*"):
                if path.is_file() and path.suffix in ['.py', '.js', '.ts']:
                    files.append(path)

        # Look for middleware files
        for path in repo_path.rglob("*middleware*"):
            if path.is_file() and path.suffix in ['.py', '.js', '.ts']:
                files.append(path)

        # Look for decorators/guards
        for path in repo_path.rglob("*decorator*"):
            if path.is_file() and path.suffix in ['.py', '.js', '.ts']:
                files.append(path)

        # Deduplicate and limit
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen and len(unique_files) < 15:
                seen.add(f)
                unique_files.append(f)

        return unique_files

    def _scan_file_for_auth(
        self,
        file_path: Path,
    ) -> tuple[Set[str], Set[str]]:
        """Scan a single file for auth patterns."""
        patterns_found: Set[str] = set()
        middleware_found: Set[str] = set()

        try:
            content = self.safe_read_file(file_path, max_bytes=30000)
            if not content:
                return patterns_found, middleware_found

            content_lower = content.lower()

            # Check for auth keywords
            for auth_type, keywords in self.AUTH_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in content_lower:
                        patterns_found.add(auth_type)
                        break

            # Check for middleware patterns
            for pattern in self.MIDDLEWARE_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    # Extract the actual decorator/function name
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches[:3]:  # Limit matches
                        middleware_found.add(match.strip())

        except Exception:
            pass

        return patterns_found, middleware_found

    def _scan_dependencies(self, repo_path: Path) -> Set[str]:
        """Scan dependency files for auth libraries."""
        patterns = set()

        # Python requirements
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            content = self.safe_read_file(req_file, max_bytes=5000).lower()

            auth_libs = {
                "jwt": ["pyjwt", "python-jose", "jose"],
                "oauth": ["authlib", "oauthlib", "requests-oauthlib"],
                "session": ["flask-login", "django", "session"],
            }

            for auth_type, libs in auth_libs.items():
                for lib in libs:
                    if lib in content:
                        patterns.add(auth_type)

        # Node package.json
        package_file = repo_path / "package.json"
        if package_file.exists():
            content = self.safe_read_file(package_file, max_bytes=5000).lower()

            auth_libs = {
                "jwt": ["jsonwebtoken", "jwt", "passport-jwt"],
                "oauth": ["passport-oauth", "oauth", "openid-client"],
                "session": ["express-session", "cookie-session"],
            }

            for auth_type, libs in auth_libs.items():
                for lib in libs:
                    if lib in content:
                        patterns.add(auth_type)

        return patterns
