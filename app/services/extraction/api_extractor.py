"""
API Extractor - Phase 3

Detects API routes, endpoints, and framework patterns.
Lightweight heuristic-based detection.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_extractor import BaseExtractor, ExtractionResult


class APIExtractor(BaseExtractor):
    """
    Extracts API layer signals from repository.

    Detects:
    - FastAPI decorators
    - Flask routes
    - Express router patterns
    - Django URL patterns
    - GraphQL schemas
    """

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "fastapi": {
            "files": ["main.py", "app.py", "api.py"],
            "imports": ["fastapi", "FastAPI"],
            "decorators": ["@app.get", "@app.post", "@app.put", "@app.delete"],
        },
        "flask": {
            "files": ["app.py", "routes.py"],
            "imports": ["flask", "Flask"],
            "decorators": ["@app.route", "@blueprint.route"],
        },
        "express": {
            "files": ["server.js", "app.js", "routes.js"],
            "imports": ["express"],
            "patterns": ["router.get", "router.post", "app.get", "app.post"],
        },
        "django": {
            "files": ["urls.py", "views.py"],
            "imports": ["django", "urlpatterns"],
            "patterns": ["path(", "url("],
        },
        "fastify": {
            "files": ["server.js", "app.js"],
            "imports": ["fastify"],
        },
    }

    # Route detection regex patterns
    ROUTE_PATTERNS = {
        "fastapi": re.compile(
            r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            re.IGNORECASE
        ),
        "flask": re.compile(
            r'@.*\.route\s*\(\s*["\']([^"\']+)["\']',
            re.IGNORECASE
        ),
        "express": re.compile(
            r'(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            re.IGNORECASE
        ),
    }

    def can_run(self, repo_analysis: Dict[str, Any]) -> bool:
        """Check if repository appears to have an API layer."""
        languages = repo_analysis.get("languages", [])
        frameworks = repo_analysis.get("frameworks", [])

        # Check for web frameworks
        web_frameworks = ["fastapi", "flask", "django", "express", "fastify"]
        if any(fw in frameworks for fw in web_frameworks):
            return True

        # Check for API-related languages
        if any(lang in languages for lang in ["python", "javascript", "typescript"]):
            return True

        return False

    def extract(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
    ) -> ExtractionResult:
        """Extract API signals from repository."""
        signals = {
            "primary_framework": None,
            "detected_routes": [],
            "api_patterns": [],
        }

        files_scanned = 0

        # Detect primary framework
        framework = self._detect_framework(repo_path, repo_analysis)
        if framework:
            signals["primary_framework"] = framework
            signals["api_patterns"].append("rest")

        # Find and scan route files
        route_files = self._find_route_files(repo_path, framework)

        for file_path in route_files:
            if files_scanned >= 10:  # Limit files scanned
                break

            routes = self._extract_routes_from_file(file_path, framework)
            if routes:
                signals["detected_routes"].extend(routes)
                files_scanned += 1

        # Detect GraphQL
        if self._detect_graphql(repo_path):
            signals["api_patterns"].append("graphql")

        # Detect WebSocket
        if self._detect_websocket(repo_path):
            signals["api_patterns"].append("websocket")

        # Limit routes to avoid bloating
        signals["detected_routes"] = signals["detected_routes"][:20]

        return ExtractionResult(
            success=True,
            signals=signals,
            files_scanned=files_scanned,
        )

    def _detect_framework(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
    ) -> Optional[str]:
        """Detect primary web framework."""
        frameworks = repo_analysis.get("frameworks", [])

        # Check known frameworks first
        for fw in ["fastapi", "flask", "django", "express", "fastify"]:
            if fw in frameworks:
                return fw

        # Check requirements/package files
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            content = self.safe_read_file(req_file, max_bytes=5000)
            if "fastapi" in content.lower():
                return "fastapi"
            if "flask" in content.lower():
                return "flask"
            if "django" in content.lower():
                return "django"

        package_file = repo_path / "package.json"
        if package_file.exists():
            content = self.safe_read_file(package_file, max_bytes=5000)
            if "express" in content.lower():
                return "express"
            if "fastify" in content.lower():
                return "fastify"

        return None

    def _find_route_files(
        self,
        repo_path: Path,
        framework: Optional[str],
    ) -> List[Path]:
        """Find files likely to contain route definitions."""
        files = []

        # Target specific directories
        target_dirs = [
            "api", "routes", "routers", "endpoints", "controllers",
            "views", "app", "src"
        ]

        # File patterns by framework
        patterns = {
            "fastapi": ["*.py"],
            "flask": ["*.py"],
            "django": ["urls.py", "views.py"],
            "express": ["*.js", "*.ts"],
            "fastify": ["*.js", "*.ts"],
        }

        file_patterns = patterns.get(framework, ["*.py", "*.js", "*.ts"])

        for dir_name in target_dirs:
            dir_path = repo_path / dir_name
            if dir_path.exists():
                for pattern in file_patterns:
                    files.extend(dir_path.glob(pattern))

        # Also check root level files
        for pattern in file_patterns:
            files.extend(repo_path.glob(pattern))

        # Limit and deduplicate
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen and len(unique_files) < 15:
                seen.add(f)
                unique_files.append(f)

        return unique_files

    def _extract_routes_from_file(
        self,
        file_path: Path,
        framework: Optional[str],
    ) -> List[Dict[str, str]]:
        """Extract route definitions from a file."""
        routes = []

        try:
            content = self.safe_read_file(file_path)
            if not content:
                return routes

            # Use appropriate pattern for framework
            pattern = self.ROUTE_PATTERNS.get(framework)

            if pattern:
                for match in pattern.finditer(content):
                    if framework == "fastapi":
                        method = match.group(1).upper()
                        path = match.group(2)
                    elif framework == "flask":
                        method = "*"  # Flask routes can handle multiple methods
                        path = match.group(1)
                    elif framework == "express":
                        method = match.group(1).upper()
                        path = match.group(2)
                    else:
                        continue

                    routes.append({
                        "method": method,
                        "path": path,
                        "source_file": str(file_path.relative_to(file_path.parent.parent)),
                    })

        except Exception:
            pass

        return routes

    def _detect_graphql(self, repo_path: Path) -> bool:
        """Detect GraphQL usage."""
        # Check for schema files
        graphql_files = list(repo_path.rglob("*.graphql")) + \
            list(repo_path.rglob("*.gql"))
        if graphql_files:
            return True

        # Check package requirements
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            content = self.safe_read_file(req_file, max_bytes=2000)
            if "graphene" in content.lower() or "ariadne" in content.lower():
                return True

        package_file = repo_path / "package.json"
        if package_file.exists():
            content = self.safe_read_file(package_file, max_bytes=2000)
            if "graphql" in content.lower():
                return True

        return False

    def _detect_websocket(self, repo_path: Path) -> bool:
        """Detect WebSocket usage."""
        patterns = ["websocket", "ws", "socket.io", "socketio"]

        # Scan a few Python/JS files
        for file_path in repo_path.rglob("*.py"):
            if file_path.stat().st_size > 50000:  # Skip large files
                continue
            content = self.safe_read_file(file_path, max_bytes=10000)
            if any(p in content.lower() for p in patterns):
                return True

        for file_path in repo_path.rglob("*.js"):
            if file_path.stat().st_size > 50000:
                continue
            content = self.safe_read_file(file_path, max_bytes=10000)
            if any(p in content.lower() for p in patterns):
                return True

        return False
