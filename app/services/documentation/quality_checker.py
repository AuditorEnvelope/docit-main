"""
Documentation Quality Checker

Port of the legacy quality checker to the app.services namespace so that
all documentation quality evaluation stays inside the app tree.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)


def _sanitize_llm_json(text: str) -> str:
    """Sanitize a JSON string returned by an LLM."""
    text = text.strip().replace("```json", "").replace("```", "").strip()
    text = text.replace("\\n", "\\\\n")
    text = text.replace("\\t", "\\\\t")
    text = text.replace("\\r", "\\\\r")
    text = re.sub(r"\\(?![\"\\/bfnrtu])", r"\\\\", text)
    return text


def safe_json_parse(text: str) -> dict:
    """Safely parse JSON from an LLM response."""
    cleaned = _sanitize_llm_json(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive path
        logger.warning("⚠️  JSON parsing error from LLM response: %s", exc)
        logger.debug("LLM text preview: %s", cleaned[:200])
        return {
            "score": 7.0,
            "feedback": "Evaluation failed due to JSON parsing error",
            "strengths": [],
            "weaknesses": ["Could not parse LLM response"],
            "suggestions": [],
        }


@dataclass
class QualityScore:
    """Quality score for a documentation type."""

    score: float
    feedback: str
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]


@dataclass
class DocumentationQuality:
    """Overall documentation quality assessment."""

    architecture_score: Optional[QualityScore] = None
    workflow_score: Optional[QualityScore] = None
    readme_score: Optional[QualityScore] = None
    api_score: Optional[QualityScore] = None
    overall_score: float = 0.0

    def _collect_scores(self) -> List[float]:
        scores: List[float] = []
        if self.architecture_score:
            scores.append(self.architecture_score.score)
        if self.workflow_score:
            scores.append(self.workflow_score.score)
        if self.readme_score:
            scores.append(self.readme_score.score)
        if self.api_score:
            scores.append(self.api_score.score)
        return scores

    def should_regenerate(self, threshold: float = 8.0) -> bool:
        scores = self._collect_scores()
        return any(score < threshold for score in scores) if scores else False

    def get_low_quality_docs(self, threshold: float = 8.0) -> List[str]:
        low_quality: List[str] = []
        if self.architecture_score and self.architecture_score.score < threshold:
            low_quality.append("architecture")
        if self.workflow_score and self.workflow_score.score < threshold:
            low_quality.append("workflow")
        if self.readme_score and self.readme_score.score < threshold:
            low_quality.append("readme")
        if self.api_score and self.api_score.score < threshold:
            low_quality.append("api")
        return low_quality


class DocumentationQualityChecker:
    """Validates documentation quality using AI evaluation."""

    def __init__(self) -> None:
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
        else:  # pragma: no cover - environment dependent
            self.model = None
            logger.warning("⚠️  GEMINI_API_KEY not found - quality checking disabled")

    async def evaluate_documentation(
        self,
        repo_name: str,
        codebase_size: Dict[str, int],
        docs: Dict[str, str],
    ) -> DocumentationQuality:
        if not self.model:
            logger.warning("⚠️  Quality checking skipped - no LLM available")
            return DocumentationQuality(overall_score=10.0)

        quality = DocumentationQuality()

        total_lines = sum(codebase_size.values())
        num_languages = len(codebase_size)
        complexity_factor = min(10, (total_lines / 1000) + (num_languages * 0.5))

        logger.info(
            "📊 Evaluating documentation quality for %s (size=%s lines, languages=%s)",
            repo_name,
            total_lines,
            num_languages,
        )

        if "architecture" in docs:
            quality.architecture_score = await self._evaluate_category(
                "architecture",
                docs["architecture"],
                codebase_size,
                complexity_factor,
            )
        if "workflow" in docs:
            quality.workflow_score = await self._evaluate_category(
                "workflow",
                docs["workflow"],
                codebase_size,
                complexity_factor,
            )
        if "readme" in docs:
            quality.readme_score = await self._evaluate_category(
                "readme",
                docs["readme"],
                codebase_size,
                complexity_factor,
            )
        if "api" in docs:
            quality.api_score = await self._evaluate_category(
                "api",
                docs["api"],
                codebase_size,
                complexity_factor,
            )

        scores = quality._collect_scores()
        quality.overall_score = sum(scores) / len(scores) if scores else 0.0
        logger.info("⭐ Overall documentation score: %.1f/10", quality.overall_score)
        return quality

    async def _evaluate_category(
        self,
        category: str,
        content: str,
        codebase_size: Dict[str, int],
        complexity_factor: float,
    ) -> QualityScore:
        prompt = self._build_prompt(category, content, codebase_size, complexity_factor)
        try:
            response = self.model.generate_content(prompt)
            result = safe_json_parse(response.text if response else "")
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("⚠️  %s evaluation failed: %s", category, exc)
            return QualityScore(score=7.0, feedback="Evaluation failed", strengths=[], weaknesses=[], suggestions=[])

        return QualityScore(
            score=float(result.get("score", 5.0)),
            feedback=result.get("feedback", ""),
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
            suggestions=result.get("suggestions", []),
        )

    def _build_prompt(
        self,
        category: str,
        content: str,
        codebase_size: Dict[str, int],
        complexity_factor: float,
    ) -> str:
        languages = ", ".join(codebase_size.keys()) or "unknown"
        total_lines = sum(codebase_size.values())
        return f"""You are a technical documentation quality evaluator. Evaluate this {category} documentation.

CODEBASE CONTEXT:
- Languages: {languages}
- Total lines: {total_lines}
- Complexity: {complexity_factor:.1f}/10

DOCUMENTATION:
{content[:4000]}

Respond in JSON format with keys score, feedback, strengths, weaknesses, suggestions."""

    def generate_quality_report(self, quality: DocumentationQuality) -> str:
        sections: List[str] = [
            "# Documentation Quality Report",
            f"\n**Overall Score: {quality.overall_score:.1f}/10**",
        ]
        if quality.architecture_score:
            sections.append(self._format_section("Architecture", quality.architecture_score))
        if quality.workflow_score:
            sections.append(self._format_section("Workflow", quality.workflow_score))
        if quality.readme_score:
            sections.append(self._format_section("README", quality.readme_score))
        if quality.api_score:
            sections.append(self._format_section("API", quality.api_score))
        return "\n\n".join(sections)

    def _format_section(self, title: str, score: QualityScore) -> str:
        strengths = "\n".join(f"- {item}" for item in score.strengths) or "- None"
        weaknesses = "\n".join(f"- {item}" for item in score.weaknesses) or "- None"
        suggestions = "\n".join(f"- {item}" for item in score.suggestions) or "- None"
        return (
            f"## {title}\n"
            f"**Score:** {score.score:.1f}/10\n\n"
            f"{score.feedback}\n\n"
            f"**Strengths:**\n{strengths}\n\n"
            f"**Weaknesses:**\n{weaknesses}\n\n"
            f"**Suggestions:**\n{suggestions}"
        )
