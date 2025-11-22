import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from app.services.documentation.comprehensive import generate_smart_documentation
from app.services.documentation.comprehensive import analyze_full_codebase
from app.services.documentation.doc_selector import determine_docs_to_update

logger = logging.getLogger(__name__)


def _mask_token(token: str) -> str:
    if not token or len(token) < 6:
        return "***"
    return f"{token[:3]}…{token[-3:]}"


@dataclass
class GenerationResult:
    workspace: Path
    docs_dir: Path
    summary: str
    architecture: str
    workflow: str
    api_doc: str

    def cleanup(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)


class ManualDocGenerator:
    def __init__(self, doc_persona: str = "internal") -> None:
        self.doc_persona = doc_persona

    async def generate(self, repo_full_name: str, github_token: str) -> GenerationResult:
        workspace = Path(tempfile.mkdtemp(prefix="docai_manual_"))
        logger.info("📥 Cloning %s for manual generation", repo_full_name)

        try:
            await self._clone_repository(repo_full_name, github_token, workspace)

            # 1. Analyze the full codebase for a comprehensive understanding.
            analysis = analyze_full_codebase(workspace)

            # 2. Determine which docs to update. For manual generation,
            #    pass an empty list of changed_files to signal that
            #    the selector should decide based on existing docs' quality.
            docs_to_update = await determine_docs_to_update(
                str(workspace),
                [],  # Pass empty list for manual generation
                analysis,
            )

            logger.info("📋 Manual generation plan: %s", docs_to_update)

            # 3. Call smart generator (diff-aware, optimized)
            await generate_smart_documentation(
                repo_dir=workspace,
                analysis=analysis,
                commit_sha="manual",
                ref="manual",
                doc_persona=self.doc_persona,
                docs_to_update=docs_to_update,
            )

            # 4. Read generated docs
            docs_dir = workspace / "docs"

            summary = self._read_file(docs_dir / "SUMMARY.md")
            architecture = self._read_file(docs_dir / "architecture" / "current.md")
            workflow = self._read_file(docs_dir / "workflow" / "current.md")
            api_doc = self._read_file(docs_dir / "api.md")

            return GenerationResult(
                workspace=workspace,
                docs_dir=docs_dir,
                summary=summary,
                architecture=architecture,
                workflow=workflow,
                api_doc=api_doc,
            )

        except Exception:
            logger.exception("Manual documentation generation failed for %s", repo_full_name)
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    # -------------------------------------------------------
    # helpers
    # -------------------------------------------------------

    async def _clone_repository(self, repo_full_name: str, token: str, workspace: Path) -> None:
        if not token:
            raise ValueError("GitHub token is required to clone the repository")

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
        masked = url.replace(token, _mask_token(token))
        logger.info("RUN git clone %s", masked)

        def _clone() -> None:
            subprocess.run(
                ["git", "clone", "--depth", "1", url, str(workspace)],
                check=True,
                env=env,
            )

        await asyncio.to_thread(_clone)


    def _read_file(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(errors="ignore")
