"""Async smart processor for GitHub push events (ported from legacy src)."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Iterable, Tuple

from app.services.docbook.publisher import DocbookPublisher
from app.services.documentation.comprehensive import ComprehensiveDocBuilder
from app.services.documentation.comprehensive import generate_smart_documentation
from app.services.documentation.quality_integration import (
    read_generated_docs,
    validate_documentation_quality,
)
from app.services.github.change_analysis import smart_analyze_change
from app.utils.github_dual_app import GitHubDualAppHelper
async def handle_push_event(
    payload: Dict[str, object],
    *,
    github_token: str | None = None,
    doc_persona: str = "internal",
) -> None:
    """Clone the repo at the pushed commit, analyse, generate docs, and publish."""

    repository = payload.get("repository") or {}
    repo_full = repository.get("full_name") if isinstance(repository, dict) else None
    if not repo_full or "/" not in repo_full:
        raise ValueError("Push payload missing repository full name")

    commit_sha = payload.get("after")
    if not isinstance(commit_sha, str) or not commit_sha:
        raise ValueError("Push payload missing commit SHA")

    changed_files, removed_files = _collect_changed_files(payload.get("commits") or [])
    if not changed_files:
        print("No changed files in push, skipping")
        return

    if _is_docai_bot_commit(payload.get("commits") or []):
        print("⏭️  Skipping DocAI bot commit")
        return

    token = await _resolve_token(github_token, payload)
    if not token:
        raise RuntimeError("No GitHub token available for smart processor")

    dual_app = GitHubDualAppHelper()

    with tempfile.TemporaryDirectory(prefix="docai_smart_") as tmpdir:
        repo_path = Path(tmpdir)
        _clone_repository(repo_full, token, repo_path)
        _checkout_commit(repo_path, commit_sha)

        analysis = smart_analyze_change(
            payload,
            str(repo_path),
            sorted(changed_files),
            sorted(removed_files),
        )

        if not analysis.get("is_significant", False):
            print(
                "❌ Change not significant:",
                analysis.get("reason") or analysis.get("summary") or "no reason provided",
            )
            return

        print(f"✅ Significant change detected: {analysis.get('title', commit_sha[:12])}")


        ref = payload.get("ref", "unknown")
        await generate_smart_documentation(
            repo_path,
            analysis,
            commit_sha,
            ref,
            doc_persona
        )

        docs = read_generated_docs(str(repo_path))
        if docs:
            await validate_documentation_quality(str(repo_path), repository.get("name", repo_full))
        else:
            print("⚠️  No documentation artefacts found after build")

        await _publish_to_docbook(
            repo_path,
            repository,
            commit_sha,
            payload,
            dual_app,
        )


async def _resolve_token(
    github_token: str | None,
    payload: Dict[str, object],
) -> str | None:
    if github_token:
        return github_token

    installation = payload.get("installation")
    installation_id = None
    if isinstance(installation, dict):
        installation_id = installation.get("id")

    helper = GitHubDualAppHelper()
    if installation_id:
        token = await helper.get_reader_token(int(installation_id))
        if token:
            print("✅ Using GitHub App installation token (reader)")
            return token

    return None


def _clone_repository(repo_full: str, token: str, target_dir: Path) -> None:
    url = f"https://x-access-token:{token}@github.com/{repo_full}.git"
    subprocess.run(
        ["git", "clone", "--depth", "50", "--single-branch", url, str(target_dir)],
        check=True,
    )


def _checkout_commit(repo_dir: Path, commit_sha: str) -> None:
    try:
        subprocess.run(["git", "checkout", "--detach", commit_sha], cwd=repo_dir, check=True)
        print(f"✅ Checked out commit {commit_sha[:8]}")
    except subprocess.CalledProcessError as exc:
        print(f"⚠️  Could not checkout commit {commit_sha[:8]}: {exc}")
        print("   Continuing on current branch")


def _collect_changed_files(commits: Iterable[Dict[str, object]]) -> Tuple[set[str], set[str]]:
    changed: set[str] = set()
    removed: set[str] = set()
    for commit in commits:
        if not isinstance(commit, dict):
            continue
        for bucket in ("added", "modified"):
            paths = commit.get(bucket)
            if isinstance(paths, list):
                changed.update(path for path in paths if isinstance(path, str))
        paths = commit.get("removed")
        if isinstance(paths, list):
            removed.update(path for path in paths if isinstance(path, str))
    return changed, removed


def _is_docai_bot_commit(commits: Iterable[Dict[str, object]]) -> bool:
    if not commits:
        return False
    last = commits[-1]
    if not isinstance(last, dict):
        return False
    author = last.get("author")
    if not isinstance(author, dict):
        return False
    name = (author.get("name") or "").lower()
    email = (author.get("email") or "").lower()
    return "docai" in name or "docai@bots.local" in email


async def _publish_to_docbook(
    repo_dir: Path,
    repository: Dict[str, object],
    commit_sha: str,
    payload: Dict[str, object],
    dual_app: GitHubDualAppHelper,
) -> None:
    docs_dir = repo_dir / "docs"
    if not docs_dir.exists():
        print("⚠️  No docs directory found, skipping docbook publish")
        return

    # Check for either db_pool (asyncpg) or db_session (SQLAlchemy)
    db_pool = payload.get("_db_pool")
    db_session = payload.get("_db_session")
    
    # Don't use db_session in worker context - it causes greenlet_spawn errors
    # Only use db_pool (asyncpg) like the old codebase, or skip if neither available
    if db_pool is None and db_session is None:
        print("ℹ️  No database pool in payload; skipping docbook publish (webhook mode)")
        return

    user_id = payload.get("_user_id")
    org_id = payload.get("_org_id")
    if not isinstance(org_id, str) or not org_id:
        full_name = repository.get("full_name")
        if isinstance(full_name, str) and "/" in full_name:
            org_id = full_name.split("/", 1)[0]
        else:
            print("⚠️  Unable to resolve organization for docbook publish; skipping")
            return  # Don't raise - make it non-blocking

    source_repo = repository.get("name")
    if not isinstance(source_repo, str) or not source_repo:
        source_repo = repository.get("full_name", "unknown-repo")

    installation_id = payload.get("_installation_id")
    if installation_id is None:
        installation = payload.get("installation")
        if isinstance(installation, dict):
            installation_id = installation.get("id")

    # Resolve writer installation ID using AppInstallationService (like old codebase)
    # This is the KEY FIX - matches old codebase behavior exactly
    writer_installation_id = installation_id
    
    if dual_app.dual_app_mode and dual_app.writer_app_id and org_id and db_pool:
        try:
            from app.services.github.app_installation_service import AppInstallationService
            service = AppInstallationService(db_pool=db_pool)
            writer_installation_id = await service.get_app_installation_id(
                org_id,
                int(dual_app.writer_app_id),
            )
            if writer_installation_id:
                print(f"✅ Resolved writer installation ID {writer_installation_id} for org {org_id}")
            else:
                print(f"⚠️  Could not resolve writer installation ID from DB for org {org_id}, app {dual_app.writer_app_id}")
                writer_installation_id = installation_id  # Fallback to reader installation
        except Exception as lookup_error:
            print(f"⚠️  Could not resolve writer installation ID from DB: {lookup_error}")
            writer_installation_id = installation_id  # Fallback to reader installation

    # Only use db_pool (asyncpg) - don't use db_session to avoid greenlet_spawn errors
    # This matches the old codebase behavior
    publisher = DocbookPublisher(db_pool=db_pool, dual_app=dual_app)
    try:
        result = await publisher.publish_to_docbook(
            user_id=user_id or "",
            org_id=org_id,
            source_repo_name=source_repo,
            docs_dir=docs_dir,
            commit_sha=commit_sha,
            installation_id=writer_installation_id,  # Use resolved writer installation ID
            commit_message=f"docs: Auto-generated documentation ({commit_sha[:7]})",
        )
        if result.get("status") == "error":
            print(f"⚠️  Docbook publish returned error: {result.get('message')}")
            # Don't raise - docbook publishing is non-critical
    except Exception as exc:  # pragma: no cover - external side effects
        # Log but don't raise - docbook publishing failure shouldn't fail event processing
        print(f"⚠️  Error publishing to docbook (non-critical): {exc}")
        import traceback
        traceback.print_exc()
        # Don't re-raise - let event processing continue
