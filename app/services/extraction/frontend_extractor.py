"""
Frontend Extractor - Phase 3

Detects frontend frameworks, components, and patterns.
Lightweight heuristic-based detection for React, Vue, Angular, etc.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .base_extractor import BaseExtractor, ExtractionResult


class FrontendExtractor(BaseExtractor):
    """
    Extracts frontend framework signals from repository.

    Detects:
    - React/Next.js patterns
    - Vue.js patterns
    - Angular patterns
    - Component structure
    - State management
    - Routing
    """

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "react": {
            "files": ["App.tsx", "App.jsx", "index.tsx", "index.jsx", "next.config.js", "next.config.ts"],
            "imports": ["react", "React", "next", "Next"],
            "patterns": ["import React", "from 'react'", "from \"react\"", "useState", "useEffect", "useContext"],
            "extensions": [".tsx", ".jsx"],
        },
        "nextjs": {
            "files": ["next.config.js", "next.config.ts", "next.config.mjs"],
            "imports": ["next"],
            "patterns": ["getStaticProps", "getServerSideProps", "getInitialProps", "next/head", "next/link"],
        },
        "vue": {
            "files": ["App.vue", "main.js", "main.ts"],
            "imports": ["vue", "Vue"],
            "patterns": ["createApp", "new Vue", "<template>", "<script setup>"],
            "extensions": [".vue"],
        },
        "angular": {
            "files": ["angular.json", "main.ts"],
            "imports": ["@angular/core", "@angular/common"],
            "patterns": ["@Component", "@NgModule", "@Injectable"],
        },
    }

    # State management detection
    STATE_PATTERNS = {
        "redux": ["redux", "createStore", "configureStore", "useSelector", "useDispatch"],
        "zustand": ["zustand", "create"],
        "mobx": ["mobx", "observable", "makeObservable"],
        "recoil": ["recoil", "atom", "selector", "useRecoilState"],
        "context": ["createContext", "useContext"],
    }

    # Routing patterns
    ROUTING_PATTERNS = {
        "react-router": ["react-router", "react-router-dom", "BrowserRouter", "useParams", "useNavigate"],
        "nextjs-routing": ["next/link", "next/router", "useRouter"],
        "vue-router": ["vue-router", "createRouter", "useRoute"],
    }

    # UI library patterns
    UI_LIBRARY_PATTERNS = {
        "material-ui": ["@mui/material", "@material-ui/core"],
        "antd": ["antd", "@ant-design"],
        "chakra": ["@chakra-ui/react"],
        "tailwind": ["tailwindcss", "tailwind"],
        "bootstrap": ["bootstrap", "react-bootstrap"],
        "shadcn": ["@/components/ui", "shadcn"],
    }

    def can_run(self, repo_analysis: Dict[str, Any]) -> bool:
        """Check if repository appears to be a frontend project."""
        languages = repo_analysis.get("languages", [])
        frameworks = repo_analysis.get("frameworks", [])

        # Check for frontend languages
        frontend_langs = ["typescript", "javascript", "ts", "js"]
        if any(lang in languages for lang in frontend_langs):
            return True

        # Check for known frontend frameworks
        frontend_frameworks = ["react", "vue", "angular", "nextjs", "svelte"]
        if any(fw in frameworks for fw in frontend_frameworks):
            return True

        return False

    def extract(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
    ) -> ExtractionResult:
        """Extract frontend signals from repository."""
        signals = {
            "primary_framework": None,
            "framework_version": None,
            "is_typescript": False,
            "component_count": 0,
            "page_count": 0,
            "state_management": [],
            "routing": [],
            "ui_libraries": [],
            "detected_hooks": [],
            "has_ssr": False,
            "has_api_routes": False,
        }

        files_scanned = 0

        try:
            # Detect primary framework
            framework = self._detect_framework(repo_path)
            signals["primary_framework"] = framework

            # Check for TypeScript and set primary language
            signals["is_typescript"] = self._detect_typescript(repo_path)
            if signals["is_typescript"]:
                signals["primary_language"] = "typescript"
            else:
                signals["primary_language"] = "javascript"

            # Count components
            signals["component_count"] = self._count_components(
                repo_path, framework)

            # Count pages (for Next.js)
            if framework in ["nextjs", "react"]:
                signals["page_count"] = self._count_pages(repo_path)

            # Detect state management
            signals["state_management"] = self._detect_state_management(
                repo_path)

            # Detect routing
            signals["routing"] = self._detect_routing(repo_path)

            # Detect UI libraries
            signals["ui_libraries"] = self._detect_ui_libraries(repo_path)

            # Detect hooks usage
            signals["detected_hooks"] = self._detect_hooks(repo_path)

            # Check for SSR (Next.js specific)
            if framework == "nextjs":
                signals["has_ssr"] = self._detect_ssr(repo_path)
                signals["has_api_routes"] = self._detect_api_routes(repo_path)

            files_scanned = self._count_relevant_files(repo_path)

            return ExtractionResult(
                success=True,
                extractor_name=self.name,
                signals=signals,
                files_scanned=files_scanned,
            )

        except Exception as e:
            return ExtractionResult(
                success=False,
                extractor_name=self.name,
                error_message=str(e),
            )

    def _detect_framework(self, repo_path: Path) -> Optional[str]:
        """Detect the primary frontend framework."""
        # Check for Next.js first (it's built on React)
        if self._check_patterns(repo_path, self.FRAMEWORK_PATTERNS["nextjs"]):
            return "nextjs"

        # Check for React
        if self._check_patterns(repo_path, self.FRAMEWORK_PATTERNS["react"]):
            return "react"

        # Check for Vue
        if self._check_patterns(repo_path, self.FRAMEWORK_PATTERNS["vue"]):
            return "vue"

        # Check for Angular
        if self._check_patterns(repo_path, self.FRAMEWORK_PATTERNS["angular"]):
            return "angular"

        return None

    def _check_patterns(self, repo_path: Path, patterns: Dict[str, Any]) -> bool:
        """Check if repository matches given patterns."""
        # Check files
        for file_name in patterns.get("files", []):
            if list(repo_path.rglob(file_name)):
                return True

        # Check package.json for imports
        package_json = repo_path / "package.json"
        if package_json.exists():
            content = self.safe_read_file(package_json)
            for import_name in patterns.get("imports", []):
                if import_name in content:
                    return True

        # Check for patterns in source files
        for ext in patterns.get("extensions", [".tsx", ".jsx", ".vue", ".ts", ".js"]):
            for file_path in repo_path.rglob(f"*{ext}"):
                if file_path.is_file():
                    content = self.safe_read_file(file_path, max_bytes=50000)
                    for pattern in patterns.get("patterns", []):
                        if pattern in content:
                            return True
                    break  # Only check first file of each extension

        return False

    def _detect_typescript(self, repo_path: Path) -> bool:
        """Check if project uses TypeScript."""
        tsconfig = repo_path / "tsconfig.json"
        if tsconfig.exists():
            return True

        # Check for .ts/.tsx files
        for ext in [".ts", ".tsx"]:
            if list(repo_path.rglob(f"*{ext}")):
                return True

        return False

    def _count_components(self, repo_path: Path, framework: Optional[str]) -> int:
        """Count React/Vue components."""
        count = 0

        if framework in ["react", "nextjs"]:
            # Count .tsx/.jsx files (excluding pages)
            for ext in [".tsx", ".jsx"]:
                for file_path in repo_path.rglob(f"*{ext}"):
                    if "node_modules" in str(file_path):
                        continue
                    if framework == "nextjs" and ("pages/" in str(file_path) or "app/" in str(file_path)):
                        continue
                    if "App." in file_path.name or "index." in file_path.name:
                        continue
                    count += 1

        elif framework == "vue":
            # Count .vue files
            for file_path in repo_path.rglob("*.vue"):
                if "node_modules" not in str(file_path):
                    count += 1

        return count

    def _count_pages(self, repo_path: Path) -> int:
        """Count Next.js pages."""
        count = 0

        # Check pages directory (Next.js < 13)
        pages_dir = repo_path / "pages"
        if pages_dir.exists():
            for file_path in pages_dir.rglob("*.tsx"):
                if "_app." not in file_path.name and "_document." not in file_path.name:
                    count += 1
            for file_path in pages_dir.rglob("*.jsx"):
                if "_app." not in file_path.name and "_document." not in file_path.name:
                    count += 1

        # Check app directory (Next.js 13+)
        app_dir = repo_path / "app"
        if app_dir.exists():
            for file_path in app_dir.rglob("page.tsx"):
                count += 1
            for file_path in app_dir.rglob("page.jsx"):
                count += 1

        return count

    def _detect_state_management(self, repo_path: Path) -> List[str]:
        """Detect state management libraries."""
        detected = []

        package_json = repo_path / "package.json"
        if not package_json.exists():
            return detected

        content = self.safe_read_file(package_json)

        for lib, patterns in self.STATE_PATTERNS.items():
            for pattern in patterns:
                if pattern in content:
                    detected.append(lib)
                    break

        return detected

    def _detect_routing(self, repo_path: Path) -> List[str]:
        """Detect routing libraries."""
        detected = []

        package_json = repo_path / "package.json"
        if not package_json.exists():
            return detected

        content = self.safe_read_file(package_json)

        for lib, patterns in self.ROUTING_PATTERNS.items():
            for pattern in patterns:
                if pattern in content:
                    detected.append(lib)
                    break

        return detected

    def _detect_ui_libraries(self, repo_path: Path) -> List[str]:
        """Detect UI component libraries."""
        detected = []

        package_json = repo_path / "package.json"
        if not package_json.exists():
            return detected

        content = self.safe_read_file(package_json)

        for lib, patterns in self.UI_LIBRARY_PATTERNS.items():
            for pattern in patterns:
                if pattern in content:
                    detected.append(lib)
                    break

        return detected

    def _detect_hooks(self, repo_path: Path) -> List[str]:
        """Detect commonly used React hooks."""
        hooks = []
        hook_patterns = [
            "useState", "useEffect", "useContext", "useReducer",
            "useCallback", "useMemo", "useRef", "useImperativeHandle",
            "useLayoutEffect", "useDebugValue", "useId",
        ]

        # Check a sample of files
        checked = 0
        for file_path in repo_path.rglob("*.tsx"):
            if checked >= 10:
                break
            if "node_modules" in str(file_path):
                continue

            content = self.safe_read_file(file_path, max_bytes=30000)
            for hook in hook_patterns:
                if hook in content and hook not in hooks:
                    hooks.append(hook)

            checked += 1

        return hooks

    def _detect_ssr(self, repo_path: Path) -> bool:
        """Check if Next.js project uses SSR."""
        # Check for getServerSideProps
        for file_path in repo_path.rglob("*.tsx"):
            if "node_modules" in str(file_path):
                continue
            content = self.safe_read_file(file_path, max_bytes=20000)
            if "getServerSideProps" in content:
                return True

        return False

    def _detect_api_routes(self, repo_path: Path) -> bool:
        """Check if Next.js project has API routes."""
        api_dir = repo_path / "pages" / "api"
        if api_dir.exists():
            return True

        api_dir = repo_path / "app" / "api"
        if api_dir.exists():
            return True

        return False

    def _count_relevant_files(self, repo_path: Path) -> int:
        """Count relevant frontend files."""
        count = 0
        for ext in [".tsx", ".jsx", ".vue", ".ts", ".js"]:
            for file_path in repo_path.rglob(f"*{ext}"):
                if "node_modules" not in str(file_path):
                    count += 1
        return count
