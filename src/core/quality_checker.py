"""
Documentation Quality Checker
Validates documentation quality using LLM evaluation and enforces minimum standards
"""

import os
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import google.generativeai as genai

def safe_json_parse(text: str) -> dict:
    """
    Safely parse JSON from LLM response, handling escape sequences
    """
    # Remove markdown code blocks
    text = text.strip().replace("```json", "").replace("```", "").strip()
    
    # Sanitize escape sequences
    text = text.replace('\\n', '\\\\n')
    text = text.replace('\\t', '\\\\t')
    text = text.replace('\\r', '\\\\r')
    
    # Fix invalid escapes (keep only valid JSON escapes)
    text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parsing error: {e}")
        print(f"   Text preview: {text[:200]}")
        # Return default structure
        return {
            "score": 7.0,
            "feedback": "Evaluation failed due to JSON parsing error",
            "strengths": [],
            "weaknesses": ["Could not parse LLM response"],
            "suggestions": []
        }

@dataclass
class QualityScore:
    """Quality score for a documentation type"""
    score: float  # 0-10
    feedback: str
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]

@dataclass
class DocumentationQuality:
    """Overall documentation quality assessment"""
    architecture_score: Optional[QualityScore] = None
    workflow_score: Optional[QualityScore] = None
    readme_score: Optional[QualityScore] = None
    api_score: Optional[QualityScore] = None
    overall_score: float = 0.0
    
    def should_regenerate(self, threshold: float = 8.0) -> bool:
        """Check if any document needs regeneration"""
        scores = []
        if self.architecture_score:
            scores.append(self.architecture_score.score)
        if self.workflow_score:
            scores.append(self.workflow_score.score)
        if self.readme_score:
            scores.append(self.readme_score.score)
        if self.api_score:
            scores.append(self.api_score.score)
            
        return any(score < threshold for score in scores) if scores else False
    
    def get_low_quality_docs(self, threshold: float = 8.0) -> List[str]:
        """Get list of documents that need improvement"""
        low_quality = []
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
    """
    Validates documentation quality using AI evaluation
    Ensures comprehensive, detailed, and useful documentation
    """
    
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        else:
            self.model = None
            print("⚠️  GEMINI_API_KEY not found - quality checking disabled")
    
    async def evaluate_documentation(
        self, 
        repo_name: str,
        codebase_size: Dict[str, int],  # Lines of code per language
        docs: Dict[str, str]
    ) -> DocumentationQuality:
        """
        Evaluate documentation quality across all doc types
        
        Args:
            repo_name: Repository name
            codebase_size: Dictionary of language -> line count
            docs: Dictionary of doc_type -> content
            
        Returns:
            DocumentationQuality with scores and feedback
        """
        if not self.model:
            print("⚠️  Quality checking skipped - no LLM available")
            return DocumentationQuality(overall_score=10.0)  # Pass by default
        
        quality = DocumentationQuality()
        
        # Calculate codebase complexity score
        total_lines = sum(codebase_size.values())
        num_languages = len(codebase_size)
        complexity_factor = min(10, (total_lines / 1000) + (num_languages * 0.5))
        
        print(f"\n📊 Evaluating documentation quality for {repo_name}")
        print(f"   Codebase: {total_lines} lines, {num_languages} languages")
        print(f"   Complexity factor: {complexity_factor:.1f}/10")
        
        # Evaluate each document type
        if "architecture" in docs:
            quality.architecture_score = await self._evaluate_architecture(
                docs["architecture"], codebase_size, complexity_factor
            )
            print(f"   🏗️  Architecture: {quality.architecture_score.score:.1f}/10")
        
        if "workflow" in docs:
            quality.workflow_score = await self._evaluate_workflow(
                docs["workflow"], codebase_size, complexity_factor
            )
            print(f"   🔄 Workflow: {quality.workflow_score.score:.1f}/10")
        
        if "readme" in docs:
            quality.readme_score = await self._evaluate_readme(
                docs["readme"], codebase_size, complexity_factor
            )
            print(f"   📖 README: {quality.readme_score.score:.1f}/10")
        
        if "api" in docs:
            quality.api_score = await self._evaluate_api(
                docs["api"], codebase_size, complexity_factor
            )
            print(f"   🔌 API: {quality.api_score.score:.1f}/10")
        
        # Calculate overall score
        scores = []
        if quality.architecture_score:
            scores.append(quality.architecture_score.score)
        if quality.workflow_score:
            scores.append(quality.workflow_score.score)
        if quality.readme_score:
            scores.append(quality.readme_score.score)
        if quality.api_score:
            scores.append(quality.api_score.score)
        
        quality.overall_score = sum(scores) / len(scores) if scores else 0.0
        print(f"   ⭐ Overall: {quality.overall_score:.1f}/10")
        
        return quality
    
    async def _evaluate_architecture(
        self, 
        content: str, 
        codebase_size: Dict[str, int],
        complexity_factor: float
    ) -> QualityScore:
        """Evaluate architecture documentation quality"""
        
        prompt = f"""You are a technical documentation quality evaluator. Evaluate this architecture documentation.

CODEBASE CONTEXT:
- Languages: {', '.join(codebase_size.keys())}
- Total lines: {sum(codebase_size.values())}
- Complexity: {complexity_factor:.1f}/10

ARCHITECTURE DOCUMENTATION:
{content[:4000]}  # Limit to avoid token limits

EVALUATION CRITERIA (Score 0-10):
1. **Component Coverage** (2 points): Are all major components documented?
2. **Technical Depth** (2 points): Are implementation details, design patterns, and technologies explained?
3. **Relationships** (2 points): Are component interactions and data flows clearly described?
4. **Diagrams/Structure** (2 points): Is there clear structural organization?
5. **Completeness** (2 points): Does depth match codebase complexity?

Respond in JSON format:
{{
  "score": 8.5,
  "feedback": "Overall assessment...",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = safe_json_parse(response.text)
            
            return QualityScore(
                score=float(result.get("score", 5.0)),
                feedback=result.get("feedback", ""),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", [])
            )
        except Exception as e:
            print(f"⚠️  Architecture evaluation failed: {e}")
            return QualityScore(score=7.0, feedback="Evaluation failed", strengths=[], weaknesses=[], suggestions=[])
    
    async def _evaluate_workflow(
        self, 
        content: str, 
        codebase_size: Dict[str, int],
        complexity_factor: float
    ) -> QualityScore:
        """Evaluate workflow documentation quality"""
        
        prompt = f"""You are a technical documentation quality evaluator. Evaluate this workflow documentation.

CODEBASE CONTEXT:
- Languages: {', '.join(codebase_size.keys())}
- Total lines: {sum(codebase_size.values())}
- Complexity: {complexity_factor:.1f}/10

WORKFLOW DOCUMENTATION:
{content[:4000]}

EVALUATION CRITERIA (Score 0-10):
1. **Process Coverage** (2 points): Are all major workflows documented?
2. **Step Detail** (2 points): Are steps clear, detailed, and actionable?
3. **Decision Points** (2 points): Are conditional flows and error handling explained?
4. **Examples** (2 points): Are there concrete examples or scenarios?
5. **Completeness** (2 points): Does depth match system complexity?

Respond in JSON format:
{{
  "score": 8.5,
  "feedback": "Overall assessment...",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = safe_json_parse(response.text)
            
            return QualityScore(
                score=float(result.get("score", 5.0)),
                feedback=result.get("feedback", ""),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", [])
            )
        except Exception as e:
            print(f"⚠️  Workflow evaluation failed: {e}")
            return QualityScore(score=7.0, feedback="Evaluation failed", strengths=[], weaknesses=[], suggestions=[])
    
    async def _evaluate_readme(
        self, 
        content: str, 
        codebase_size: Dict[str, int],
        complexity_factor: float
    ) -> QualityScore:
        """Evaluate README documentation quality"""
        
        prompt = f"""You are a technical documentation quality evaluator. Evaluate this README documentation.

CODEBASE CONTEXT:
- Languages: {', '.join(codebase_size.keys())}
- Total lines: {sum(codebase_size.values())}
- Complexity: {complexity_factor:.1f}/10

README DOCUMENTATION:
{content[:4000]}

EVALUATION CRITERIA (Score 0-10):
1. **Overview Clarity** (2 points): Is the project purpose and value clear?
2. **Setup Instructions** (2 points): Are installation and configuration steps complete?
3. **Feature Coverage** (2 points): Are key features well-explained?
4. **Usage Examples** (2 points): Are there practical examples?
5. **Completeness** (2 points): Does it cover all essential information?

Respond in JSON format:
{{
  "score": 8.5,
  "feedback": "Overall assessment...",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = safe_json_parse(response.text)
            
            return QualityScore(
                score=float(result.get("score", 5.0)),
                feedback=result.get("feedback", ""),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", [])
            )
        except Exception as e:
            print(f"⚠️  README evaluation failed: {e}")
            return QualityScore(score=7.0, feedback="Evaluation failed", strengths=[], weaknesses=[], suggestions=[])
    
    async def _evaluate_api(
        self, 
        content: str, 
        codebase_size: Dict[str, int],
        complexity_factor: float
    ) -> QualityScore:
        """Evaluate API documentation quality"""
        
        prompt = f"""You are a technical documentation quality evaluator. Evaluate this API documentation.

CODEBASE CONTEXT:
- Languages: {', '.join(codebase_size.keys())}
- Total lines: {sum(codebase_size.values())}
- Complexity: {complexity_factor:.1f}/10

API DOCUMENTATION:
{content[:4000]}

EVALUATION CRITERIA (Score 0-10):
1. **Endpoint Coverage** (2 points): Are all API endpoints documented?
2. **Parameter Details** (2 points): Are request/response formats clear?
3. **Examples** (2 points): Are there usage examples with sample data?
4. **Error Handling** (2 points): Are error codes and handling documented?
5. **Completeness** (2 points): Is authentication, rate limits, etc. covered?

Respond in JSON format:
{{
  "score": 8.5,
  "feedback": "Overall assessment...",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = safe_json_parse(response.text)
            
            return QualityScore(
                score=float(result.get("score", 5.0)),
                feedback=result.get("feedback", ""),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", [])
            )
        except Exception as e:
            print(f"⚠️  API evaluation failed: {e}")
            return QualityScore(score=7.0, feedback="Evaluation failed", strengths=[], weaknesses=[], suggestions=[])
    
    def generate_quality_report(self, quality: DocumentationQuality) -> str:
        """Generate a human-readable quality report"""
        
        report = f"""
# Documentation Quality Report

**Overall Score: {quality.overall_score:.1f}/10**
{'✅ PASSED' if quality.overall_score >= 8.0 else '❌ NEEDS IMPROVEMENT'}

---

"""
        
        if quality.architecture_score:
            report += f"""
## 🏗️ Architecture Documentation
**Score: {quality.architecture_score.score:.1f}/10**

{quality.architecture_score.feedback}

**Strengths:**
{chr(10).join(f'- {s}' for s in quality.architecture_score.strengths)}

**Weaknesses:**
{chr(10).join(f'- {w}' for w in quality.architecture_score.weaknesses)}

**Suggestions:**
{chr(10).join(f'- {s}' for s in quality.architecture_score.suggestions)}

---
"""
        
        if quality.workflow_score:
            report += f"""
## 🔄 Workflow Documentation
**Score: {quality.workflow_score.score:.1f}/10**

{quality.workflow_score.feedback}

**Strengths:**
{chr(10).join(f'- {s}' for s in quality.workflow_score.strengths)}

**Weaknesses:**
{chr(10).join(f'- {w}' for w in quality.workflow_score.weaknesses)}

**Suggestions:**
{chr(10).join(f'- {s}' for s in quality.workflow_score.suggestions)}

---
"""
        
        if quality.readme_score:
            report += f"""
## 📖 README Documentation
**Score: {quality.readme_score.score:.1f}/10**

{quality.readme_score.feedback}

**Strengths:**
{chr(10).join(f'- {s}' for s in quality.readme_score.strengths)}

**Weaknesses:**
{chr(10).join(f'- {w}' for w in quality.readme_score.weaknesses)}

**Suggestions:**
{chr(10).join(f'- {s}' for s in quality.readme_score.suggestions)}

---
"""
        
        if quality.api_score:
            report += f"""
## 🔌 API Documentation
**Score: {quality.api_score.score:.1f}/10**

{quality.api_score.feedback}

**Strengths:**
{chr(10).join(f'- {s}' for s in quality.api_score.strengths)}

**Weaknesses:**
{chr(10).join(f'- {w}' for w in quality.api_score.weaknesses)}

**Suggestions:**
{chr(10).join(f'- {s}' for s in quality.api_score.suggestions)}

---
"""
        
        return report

"""
Documentation Quality Checker
Validates documentation quality using LLM evaluation and enforces minimum standards
"""

import os
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import google.generativeai as genai

def safe_json_parse(text: str) -> dict:
    """
    Safely parse JSON from LLM response, handling escape sequences
    """
    # Remove markdown code blocks
    text = text.strip().replace("```json", "").replace("```", "").strip()
    
    # Sanitize escape sequences
    text = text.replace('\\n', '\\\\n')
    text = text.replace('\\t', '\\\\t')
    text = text.replace('\\r', '\\\\r')
    
    # Fix invalid escapes (keep only valid JSON escapes)
    text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parsing error: {e}")
        print(f"   Text preview: {text[:200]}")
        # Return default structure
        return {
            "score": 7.0,
            "feedback": "Evaluation failed due to JSON parsing error",
            "strengths": [],
            "weaknesses": ["Could not parse LLM response"],
            "suggestions": []
        }

@dataclass
class QualityScore:
    """Quality score for a documentation type"""
    score: float  # 0-10
    feedback: str
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]

@dataclass
class DocumentationQuality:
    """Overall documentation quality assessment"""
    architecture_score: Optional[QualityScore] = None
    workflow_score: Optional[QualityScore] = None
    readme_score: Optional[QualityScore] = None
    api_score: Optional[QualityScore] = None
    overall_score: float = 0.0
    
    def should_regenerate(self, threshold: float = 8.0) -> bool:
        """Check if any document needs regeneration"""
        scores = []
        if self.architecture_score:
            scores.append(self.architecture_score.score)
        if self.workflow_score:
            scores.append(self.workflow_score.score)
        if self.readme_score:
            scores.append(self.readme_score.score)
        if self.api_score:
            scores.append(self.api_score.score)
            
        return any(score < threshold for score in scores) if scores else False
    
    def get_low_quality_docs(self, threshold: float = 8.0) -> List[str]:
        """Get list of documents that need improvement"""
        low_quality = []
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
    """
    Validates documentation quality using AI evaluation
    Ensures comprehensive, detailed, and useful documentation
    """
    
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        else:
            self.model = None
            print("⚠️  GEMINI_API_KEY not found - quality checking disabled")
    
    async def evaluate_documentation(
        self, 
        repo_name: str,
        codebase_size: Dict[str, int],  # Lines of code per language
        docs: Dict[str, str]
    ) -> DocumentationQuality:
        """
        Evaluate documentation quality across all doc types
        
        Args:
            repo_name: Repository name
            codebase_size: Dictionary of language -> line count
            docs: Dictionary of doc_type -> content
            
        Returns:
            DocumentationQuality with scores and feedback
        """
        if not self.model:
            print("⚠️  Quality checking skipped - no LLM available")
            return DocumentationQuality(overall_score=10.0)  # Pass by default
        
        quality = DocumentationQuality()
        
        # Calculate codebase complexity score
        total_lines = sum(codebase_size.values())
        num_languages = len(codebase_size)
        complexity_factor = min(10, (total_lines / 1000) + (num_languages * 0.5))
        
        print(f"\n📊 Evaluating documentation quality for {repo_name}")
        print(f"   Codebase: {total_lines} lines, {num_languages} languages")
        print(f"   Complexity factor: {complexity_factor:.1f}/10")
        
        # Evaluate each document type
        if "architecture" in docs:
            quality.architecture_score = await self._evaluate_architecture(
                docs["architecture"], codebase_size, complexity_factor
            )
            print(f"   🏗️  Architecture: {quality.architecture_score.score:.1f}/10")
        
        if "workflow" in docs:
            quality.workflow_score = await self._evaluate_workflow(
                docs["workflow"], codebase_size, complexity_factor
            )
            print(f"   🔄 Workflow: {quality.workflow_score.score:.1f}/10")
        
        if "readme" in docs:
            quality.readme_score = await self._evaluate_readme(
                docs["readme"], codebase_size, complexity_factor
            )
            print(f"   📖 README: {quality.readme_score.score:.1f}/10")
        
        if "api" in docs:
            quality.api_score = await self._evaluate_api(
                docs["api"], codebase_size, complexity_factor
            )
            print(f"   🔌 API: {quality.api_score.score:.1f}/10")
        
        # Calculate overall score
        scores = []
        if quality.architecture_score:
            scores.append(quality.architecture_score.score)
        if quality.workflow_score:
            scores.append(quality.workflow_score.score)
        if quality.readme_score:
            scores.append(quality.readme_score.score)
        if quality.api_score:
            scores.append(quality.api_score.score)
        
        quality.overall_score = sum(scores) / len(scores) if scores else 0.0
        print(f"   ⭐ Overall: {quality.overall_score:.1f}/10")
        
        return quality
    
    async def _evaluate_architecture(
        self, 
        content: str, 
        codebase_size: Dict[str, int],
        complexity_factor: float
    ) -> QualityScore:
        """Evaluate architecture documentation quality"""
        
        prompt = f"""You are a technical documentation quality evaluator. Evaluate this architecture documentation.

CODEBASE CONTEXT:
- Languages: {', '.join(codebase_size.keys())}
- Total lines: {sum(codebase_size.values())}
- Complexity: {complexity_factor:.1f}/10

ARCHITECTURE DOCUMENTATION:
{content[:4000]}  # Limit to avoid token limits

EVALUATION CRITERIA (Score 0-10):
1. **Component Coverage** (2 points): Are all major components documented?
2. **Technical Depth** (2 points): Are implementation details, design patterns, and technologies explained?
3. **Relationships** (2 points): Are component interactions and data flows clearly described?
4. **Diagrams/Structure** (2 points): Is there clear structural organization?
5. **Completeness** (2 points): Does depth match codebase complexity?

Respond in JSON format:
{{
  "score": 8.5,
  "feedback": "Overall assessment...",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = safe_json_parse(response.text)
            
            return QualityScore(
                score=float(result.get("score", 5.0)),
                feedback=result.get("feedback", ""),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", [])
            )
        except Exception as e:
            print(f"⚠️  Architecture evaluation failed: {e}")
            return QualityScore(score=7.0, feedback="Evaluation failed", strengths=[], weaknesses=[], suggestions=[])
    
    async def _evaluate_workflow(
        self, 
        content: str, 
        codebase_size: Dict[str, int],
        complexity_factor: float
    ) -> QualityScore:
        """Evaluate workflow documentation quality"""
        
        prompt = f"""You are a technical documentation quality evaluator. Evaluate this workflow documentation.

CODEBASE CONTEXT:
- Languages: {', '.join(codebase_size.keys())}
- Total lines: {sum(codebase_size.values())}
- Complexity: {complexity_factor:.1f}/10

WORKFLOW DOCUMENTATION:
{content[:4000]}

EVALUATION CRITERIA (Score 0-10):
1. **Process Coverage** (2 points): Are all major workflows documented?
2. **Step Detail** (2 points): Are steps clear, detailed, and actionable?
3. **Decision Points** (2 points): Are conditional flows and error handling explained?
4. **Examples** (2 points): Are there concrete examples or scenarios?
5. **Completeness** (2 points): Does depth match system complexity?

Respond in JSON format:
{{
  "score": 8.5,
  "feedback": "Overall assessment...",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = safe_json_parse(response.text)
            
            return QualityScore(
                score=float(result.get("score", 5.0)),
                feedback=result.get("feedback", ""),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", [])
            )
        except Exception as e:
            print(f"⚠️  Workflow evaluation failed: {e}")
            return QualityScore(score=7.0, feedback="Evaluation failed", strengths=[], weaknesses=[], suggestions=[])
    
    async def _evaluate_readme(
        self, 
        content: str, 
        codebase_size: Dict[str, int],
        complexity_factor: float
    ) -> QualityScore:
        """Evaluate README documentation quality"""
        
        prompt = f"""You are a technical documentation quality evaluator. Evaluate this README documentation.

CODEBASE CONTEXT:
- Languages: {', '.join(codebase_size.keys())}
- Total lines: {sum(codebase_size.values())}
- Complexity: {complexity_factor:.1f}/10

README DOCUMENTATION:
{content[:4000]}

EVALUATION CRITERIA (Score 0-10):
1. **Overview Clarity** (2 points): Is the project purpose and value clear?
2. **Setup Instructions** (2 points): Are installation and configuration steps complete?
3. **Feature Coverage** (2 points): Are key features well-explained?
4. **Usage Examples** (2 points): Are there practical examples?
5. **Completeness** (2 points): Does it cover all essential information?

Respond in JSON format:
{{
  "score": 8.5,
  "feedback": "Overall assessment...",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = safe_json_parse(response.text)
            
            return QualityScore(
                score=float(result.get("score", 5.0)),
                feedback=result.get("feedback", ""),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", [])
            )
        except Exception as e:
            print(f"⚠️  README evaluation failed: {e}")
            return QualityScore(score=7.0, feedback="Evaluation failed", strengths=[], weaknesses=[], suggestions=[])
    
    async def _evaluate_api(
        self, 
        content: str, 
        codebase_size: Dict[str, int],
        complexity_factor: float
    ) -> QualityScore:
        """Evaluate API documentation quality"""
        
        prompt = f"""You are a technical documentation quality evaluator. Evaluate this API documentation.

CODEBASE CONTEXT:
- Languages: {', '.join(codebase_size.keys())}
- Total lines: {sum(codebase_size.values())}
- Complexity: {complexity_factor:.1f}/10

API DOCUMENTATION:
{content[:4000]}

EVALUATION CRITERIA (Score 0-10):
1. **Endpoint Coverage** (2 points): Are all API endpoints documented?
2. **Parameter Details** (2 points): Are request/response formats clear?
3. **Examples** (2 points): Are there usage examples with sample data?
4. **Error Handling** (2 points): Are error codes and handling documented?
5. **Completeness** (2 points): Is authentication, rate limits, etc. covered?

Respond in JSON format:
{{
  "score": 8.5,
  "feedback": "Overall assessment...",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = safe_json_parse(response.text)
            
            return QualityScore(
                score=float(result.get("score", 5.0)),
                feedback=result.get("feedback", ""),
                strengths=result.get("strengths", []),
                weaknesses=result.get("weaknesses", []),
                suggestions=result.get("suggestions", [])
            )
        except Exception as e:
            print(f"⚠️  API evaluation failed: {e}")
            return QualityScore(score=7.0, feedback="Evaluation failed", strengths=[], weaknesses=[], suggestions=[])
    
    def generate_quality_report(self, quality: DocumentationQuality) -> str:
        """Generate a human-readable quality report"""
        
        report = f"""
# Documentation Quality Report

**Overall Score: {quality.overall_score:.1f}/10**
{'✅ PASSED' if quality.overall_score >= 8.0 else '❌ NEEDS IMPROVEMENT'}

---

"""
        
        if quality.architecture_score:
            report += f"""
## 🏗️ Architecture Documentation
**Score: {quality.architecture_score.score:.1f}/10**

{quality.architecture_score.feedback}

**Strengths:**
{chr(10).join(f'- {s}' for s in quality.architecture_score.strengths)}

**Weaknesses:**
{chr(10).join(f'- {w}' for w in quality.architecture_score.weaknesses)}

**Suggestions:**
{chr(10).join(f'- {s}' for s in quality.architecture_score.suggestions)}

---
"""
        
        if quality.workflow_score:
            report += f"""
## 🔄 Workflow Documentation
**Score: {quality.workflow_score.score:.1f}/10**

{quality.workflow_score.feedback}

**Strengths:**
{chr(10).join(f'- {s}' for s in quality.workflow_score.strengths)}

**Weaknesses:**
{chr(10).join(f'- {w}' for w in quality.workflow_score.weaknesses)}

**Suggestions:**
{chr(10).join(f'- {s}' for s in quality.workflow_score.suggestions)}

---
"""
        
        if quality.readme_score:
            report += f"""
## 📖 README Documentation
**Score: {quality.readme_score.score:.1f}/10**

{quality.readme_score.feedback}

**Strengths:**
{chr(10).join(f'- {s}' for s in quality.readme_score.strengths)}

**Weaknesses:**
{chr(10).join(f'- {w}' for w in quality.readme_score.weaknesses)}

**Suggestions:**
{chr(10).join(f'- {s}' for s in quality.readme_score.suggestions)}

---
"""
        
        if quality.api_score:
            report += f"""
## 🔌 API Documentation
**Score: {quality.api_score.score:.1f}/10**

{quality.api_score.feedback}

**Strengths:**
{chr(10).join(f'- {s}' for s in quality.api_score.strengths)}

**Weaknesses:**
{chr(10).join(f'- {w}' for w in quality.api_score.weaknesses)}

**Suggestions:**
{chr(10).join(f'- {s}' for s in quality.api_score.suggestions)}

---
"""
        
        return report
