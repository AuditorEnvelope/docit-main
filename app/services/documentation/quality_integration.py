"""
Quality integration helpers that wrap documentation generation with
quality evaluation. Ported from the legacy src/processors module and
updated to reference app.services equivalents only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple

from app.services.documentation.quality_checker import (
    DocumentationQuality,
    DocumentationQualityChecker,
    QualityScore,
)


class QualityValidationWrapper:
    """Validate generated documentation with optional regeneration hooks."""

    def __init__(self, threshold: float = 8.0, max_regenerations: int = 2) -> None:
        self.checker = DocumentationQualityChecker()
        self.threshold = threshold
        self.max_regenerations = max_regenerations

    async def validate_and_improve(
        self,
        repo_dir: str,
        repo_name: str,
        docs: Dict[str, str],
        regeneration_callback=None,
    ) -> Tuple[bool, DocumentationQuality]:
        """Validate documentation quality and regenerate if needed."""

        codebase_size = self._calculate_codebase_size(repo_dir)

        print("\n" + "=" * 60)
        print(f"🔍 QUALITY VALIDATION: {repo_name}")
        print("=" * 60)

        for attempt in range(self.max_regenerations + 1):
            quality = await self.checker.evaluate_documentation(
                repo_name=repo_name,
                codebase_size=codebase_size,
                docs=docs,
            )

            if attempt == 0:
                print("\n📊 Initial Quality Assessment:")
            else:
                print(f"\n📊 Quality Assessment (Attempt {attempt + 1}):")

            self._print_quality_summary(quality)

            if quality.overall_score >= self.threshold:
                print(
                    f"\n✅ QUALITY CHECK PASSED (Score: {quality.overall_score:.1f}/10)"
                )
                print("=" * 60 + "\n")
                return True, quality

            if attempt < self.max_regenerations:
                low_quality_docs = quality.get_low_quality_docs(self.threshold)
                print(
                    f"\n⚠️  QUALITY CHECK FAILED (Score: {quality.overall_score:.1f}/10)"
                )
                print(
                    "📝 Low-quality documents: "
                    + (", ".join(low_quality_docs) or "none identified")
                )
                print(
                    f"🔄 Regenerating with feedback (Attempt {attempt + 1}/{self.max_regenerations})..."
                )

                if regeneration_callback:
                    docs = await regeneration_callback(low_quality_docs, quality)
                else:
                    print("⚠️  No regeneration callback provided, cannot improve further")
                    break
            else:
                print(
                    "\n❌ QUALITY CHECK FAILED after "
                    f"{self.max_regenerations} regenerations"
                )
                print(
                    f"   Final Score: {quality.overall_score:.1f}/10 (Threshold: {self.threshold})"
                )
                print("=" * 60 + "\n")
                return False, quality

        return False, quality

    def _calculate_codebase_size(self, repo_dir: str) -> Dict[str, int]:
        language_extensions = {
            "Python": [".py"],
            "TypeScript": [".ts", ".tsx"],
            "JavaScript": [".js", ".jsx"],
            "Go": [".go"],
            "Rust": [".rs"],
            "Java": [".java"],
            "C++": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
            "C#": [".cs"],
            "Ruby": [".rb"],
            "PHP": [".php"],
            "Swift": [".swift"],
            "Kotlin": [".kt"],
            "Scala": [".scala"],
        }

        codebase_size: Dict[str, int] = {}
        repo_path = Path(repo_dir)
        skip_dirs = {".git", "node_modules", "venv", "__pycache__", "dist", "build", ".next"}

        for lang, extensions in language_extensions.items():
            total_lines = 0
            for ext in extensions:
                for file_path in repo_path.rglob(f"*{ext}"):
                    if any(skip in file_path.parts for skip in skip_dirs):
                        continue
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                            total_lines += sum(1 for _ in handle)
                    except OSError:
                        continue
            if total_lines > 0:
                codebase_size[lang] = total_lines

        return codebase_size

    def _print_quality_summary(self, quality: DocumentationQuality) -> None:
        print(f"\n   Overall Score: {quality.overall_score:.1f}/10")
        self._print_section("Architecture", quality.architecture_score)
        self._print_section("Workflow", quality.workflow_score)
        self._print_section("README", quality.readme_score)
        self._print_section("API", quality.api_score)

    def _print_section(self, title: str, score: QualityScore | None) -> None:
        if not score:
            return
        status = "✅" if score.score >= self.threshold else "❌"
        print(f"   {status} {title}: {score.score:.1f}/10")
        if score.score < self.threshold and score.weaknesses:
            preview = ", ".join(score.weaknesses[:2])
            print(f"      Issues: {preview}")

    def save_quality_report(self, repo_dir: str, quality: DocumentationQuality) -> None:
        report = self.checker.generate_quality_report(quality)
        report_path = Path(repo_dir) / "docs" / "QUALITY_REPORT.md"
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report, encoding="utf-8")
            print(f"📄 Quality report saved to {report_path}")
        except OSError as exc:  # pragma: no cover - filesystem dependent
            print(f"⚠️  Failed to save quality report: {exc}")


def read_generated_docs(repo_dir: str) -> Dict[str, str]:
    """Collect generated documentation artefacts from disk."""

    docs: Dict[str, str] = {}
    docs_path = Path(repo_dir) / "docs"

    arch = docs_path / "architecture" / "current.md"
    if arch.exists():
        docs["architecture"] = arch.read_text(encoding="utf-8")

    workflow = docs_path / "workflow" / "current.md"
    if workflow.exists():
        docs["workflow"] = workflow.read_text(encoding="utf-8")

    api_doc = docs_path / "api.md"
    if api_doc.exists():
        docs["api"] = api_doc.read_text(encoding="utf-8")

    readme_path = Path(repo_dir) / "README.md"
    if readme_path.exists():
        docs["readme"] = readme_path.read_text(encoding="utf-8")

    return docs


async def validate_documentation_quality(repo_dir: str, repo_name: str) -> bool:
    """Async helper that validates documentation and persists the report."""

    docs = read_generated_docs(repo_dir)
    if not docs:
        print("⚠️  No documentation found to validate")
        return True

    wrapper = QualityValidationWrapper(threshold=8.0, max_regenerations=0)
    passed, quality = await wrapper.validate_and_improve(repo_dir, repo_name, docs)
    wrapper.save_quality_report(repo_dir, quality)
    return passed
