import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from app.services.documentation.comprehensive import (
    ComprehensiveDocBuilder,
    update_summary_navigation,
    get_current_version,
)

logger = logging.getLogger(__name__)


def _mask_token(token: str) -> str:
    if not token or len(token) < 6:
        return "***"
    return f"{token[:3]}…{token[-3:]}"


@dataclass
class GenerationResult:
    """Result of the manual documentation generation."""

    workspace: Path
    docs_dir: Path
    summary: str
    architecture: str
    workflow: str
    api_doc: str
    # Phase 6: Token tracking
    input_tokens: int
    output_tokens: int
    model_name: str

    def cleanup(self) -> None:
        """Remove the temporary workspace."""
        shutil.rmtree(self.workspace, ignore_errors=True)


class ManualDocGenerator:
    """Generate documentation artefacts for a repository using LLM rotation."""

    def __init__(self, doc_persona: str = "internal") -> None:
        self.doc_persona = doc_persona

    async def generate(self, repo_full_name: str, github_token: str) -> GenerationResult:
        """Clone repository, generate docs, and return generation artefacts."""
        workspace = Path(tempfile.mkdtemp(prefix="docai_manual_"))
        logger.info("📥 Cloning %s for manual generation", repo_full_name)

        try:
            await self._clone_repository(repo_full_name, github_token, workspace)
            docs_dir = workspace / "docs"
            self._prepare_docs_directory(docs_dir)

            builder = ComprehensiveDocBuilder(
                workspace, doc_persona=self.doc_persona, repo_name=repo_full_name)
            generated_docs: Dict[str, str] = await builder.build()

            # Handle dynamic sections - support both old and new section IDs
            summary = generated_docs.get(
                "overview") or generated_docs.get("summary", "")
            architecture = generated_docs.get("architecture", "")
            workflow = generated_docs.get(
                "development") or generated_docs.get("workflow", "")
            api_doc = generated_docs.get(
                "api") or generated_docs.get("usage", "")

            # NEW: Extract additional sections from comprehensive build
            components = generated_docs.get("components", "")
            dependencies = generated_docs.get("dependencies", "")
            deployment = generated_docs.get("deployment", "")

            # Phase 6: Extract token data from generation result
            token_data = generated_docs.get("token_data", {})
            input_tokens = token_data.get("input_tokens", 0)
            output_tokens = token_data.get("output_tokens", 0)
            model_name = token_data.get("model_name", "unknown")

            # Create the proper folder structure based on doc_persona
            persona_folder_name = "dev" if self.doc_persona in (
                "dev", "developer") else "internal"
            print(f"📚 Creating documentation in {persona_folder_name} folder")

            # Create the current persona folder
            persona_dir = docs_dir / persona_folder_name
            persona_dir.mkdir(exist_ok=True)

            # Create the other persona folder if it doesn't exist
            # But don't modify its contents if it already exists
            other_persona = "internal" if persona_folder_name == "dev" else "dev"
            other_persona_dir = docs_dir / other_persona
            other_persona_dir.mkdir(exist_ok=True)

            # Only add a placeholder README if the other persona folder is empty
            if not any(other_persona_dir.iterdir()):
                print(
                    f"📝 Creating placeholder README in {other_persona} folder")
                self._write_text(other_persona_dir / "README.md",
                                 f"# Documentation for {other_persona}\n\nThis persona documentation is not available.")

            # Persist artefacts in the correct persona folder
            # Write overview content to README.md (the actual content)
            self._write_text(persona_dir / "README.md", summary)

            # ============================================================
            # DYNAMIC SECTION WRITING FROM PLAN
            # Writes sections using meaningful folder names from the plan
            # e.g., "component-hierarchy/", "state-management/"
            # ============================================================

            # Get the plan from generated_docs (contains meaningful section IDs)
            plan_data = generated_docs.get("plan", {})
            planned_sections = plan_data.get("sections", [])

            # DEBUG: Log what we received
            print(f"   🔍 DEBUG: plan_data keys: {list(plan_data.keys())}")
            print(
                f"   🔍 DEBUG: planned_sections count: {len(planned_sections)}")
            print(
                f"   🔍 DEBUG: generated_docs keys: {[k for k in generated_docs.keys() if not k.startswith('_')]}")
            for ps in planned_sections[:3]:
                section_id = ps.get("id", "")
                has_content = bool(generated_docs.get(section_id, ""))
                print(
                    f"   🔍 DEBUG: section '{section_id}' has content: {has_content}")

            written_sections = []
            for section_info in planned_sections:
                # e.g., "component-hierarchy"
                section_id = section_info.get("id", "")
                section_title = section_info.get("title", "")

                # Get content for this section
                section_content = generated_docs.get(section_id, "")

                if section_content:
                    section_dir = persona_dir / section_id
                    section_dir.mkdir(exist_ok=True)
                    self._write_text(
                        section_dir / "current.md", section_content)
                    version = get_current_version(persona_dir, section_id)
                    self._write_text(
                        section_dir / f"v{version}-{section_id}.md", section_content)
                    print(f"   📄 {section_title}: v{version}")
                    written_sections.append(section_id)

            # Fallback: Write any standard sections not in plan (backward compatibility)
            fallback_mapping = [
                ("architecture", architecture, "📐 Architecture"),
                ("workflow", workflow, "🔄 Workflow"),
                ("api", api_doc, "📡 API"),
                ("components", components, "🧩 Components"),
                ("dependencies", dependencies, "📦 Dependencies"),
                ("deployment", deployment, "🚀 Deployment"),
            ]

            for folder_name, content, label in fallback_mapping:
                if folder_name not in written_sections and content:
                    section_dir = persona_dir / folder_name
                    section_dir.mkdir(exist_ok=True)
                    self._write_text(section_dir / "current.md", content)
                    version = get_current_version(persona_dir, folder_name)
                    self._write_text(
                        section_dir / f"v{version}-{folder_name}.md", content)
                    print(f"   {label}: v{version} [fallback]")
                    written_sections.append(folder_name)

            # Create changes folder inside the persona folder
            (persona_dir / "changes").mkdir(exist_ok=True)

            # Generate proper navigation SUMMARY.md for the persona folder
            # This creates links to all sections (architecture, workflow, components, etc.)
            update_summary_navigation(persona_dir)

            # Update root README & changelog for traceability
            self._write_text(workspace / "README.md", summary)
            changelog = (
                "# Changelog\n\n"
                "## [1.0.0] - Auto-generated documentation\n\n"
                "### Added\n"
                "- Comprehensive documentation set generated by DocIt AI\n"
                "- Architecture, workflow, API docs under /docs\n"
                "- Updated README summary\n"
            )
            self._write_text(workspace / "CHANGELOG.md", changelog)

            return GenerationResult(
                workspace=workspace,
                docs_dir=docs_dir,
                summary=summary,
                architecture=architecture,
                workflow=workflow,
                api_doc=api_doc,
                # Phase 6: Include token data
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_name=model_name,
            )
        except Exception:
            logger.exception(
                "Manual documentation generation failed for %s", repo_full_name)
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    async def _clone_repository(self, repo_full_name: str, token: str, workspace: Path) -> None:
        if not token:
            raise ValueError(
                "GitHub token is required to clone the repository")

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
        masked = url.replace(token, _mask_token(token))
        logger.info("RUN git clone %s", masked)

        def _clone() -> None:
            import subprocess
            try:
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", url, str(workspace)],
                    check=True,
                    env=env,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.lower() if e.stderr else ""
                if "repository not found" in error_msg:
                    raise ValueError(
                        f"Repository '{repo_full_name}' not found. "
                        "Please check that the repository exists and you have access to it."
                    )
                elif "authentication failed" in error_msg:
                    raise ValueError(
                        "GitHub authentication failed. "
                        "Please reconnect your GitHub account."
                    )
                else:
                    raise ValueError(
                        f"Failed to clone repository: {e.stderr or 'Unknown error'}"
                    )

        await asyncio.to_thread(_clone)

    def _prepare_docs_directory(self, docs_dir: Path) -> None:
        docs_dir.mkdir(exist_ok=True)

    def _write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
