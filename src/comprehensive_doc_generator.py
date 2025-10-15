"""
Comprehensive Documentation Generator for DocAI
Ensures high-quality, complete documentation for all repositories
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from llm_provider_v2 import get_rotator

def check_documentation_quality(repo_dir):
    """
    Check if existing documentation is comprehensive and worthy
    Returns dict with quality scores and what needs to be generated
    """
    docs_dir = Path(repo_dir) / "docs"
    
    quality_report = {
        "summary_exists": False,
        "summary_quality": 0,  # 0-10 scale
        "architecture_exists": False,
        "architecture_quality": 0,
        "workflow_exists": False,
        "workflow_quality": 0,
        "api_exists": False,
        "api_quality": 0,
        "needs_generation": []
    }
    
    # Check SUMMARY.md or README.md
    summary_files = [
        docs_dir / "SUMMARY.md",
        docs_dir / "README.md",
        Path(repo_dir) / "README.md"
    ]
    
    for summary_file in summary_files:
        if summary_file.exists():
            content = summary_file.read_text()
            quality_report["summary_exists"] = True
            quality_report["summary_quality"] = assess_content_quality(
                content, "summary"
            )
            break
    
    # Check architecture documentation
    arch_files = [
        docs_dir / "architecture.md",
        docs_dir / "ARCHITECTURE.md",
        docs_dir / "architecture" / "current.md"
    ]
    
    for arch_file in arch_files:
        if arch_file.exists():
            content = arch_file.read_text()
            quality_report["architecture_exists"] = True
            quality_report["architecture_quality"] = assess_content_quality(
                content, "architecture"
            )
            break
    
    # Check workflow documentation
    workflow_files = [
        docs_dir / "workflow.md",
        docs_dir / "WORKFLOW.md",
        docs_dir / "workflow" / "current.md"
    ]
    
    for workflow_file in workflow_files:
        if workflow_file.exists():
            content = workflow_file.read_text()
            quality_report["workflow_exists"] = True
            quality_report["workflow_quality"] = assess_content_quality(
                content, "workflow"
            )
            break
    
    # Check API documentation
    api_files = [
        docs_dir / "api.md",
        docs_dir / "API.md",
        docs_dir / "api" / "README.md"
    ]
    
    for api_file in api_files:
        if api_file.exists():
            content = api_file.read_text()
            quality_report["api_exists"] = True
            quality_report["api_quality"] = assess_content_quality(
                content, "api"
            )
            break
    
    # Determine what needs generation (quality < 7)
    if not quality_report["summary_exists"] or quality_report["summary_quality"] < 7:
        quality_report["needs_generation"].append("summary")
    
    if not quality_report["architecture_exists"] or quality_report["architecture_quality"] < 7:
        quality_report["needs_generation"].append("architecture")
    
    if not quality_report["workflow_exists"] or quality_report["workflow_quality"] < 7:
        quality_report["needs_generation"].append("workflow")
    
    if not quality_report["api_exists"] or quality_report["api_quality"] < 7:
        quality_report["needs_generation"].append("api")
    
    return quality_report


def assess_content_quality(content, doc_type):
    """
    Use LLM to assess documentation quality
    Returns score 0-10
    """
    if len(content.strip()) < 100:
        return 2  # Too short
    
    # Quick heuristic checks
    score = 5  # Base score
    
    # Check for headings
    if "##" in content or "# " in content:
        score += 1
    
    # Check for code blocks
    if "```" in content:
        score += 1
    
    # Check for lists
    if "- " in content or "* " in content or "1. " in content:
        score += 1
    
    # Check length (comprehensive docs are longer)
    if len(content) > 1000:
        score += 1
    if len(content) > 3000:
        score += 1
    
    # Use LLM for deeper quality assessment
    try:
        rotator = get_rotator()
        
        quality_prompt = f"""
Assess the quality of this {doc_type} documentation on a scale of 0-10.

DOCUMENTATION CONTENT:
{content[:2000]}

QUALITY CRITERIA:
- Clarity and completeness
- Technical depth
- Proper structure
- Useful examples
- Up-to-date information

Respond with ONLY a number 0-10, nothing else.
"""
        
        response = rotator.generate_with_rotation(quality_prompt)
        if response:
            try:
                llm_score = float(response.strip())
                # Average heuristic and LLM scores
                final_score = (score + llm_score) / 2
                return min(10, max(0, final_score))
            except ValueError:
                print(f"Warning: Could not parse LLM score: {response}")
                return score
        else:
            print("Warning: LLM returned no response for quality assessment")
            return score
        
    except Exception as e:
        print(f"Warning: LLM quality assessment failed: {e}")
        return score


def get_current_version(docs_dir, doc_type):
    """
    Get the current version number for architecture/workflow docs
    Returns the next version number to create
    """
    version_dir = docs_dir / doc_type
    
    if not version_dir.exists():
        return 1
    
    # Find existing version files
    version_files = list(version_dir.glob("v*-*.md"))
    
    if not version_files:
        return 1
    
    # Extract version numbers
    versions = []
    for vf in version_files:
        try:
            version_num = int(vf.stem.split("-")[0][1:])  # Extract number from v1, v2, etc.
            versions.append(version_num)
        except:
            continue
    
    return max(versions) + 1 if versions else 1


def analyze_architectural_impact(repo_dir, changed_files, analysis):
    """
    Determine if changes warrant a new architecture/workflow version
    Returns dict with versioning decisions
    """
    versioning_decision = {
        "needs_new_architecture_version": False,
        "needs_new_workflow_version": False,
        "architecture_change_reason": "",
        "workflow_change_reason": ""
    }
    
    # Major indicators for architectural changes
    arch_indicators = [
        any("database" in f.lower() for f in changed_files),
        any("schema" in f.lower() for f in changed_files),
        any("model" in f.lower() for f in changed_files),
        any("architecture" in f.lower() for f in changed_files),
        analysis.get("type") == "breaking_change",
        len(changed_files) > 30,
        "database" in analysis.get("impact_scope", []),
        "architecture" in analysis.get("impact_scope", [])
    ]
    
    # Major indicators for workflow changes
    workflow_indicators = [
        any("workflow" in f.lower() for f in changed_files),
        any("pipeline" in f.lower() for f in changed_files),
        any("process" in f.lower() for f in changed_files),
        "workflow" in analysis.get("impact_scope", []),
        "deployment" in analysis.get("impact_scope", [])
    ]
    
    if any(arch_indicators):
        versioning_decision["needs_new_architecture_version"] = True
        versioning_decision["architecture_change_reason"] = (
            f"Major architectural change detected: {analysis.get('title', 'Unknown')}"
        )
    
    if any(workflow_indicators):
        versioning_decision["needs_new_workflow_version"] = True
        versioning_decision["workflow_change_reason"] = (
            f"Major workflow change detected: {analysis.get('title', 'Unknown')}"
        )
    
    return versioning_decision


def generate_comprehensive_documentation(repo_dir, analysis, changed_files):
    """
    Generate comprehensive documentation for the repository
    This is the main orchestrator function
    """
    docs_dir = Path(repo_dir) / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    print("📊 Checking documentation quality...")
    quality_report = check_documentation_quality(repo_dir)
    
    print(f"📋 Quality Report: {json.dumps(quality_report, indent=2)}")
    
    # Generate missing or low-quality documentation
    if "summary" in quality_report["needs_generation"]:
        print("📝 Generating comprehensive README/Summary...")
        generate_comprehensive_summary(repo_dir, docs_dir, analysis)
    
    # Check if we need new versions for architecture/workflow
    versioning = analyze_architectural_impact(repo_dir, changed_files, analysis)
    
    if "architecture" in quality_report["needs_generation"] or versioning["needs_new_architecture_version"]:
        print("🏗️  Generating architecture documentation...")
        generate_versioned_architecture(repo_dir, docs_dir, analysis, versioning)
    
    if "workflow" in quality_report["needs_generation"] or versioning["needs_new_workflow_version"]:
        print("🔄 Generating workflow documentation...")
        generate_versioned_workflow(repo_dir, docs_dir, analysis, versioning)
    
    if "api" in quality_report["needs_generation"]:
        print("📡 Generating API documentation...")
        generate_api_documentation(repo_dir, docs_dir, analysis)
    
    # Always update SUMMARY.md for navigation
    update_summary_navigation(docs_dir)
    
    print("✅ Comprehensive documentation generation complete!")


def generate_comprehensive_summary(repo_dir, docs_dir, analysis):
    """Generate a comprehensive README/Summary for the repository"""
    
    # Analyze the entire codebase
    codebase_analysis = analyze_full_codebase(repo_dir)
    
    rotator = get_rotator()
    
    summary_prompt = f"""
You are DocAI, an expert technical writer. Create a comprehensive README/Summary for this repository.

CODEBASE ANALYSIS:
{json.dumps(codebase_analysis, indent=2)}

RECENT CHANGES:
{json.dumps(analysis, indent=2)}

Create a professional, comprehensive README.md that includes:

# [Project Name]

## Overview
- What is this project?
- What problem does it solve?
- Key features and capabilities

## Architecture
- High-level system design
- Main components and their roles
- Technology stack

## Getting Started
### Prerequisites
### Installation
### Quick Start

## Usage
- Basic usage examples
- Common workflows
- Configuration options

## Project Structure
```
/
├── src/
├── docs/
└── ...
```

## API Overview
- Key endpoints/modules
- Main interfaces

## Development
- How to contribute
- Development setup
- Testing

## Documentation
- Link to detailed docs
- Architecture docs
- API reference

## License & Contact

Make it professional, clear, and comprehensive. Use proper markdown formatting.
"""
    
    try:
        print("🔄 Generating comprehensive summary with LLM...")
        summary_content = rotator.generate_with_rotation(summary_prompt)
        
        if not summary_content or len(summary_content.strip()) < 100:
            print("❌ LLM returned insufficient content for summary")
            return
        
        # Save to both docs/SUMMARY.md and root README.md
        summary_file = docs_dir / "SUMMARY.md"
        summary_file.write_text(summary_content)
        print(f"✅ Created {summary_file}")
        
        # Also update root README if it doesn't exist or is poor quality
        readme_file = Path(repo_dir) / "README.md"
        if not readme_file.exists() or len(readme_file.read_text()) < 500:
            readme_file.write_text(summary_content)
            print(f"✅ Updated {readme_file}")
            
    except Exception as e:
        print(f"❌ Failed to generate summary: {e}")
        import traceback
        traceback.print_exc()


def generate_versioned_architecture(repo_dir, docs_dir, analysis, versioning):
    """Generate versioned architecture documentation"""
    
    arch_dir = docs_dir / "architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    
    version = get_current_version(docs_dir, "architecture")
    
    # Analyze architecture
    arch_analysis = analyze_architecture(repo_dir)
    
    rotator = get_rotator()
    
    arch_prompt = f"""
You are DocAI, an expert system architect. Create comprehensive architecture documentation.

VERSION: v{version}
REASON FOR NEW VERSION: {versioning.get('architecture_change_reason', 'Initial documentation')}

CODEBASE ANALYSIS:
{json.dumps(arch_analysis, indent=2)}

RECENT CHANGES:
{json.dumps(analysis, indent=2)}

Create detailed architecture documentation that includes:

# Architecture v{version}

## System Overview
- High-level architecture diagram (MUST include ASCII/text diagram)
- Core components and their relationships
- Data flow

**IMPORTANT**: You MUST include an ASCII art diagram showing the system architecture.
Use boxes, arrows, and clear labels. Example format:
```
+-------------------+      HTTP      +-------------------+
|     Frontend      |<-------------->|     Backend       |
+-------------------+                +-------------------+
                                             |
                                             | Database
                                             v
                                     +-------------------+
                                     |     Database      |
                                     +-------------------+
```

## Component Details
### [Component 1]
- Purpose
- Responsibilities
- Interfaces
- Dependencies

### [Component 2]
...

## Technology Stack
- Languages and frameworks
- Databases and storage
- External services
- Infrastructure

## Design Patterns
- Patterns used
- Why they were chosen

## Scalability & Performance
- How the system scales
- Performance considerations

## Security Architecture
- Authentication/Authorization
- Data protection
- Security measures

## Deployment Architecture
- Deployment model
- Infrastructure requirements

## Future Considerations
- Planned improvements
- Known limitations

Make it technical, detailed, and professional.
"""
    
    try:
        print(f"🔄 Generating architecture v{version} with LLM...")
        arch_content = rotator.generate_with_rotation(arch_prompt)
        
        if not arch_content or len(arch_content.strip()) < 100:
            print("❌ LLM returned insufficient content for architecture")
            return
        
        # Save versioned file
        arch_file = arch_dir / f"v{version}-architecture.md"
        arch_file.write_text(arch_content)
        print(f"✅ Created {arch_file}")
        
        # Also create/update current.md symlink or copy
        current_file = arch_dir / "current.md"
        current_file.write_text(arch_content)
        print(f"✅ Updated {current_file}")
        
    except Exception as e:
        print(f"❌ Failed to generate architecture: {e}")
        import traceback
        traceback.print_exc()


def generate_versioned_workflow(repo_dir, docs_dir, analysis, versioning):
    """Generate versioned workflow documentation"""
    
    workflow_dir = docs_dir / "workflow"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    version = get_current_version(docs_dir, "workflow")
    
    # Analyze workflows
    workflow_analysis = analyze_workflows(repo_dir)
    
    rotator = get_rotator()
    
    workflow_prompt = f"""
You are DocAI, an expert process analyst. Create comprehensive workflow documentation.

VERSION: v{version}
REASON FOR NEW VERSION: {versioning.get('workflow_change_reason', 'Initial documentation')}

WORKFLOW ANALYSIS:
{json.dumps(workflow_analysis, indent=2)}

RECENT CHANGES:
{json.dumps(analysis, indent=2)}

Create detailed workflow documentation that includes:

# Workflow v{version}

**IMPORTANT**: You MUST include workflow diagrams using ASCII art or flowchart notation.
Example format:
```
Developer → Create Branch → Code → Test → PR → Review → Merge → Deploy
                                                  ↓
                                              Feedback
                                                  ↓
                                              Fix Issues
```

## Development Workflow
### Setup
1. Clone repository
2. Install dependencies
3. Configure environment

### Development Process (with diagram)
```
[Start] → [Create Branch] → [Code] → [Test] → [PR] → [Review] → [Merge]
                                         ↓                ↓
                                      [Failed]        [Changes]
                                         ↓                ↓
                                      [Fix] ←----------[Fix]
```

1. Create feature branch
2. Implement changes
3. Write tests
4. Submit PR

### Code Review Process
- Review guidelines
- Approval process

## Deployment Workflow
### Staging Deployment
- Steps
- Validation

### Production Deployment
- Steps
- Rollback procedure

## CI/CD Pipeline
- Build process
- Testing stages
- Deployment stages

## Release Process
- Version management
- Release notes
- Communication

## Monitoring & Maintenance
- Health checks
- Logging
- Incident response

## Common Tasks
### Task 1: [Description]
Steps...

### Task 2: [Description]
Steps...

Make it practical, step-by-step, and easy to follow.
"""
    
    try:
        print(f"🔄 Generating workflow v{version} with LLM...")
        workflow_content = rotator.generate_with_rotation(workflow_prompt)
        
        if not workflow_content or len(workflow_content.strip()) < 100:
            print("❌ LLM returned insufficient content for workflow")
            return
        
        # Save versioned file
        workflow_file = workflow_dir / f"v{version}-workflow.md"
        workflow_file.write_text(workflow_content)
        print(f"✅ Created {workflow_file}")
        
        # Also create/update current.md
        current_file = workflow_dir / "current.md"
        current_file.write_text(workflow_content)
        print(f"✅ Updated {current_file}")
        
    except Exception as e:
        print(f"❌ Failed to generate workflow: {e}")
        import traceback
        traceback.print_exc()


def generate_api_documentation(repo_dir, docs_dir, analysis):
    """Generate comprehensive API documentation"""
    
    # Analyze API endpoints/modules
    api_analysis = analyze_api_structure(repo_dir)
    
    rotator = get_rotator()
    
    api_prompt = f"""
You are DocAI, an expert API documentation writer. Create comprehensive API documentation.

API ANALYSIS:
{json.dumps(api_analysis, indent=2)}

RECENT CHANGES:
{json.dumps(analysis, indent=2)}

Create detailed API documentation that includes:

# API Documentation

## Overview
- API purpose
- Base URL
- Authentication

## Endpoints

### Endpoint 1: [Method] /path
**Description**: What it does

**Request**:
```json
{{
  "param1": "value"
}}
```

**Response**:
```json
{{
  "result": "data"
}}
```

**Errors**:
- 400: Bad Request
- 401: Unauthorized

### Endpoint 2: [Method] /path
...

## Data Models
### Model 1
```json
{{
  "field1": "type",
  "field2": "type"
}}
```

## Authentication
- How to authenticate
- Token management

## Rate Limiting
- Limits
- Headers

## Examples
### Example 1: [Use Case]
```bash
curl -X POST ...
```

## SDKs & Libraries
- Available SDKs
- Usage examples

Make it clear, complete, and developer-friendly.
"""
    
    try:
        print("🔄 Generating API documentation with LLM...")
        api_content = rotator.generate_with_rotation(api_prompt)
        
        if not api_content or len(api_content.strip()) < 100:
            print("❌ LLM returned insufficient content for API docs")
            return
        
        api_file = docs_dir / "api.md"
        api_file.write_text(api_content)
        print(f"✅ Created {api_file}")
        
    except Exception as e:
        print(f"❌ Failed to generate API docs: {e}")
        import traceback
        traceback.print_exc()


def analyze_full_codebase(repo_dir):
    """Analyze the entire codebase structure"""
    analysis = {
        "project_name": Path(repo_dir).name,
        "file_count": 0,
        "languages": [],
        "main_directories": [],
        "dependencies": {},
        "entry_points": []
    }
    
    try:
        # Count files
        result = subprocess.run(
            "find . -type f | wc -l",
            shell=True, cwd=repo_dir, capture_output=True, text=True
        )
        analysis["file_count"] = int(result.stdout.strip())
        
        # Detect languages
        for ext in [".py", ".js", ".ts", ".java", ".go", ".rs"]:
            result = subprocess.run(
                f"find . -name '*{ext}' | wc -l",
                shell=True, cwd=repo_dir, capture_output=True, text=True
            )
            count = int(result.stdout.strip())
            if count > 0:
                analysis["languages"].append(ext[1:])
        
        # Get directory structure
        result = subprocess.run(
            "find . -maxdepth 2 -type d | head -20",
            shell=True, cwd=repo_dir, capture_output=True, text=True
        )
        analysis["main_directories"] = result.stdout.strip().split("\n")
        
        # Check for dependency files
        for dep_file in ["package.json", "requirements.txt", "go.mod", "Cargo.toml"]:
            dep_path = Path(repo_dir) / dep_file
            if dep_path.exists():
                analysis["dependencies"][dep_file] = dep_path.read_text()[:500]
        
    except Exception as e:
        print(f"Warning: Codebase analysis error: {e}")
    
    return analysis


def analyze_architecture(repo_dir):
    """Analyze system architecture"""
    return {
        "components": analyze_components(repo_dir),
        "structure": analyze_full_codebase(repo_dir),
        "patterns": detect_design_patterns(repo_dir)
    }


def analyze_workflows(repo_dir):
    """Analyze development workflows"""
    workflows = {
        "has_ci_cd": False,
        "ci_files": [],
        "scripts": []
    }
    
    # Check for CI/CD files
    ci_files = [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci"]
    for ci_file in ci_files:
        if (Path(repo_dir) / ci_file).exists():
            workflows["has_ci_cd"] = True
            workflows["ci_files"].append(ci_file)
    
    # Check for scripts
    scripts_dir = Path(repo_dir) / "scripts"
    if scripts_dir.exists():
        workflows["scripts"] = [f.name for f in scripts_dir.iterdir() if f.is_file()]
    
    return workflows


def analyze_api_structure(repo_dir):
    """Analyze API structure"""
    api_info = {
        "has_api": False,
        "api_files": [],
        "framework": None
    }
    
    # Detect API framework
    frameworks = {
        "FastAPI": ["from fastapi", "FastAPI()"],
        "Flask": ["from flask", "Flask(__name__)"],
        "Express": ["express()", "require('express')"],
        "Django": ["django", "urls.py"]
    }
    
    try:
        for framework, patterns in frameworks.items():
            for pattern in patterns:
                result = subprocess.run(
                    f"grep -r '{pattern}' . --include='*.py' --include='*.js' | head -1",
                    shell=True, cwd=repo_dir, capture_output=True, text=True
                )
                if result.stdout:
                    api_info["has_api"] = True
                    api_info["framework"] = framework
                    break
            if api_info["framework"]:
                break
    except Exception as e:
        print(f"Warning: API analysis error: {e}")
    
    return api_info


def analyze_components(repo_dir):
    """Analyze system components"""
    # Simplified component detection
    return ["core", "api", "database", "frontend"]


def detect_design_patterns(repo_dir):
    """Detect design patterns in use"""
    # Simplified pattern detection
    return ["MVC", "Repository Pattern"]


def update_summary_navigation(docs_dir):
    """Update SUMMARY.md with proper navigation links"""
    
    summary_content = "# Summary\n\n"
    
    # Add main documentation links
    if (docs_dir / "SUMMARY.md").exists() or (docs_dir / "README.md").exists():
        summary_content += "* [Home](README.md)\n"
    
    # Add architecture versions
    arch_dir = docs_dir / "architecture"
    if arch_dir.exists():
        arch_files = sorted(arch_dir.glob("v*-architecture.md"), reverse=True)
        if arch_files:
            summary_content += "\n## Architecture\n"
            for arch_file in arch_files:
                version = arch_file.stem.split("-")[0]
                summary_content += f"* [{version.upper()} Architecture](architecture/{arch_file.name})\n"
    
    # Add workflow versions
    workflow_dir = docs_dir / "workflow"
    if workflow_dir.exists():
        workflow_files = sorted(workflow_dir.glob("v*-workflow.md"), reverse=True)
        if workflow_files:
            summary_content += "\n## Workflow\n"
            for workflow_file in workflow_files:
                version = workflow_file.stem.split("-")[0]
                summary_content += f"* [{version.upper()} Workflow](workflow/{workflow_file.name})\n"
    
    # Add API docs
    if (docs_dir / "api.md").exists():
        summary_content += "\n## API\n"
        summary_content += "* [API Documentation](api.md)\n"
    
    # Add changes
    changes_dir = docs_dir / "changes"
    if changes_dir.exists():
        change_files = sorted(changes_dir.glob("*.md"), reverse=True)
        if change_files:
            summary_content += "\n## Changes\n"
            for change_file in change_files[:10]:  # Latest 10
                # Extract title from filename
                title = change_file.stem.split("-", 1)[-1].replace("-", " ").title()
                summary_content += f"* [{title}](changes/{change_file.name})\n"
    
    # Save SUMMARY.md
    summary_file = docs_dir / "SUMMARY.md"
    summary_file.write_text(summary_content)
    print(f"✅ Updated {summary_file}")
