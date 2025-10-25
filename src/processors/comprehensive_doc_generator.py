"""
Comprehensive Documentation Generator for DocAI
Ensures high-quality, complete documentation for all repositories
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from utilities.llm_provider_v2 import get_rotator

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
    
    # Determine what needs generation (quality < 8 for regeneration)
    if not quality_report["summary_exists"] or quality_report["summary_quality"] < 8:
        quality_report["needs_generation"].append("summary")

    if not quality_report["architecture_exists"] or quality_report["architecture_quality"] < 8:
        quality_report["needs_generation"].append("architecture")

    if not quality_report["workflow_exists"] or quality_report["workflow_quality"] < 8:
        quality_report["needs_generation"].append("workflow")

    if not quality_report["api_exists"] or quality_report["api_quality"] < 8:
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
    Get the current version number using semantic versioning (v1.0, v1.1, v2.0)
    Returns the next version number to create

    This prevents excessive versioning by using proper semantic versioning
    """
    version_dir = docs_dir / doc_type

    if not version_dir.exists():
        return "1.0"  # Start with v1.0

    # Find existing version files
    version_files = list(version_dir.glob("v*-*.md"))

    if not version_files:
        return "1.0"

    # Extract version numbers and find the highest
    versions = []
    for vf in version_files:
        try:
            # Extract version from v1.0-architecture.md format
            version_str = vf.stem.split("-")[0][1:]  # Remove 'v' prefix
            if "." in version_str:
                # Semantic version (1.0, 1.1, 2.0)
                major, minor = version_str.split(".")
                versions.append((int(major), int(minor)))
            else:
                # Legacy version (1, 2, 3) - treat as major version
                versions.append((int(version_str), 0))
        except:
            continue

    if not versions:
        return "1.0"

    # Get the highest version
    max_major, max_minor = max(versions)

    # Return next minor version (v1.0 → v1.1, v1.9 → v2.0)
    if max_minor >= 9:
        return f"{max_major + 1}.0"
    else:
        return f"{max_major}.{max_minor + 1}"


def analyze_architectural_impact(repo_dir, changed_files, analysis):
    """
    Determine if changes warrant a new architecture/workflow version
    Uses semantic versioning (v1.0, v1.1, v2.0) instead of incremental numbers

    Only create new versions for TRULY significant architectural changes:
    - Major feature additions that change system architecture
    - Breaking changes that affect core components
    - Major refactoring of system structure
    - NOT for: bug fixes, minor features, documentation updates
    """
    versioning_decision = {
        "needs_new_architecture_version": False,
        "needs_new_workflow_version": False,
        "architecture_change_reason": "",
        "workflow_change_reason": ""
    }

    # STRICT criteria for architectural changes (only truly major changes)
    major_arch_indicators = [
        # Major system restructuring
        len(changed_files) > 50,  # Only very large changes
        # Core infrastructure changes
        any("migrate" in f.lower() for f in changed_files),
        any("refactor" in f.lower() for f in changed_files),
        any("restructure" in f.lower() for f in changed_files),
        # Major new features that change architecture
        analysis.get("type") == "breaking_change" and analysis.get("significance", 0) >= 9,
        # Database schema changes (but not migrations)
        any("schema" in f.lower() and "migration" not in f.lower() for f in changed_files),
        # Major technology stack changes
        any("docker" in f.lower() and "compose" in f.lower() for f in changed_files),
        any("kubernetes" in f.lower() for f in changed_files),
        any("terraform" in f.lower() for f in changed_files),
    ]

    # STRICT criteria for workflow changes (only major process changes)
    major_workflow_indicators = [
        # CI/CD pipeline changes
        any("github" in f.lower() and "workflow" in f.lower() for f in changed_files),
        any("gitlab" in f.lower() and "ci" in f.lower() for f in changed_files),
        any("jenkins" in f.lower() for f in changed_files),
        # Deployment process changes
        any("deploy" in f.lower() and ("script" in f.lower() or "config" in f.lower()) for f in changed_files),
        # Major development process changes
        analysis.get("type") == "breaking_change" and "deployment" in analysis.get("impact_scope", []),
        len(changed_files) > 40,  # Large changes to development files
    ]

    # Only create new version for TRULY major changes
    if any(major_arch_indicators) and analysis.get("significance", 0) >= 8:
        versioning_decision["needs_new_architecture_version"] = True
        versioning_decision["architecture_change_reason"] = (
            f"Major architectural evolution: {analysis.get('title', 'Unknown')}"
        )

    if any(major_workflow_indicators) and analysis.get("significance", 0) >= 8:
        versioning_decision["needs_new_workflow_version"] = True
        versioning_decision["workflow_change_reason"] = (
            f"Major workflow change: {analysis.get('title', 'Unknown')}"
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
You are DocAI, an expert technical writer analyzing THIS SPECIFIC REPOSITORY.

ACTUAL CODEBASE ANALYSIS (USE THIS DATA ONLY):
{json.dumps(codebase_analysis, indent=2)}

RECENT CHANGES:
{json.dumps(analysis, indent=2)}

CRITICAL: Document ONLY what exists in the codebase analysis above. NO generic templates.

Create a README based on ACTUAL code:

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
You are DocAI, an expert system architect analyzing THIS SPECIFIC CODEBASE.

VERSION: v{version}
REASON FOR NEW VERSION: {versioning.get('architecture_change_reason', 'Initial documentation')}

ACTUAL CODEBASE ANALYSIS (USE THIS DATA ONLY):
{json.dumps(arch_analysis, indent=2)}

RECENT CHANGES:
{json.dumps(analysis, indent=2)}

CRITICAL INSTRUCTIONS:
1. ONLY document what EXISTS in the codebase analysis above
2. DO NOT invent components that don't exist
3. DO NOT use generic examples (no "Frontend", "API Gateway" unless they actually exist)
4. USE the actual file names, classes, and functions from the analysis
5. If you see FastAPI in the analysis, document FastAPI (not Flask/Express)
6. If you see PostgreSQL, document PostgreSQL (not MySQL/MongoDB)
7. Reference actual imports like {', '.join(arch_analysis['structure']['imports'].keys())}
8. Document actual frameworks found: {', '.join(arch_analysis['structure']['frameworks'])}
9. Include actual database technologies: {', '.join(arch_analysis['structure']['database_tech'])}
10. Mention deployment methods: {', '.join(arch_analysis['structure']['deployment_tech'])}

Create documentation based ONLY on the actual codebase:

# Architecture v{version}

## System Overview
[Create ASCII diagram showing ACTUAL components from the analysis - use real file/service names]

## Actual Components Found
[Document the services, handlers, models, and utilities that actually exist in the codebase]

### Services
{chr(10).join(f"- {svc['name']}: {svc['description']} (Path: {svc['path']})" for svc in arch_analysis['components']['services'])}

### Handlers
{chr(10).join(f"- {hdl['name']}: {hdl['description']} (Path: {hdl['path']})" for hdl in arch_analysis['components']['handlers'])}

### Models/Schemas
{chr(10).join(f"- {mdl['name']}: {mdl['description']} (Path: {mdl['path']})" for mdl in arch_analysis['components']['models'])}

### Utilities
{chr(10).join(f"- {util['name']}: {util['description']} (Path: {util['path']})" for util in arch_analysis['components']['utilities'])}

## Actual Technology Stack
### Core Technologies
- Languages: {', '.join(arch_analysis['structure']['languages'])}
- Frameworks: {', '.join(arch_analysis['structure']['frameworks'])}
- Database: {', '.join(arch_analysis['structure']['database_tech'])}
- Deployment: {', '.join(arch_analysis['structure']['deployment_tech'])}

### Key Dependencies
{chr(10).join(f"- {dep}: Used {count} times across the codebase" for dep, count in list(arch_analysis['structure']['imports'].items())[:8])}

## Design Patterns Detected
[Document the actual patterns found in the code analysis]
{chr(10).join(f"- {pattern}" for pattern in arch_analysis['patterns'])}

## Current Architecture
[Describe how the ACTUAL system works based on the real code structure, imports, and dependencies]

## Data Flow
[Explain how data flows between the actual components found in the analysis]

## Recent Changes Impact
[Explain how the recent changes affect this specific architecture version based on the actual changes]

BE SPECIFIC. USE ONLY THE DATA FROM THE ANALYSIS. NO GENERIC TEMPLATES.
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

## Development Workflow
### Setup Process
1. Environment setup and configuration
2. Dependency installation
3. Development environment preparation

### Development Process (with diagram)
```
[Start] → [Create Branch] → [Code] → [Test] → [PR] → [Review] → [Merge]
                                         ↓                ↓
                                      [Failed]        [Changes]
                                         ↓                ↓
                                      [Fix] ←----------[Fix]
```

### Code Review Process
- Review guidelines and standards
- Approval requirements and process
- Quality gates and checks

## Deployment Workflow
### Development Deployment
- Steps for development environment
- Testing and validation
- Rollback procedures

### Production Deployment
- Production deployment steps
- Monitoring and validation
- Emergency rollback process

## CI/CD Pipeline
- Build process and automation
- Testing stages and quality gates
- Deployment automation

## Release Process
- Version management and tagging
- Release notes and communication
- Documentation updates

## Monitoring & Maintenance
- Health checks and monitoring
- Logging and alerting
- Incident response procedures

## Recent Changes Impact
[Explain how the recent changes affect this workflow version]

Make it practical, step-by-step, and focused on actual processes used in this codebase.
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
You are DocAI, an expert API documentation writer analyzing THIS SPECIFIC API.

ACTUAL API ANALYSIS (USE THIS DATA ONLY):
{json.dumps(api_analysis, indent=2)}

RECENT CHANGES:
{json.dumps(analysis, indent=2)}

CRITICAL: Document ONLY the actual API endpoints found in the analysis. NO generic examples.

Create API documentation based on ACTUAL endpoints:

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
    """Analyze the entire codebase structure with detailed insights"""
    analysis = {
        "project_name": Path(repo_dir).name,
        "file_count": 0,
        "languages": [],
        "main_directories": [],
        "dependencies": {},
        "entry_points": [],
        "imports": {},
        "frameworks": [],
        "database_tech": [],
        "deployment_tech": []
    }
    
    try:
        # Count files and detect languages
        result = subprocess.run(
            "find . -type f | wc -l",
            shell=True, cwd=repo_dir, capture_output=True, text=True
        )
        analysis["file_count"] = int(result.stdout.strip())

        # Detect languages with actual analysis
        for ext in [".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".php", ".rb"]:
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

        # Analyze Python dependencies and imports
        if ".py" in analysis["languages"]:
            analyze_python_dependencies(repo_dir, analysis)

        # Check for dependency files
        for dep_file in ["package.json", "requirements.txt", "go.mod", "Cargo.toml", "composer.json", "Gemfile"]:
            dep_path = Path(repo_dir) / dep_file
            if dep_path.exists():
                analysis["dependencies"][dep_file] = dep_path.read_text()[:1000]

        # Detect frameworks and technologies
        detect_technologies(repo_dir, analysis)

    except Exception as e:
        print(f"Warning: Codebase analysis error: {e}")

    return analysis


def analyze_python_dependencies(repo_dir, analysis):
    """Analyze Python imports and dependencies"""
    imports = {}
    frameworks = []

    try:
        for py_file in Path(repo_dir).rglob("*.py"):
            try:
                content = py_file.read_text()

                # Extract import statements
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith(('import ', 'from ')):
                        # Extract main module
                        if line.startswith('import '):
                            module = line.split(' ')[1].split('.')[0]
                        elif line.startswith('from '):
                            module = line.split(' ')[1].split('.')[0]

                        if module not in ['os', 'sys', 'json', 'time', 'datetime', 'typing']:
                            imports[module] = imports.get(module, 0) + 1

            except:
                continue

        # Detect frameworks
        framework_indicators = {
            "FastAPI": ["fastapi", "FastAPI"],
            "Django": ["django", "DJANGO"],
            "Flask": ["flask", "Flask"],
            "SQLAlchemy": ["sqlalchemy", "SQLAlchemy"],
            "AsyncPG": ["asyncpg", "AsyncPG"],
            "Pydantic": ["pydantic", "Pydantic"],
            "Click": ["click", "Click"],
            "Typer": ["typer", "Typer"]
        }

        for framework, indicators in framework_indicators.items():
            if any(indicator in str(imports) for indicator in indicators):
                frameworks.append(framework)

        analysis["imports"] = dict(sorted(imports.items(), key=lambda x: x[1], reverse=True)[:10])
        analysis["frameworks"] = frameworks

    except Exception as e:
        print(f"Warning: Python analysis failed: {e}")


def detect_technologies(repo_dir, analysis):
    """Detect technologies and deployment methods"""
    content = ""
    for file_path in Path(repo_dir).rglob("*"):
        try:
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.yaml', '.yml', '.json', '.md']:
                content += file_path.read_text().lower()
        except:
            continue

    # Database technologies
    db_indicators = {
        "PostgreSQL": ["postgresql", "postgres", "psycopg"],
        "MySQL": ["mysql", "pymysql"],
        "SQLite": ["sqlite", "sqlite3"],
        "MongoDB": ["mongodb", "pymongo", "mongo"],
        "Redis": ["redis", "aredis"],
        "Milvus": ["milvus", "pymilvus"]
    }

    for db, indicators in db_indicators.items():
        if any(indicator in content for indicator in indicators):
            analysis["database_tech"].append(db)

    # Deployment technologies
    deploy_indicators = {
        "Docker": ["docker", "dockerfile", "docker-compose"],
        "Kubernetes": ["kubernetes", "k8s", "kubectl"],
        "AWS": ["aws", "boto3", "s3", "ec2"],
        "GCP": ["google", "gcp", "firebase"],
        "Azure": ["azure", "microsoft"],
        "Heroku": ["heroku", "gunicorn"],
        "Vercel": ["vercel", "now"],
        "Netlify": ["netlify"]
    }

    for deploy, indicators in deploy_indicators.items():
        if any(indicator in content for indicator in indicators):
            analysis["deployment_tech"].append(deploy)


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
    """Analyze system components based on actual codebase structure"""
    components = {
        "detected": [],
        "services": [],
        "utilities": [],
        "models": [],
        "handlers": []
    }

    try:
        # Look for actual component structure
        src_dir = Path(repo_dir) / "src"
        if src_dir.exists():
            # Detect services
            for py_file in src_dir.rglob("*.py"):
                filename = py_file.stem.lower()
                content = py_file.read_text()

                if any(pattern in filename for pattern in ["service", "_service"]):
                    components["services"].append({
                        "name": py_file.stem,
                        "path": str(py_file.relative_to(repo_dir)),
                        "description": f"Service module handling {filename.replace('_', ' ')} functionality"
                    })

                elif any(pattern in filename for pattern in ["handler", "_handler"]):
                    components["handlers"].append({
                        "name": py_file.stem,
                        "path": str(py_file.relative_to(repo_dir)),
                        "description": f"Handler for {filename.replace('_', ' ')} operations"
                    })

                elif any(pattern in filename for pattern in ["model", "_model", "schema"]) and "class" in content:
                    components["models"].append({
                        "name": py_file.stem,
                        "path": str(py_file.relative_to(repo_dir)),
                        "description": f"Data model/schema for {filename.replace('_', ' ')}"
                    })

                elif any(pattern in filename for pattern in ["util", "helper", "utils"]) or "def " in content and len(content.split("def ")) > 3:
                    components["utilities"].append({
                        "name": py_file.stem,
                        "path": str(py_file.relative_to(repo_dir)),
                        "description": f"Utility functions for {filename.replace('_', ' ')}"
                    })

        # Detect main application structure
        main_patterns = {
            "api": ["fastapi", "flask", "app.py", "main.py"],
            "database": ["database", "db", "postgres", "sqlite", "model"],
            "frontend": ["static", "templates", "public", "web", "ui"],
            "core": ["core", "engine", "manager", "processor"]
        }

        for component_type, patterns in main_patterns.items():
            for pattern in patterns:
                if any(pattern in str(f) for f in Path(repo_dir).rglob("*") if f.is_file()):
                    if component_type not in components["detected"]:
                        components["detected"].append(component_type)

        # If no specific components found, fall back to basic detection
        if not components["detected"]:
            components["detected"] = ["core", "api", "database"]

        return components

    except Exception as e:
        print(f"Warning: Component analysis failed: {e}")
        return {"detected": ["core", "api", "database"], "services": [], "utilities": [], "models": [], "handlers": []}


def detect_design_patterns(repo_dir):
    """Detect actual design patterns in the codebase"""
    patterns = []

    try:
        # Look for actual patterns in the code
        pattern_indicators = {
            "Factory Pattern": ["factory", "create", "builder"],
            "Observer Pattern": ["observer", "listener", "event", "callback", "subscribe"],
            "Singleton Pattern": ["singleton", "instance", "_instance", "getinstance"],
            "Repository Pattern": ["repository", "repo", "dao", "data access"],
            "MVC Pattern": ["model", "view", "controller", "mvc"],
            "Dependency Injection": ["inject", "container", "di", "provider"],
            "Strategy Pattern": ["strategy", "algorithm", "policy"],
            "Decorator Pattern": ["decorator", "wrapper", "wrap"],
            "Command Pattern": ["command", "execute", "undo"],
            "Adapter Pattern": ["adapter", "bridge", "interface"],
            "Facade Pattern": ["facade", "simplify", "interface"],
            "Proxy Pattern": ["proxy", "delegate", "surrogate"],
            "Chain of Responsibility": ["chain", "handler", "next"],
            "Template Method": ["template", "hook", "abstract"],
            "State Pattern": ["state", "context", "transition"],
            "Composite Pattern": ["composite", "component", "leaf", "container"],
            "Iterator Pattern": ["iterator", "next", "hasnext", "iterable"],
            "Mediator Pattern": ["mediator", "communicate", "central"],
            "Memento Pattern": ["memento", "snapshot", "state"],
            "Flyweight Pattern": ["flyweight", "cache", "pool", "reuse"]
        }

        # Search through Python files for pattern indicators
        for py_file in Path(repo_dir).rglob("*.py"):
            try:
                content = py_file.read_text().lower()

                for pattern_name, indicators in pattern_indicators.items():
                    if any(indicator in content for indicator in indicators):
                        # Check for actual implementation, not just mentions
                        if pattern_name.lower() in content or any(f"class.*{ind}" in content for ind in indicators):
                            if pattern_name not in patterns:
                                patterns.append(pattern_name)
            except:
                continue

        # If no patterns found, return basic ones that are commonly used
        if not patterns:
            # Check for common patterns in our specific codebase
            content = ""
            for py_file in Path(repo_dir).rglob("*.py"):
                try:
                    content += py_file.read_text()
                except:
                    continue

            if "class" in content and "def" in content:
                patterns.append("Object-Oriented Design")

            if "async" in content or "await" in content:
                patterns.append("Async/Await Pattern")

            if "try:" in content and "except" in content:
                patterns.append("Error Handling Pattern")

        return patterns if patterns else ["Object-Oriented Design", "Error Handling"]

    except Exception as e:
        print(f"Warning: Design pattern detection failed: {e}")
        return ["Object-Oriented Design", "Async/Await Pattern"]


def update_summary_navigation(docs_dir):
    """Update SUMMARY.md with proper navigation links"""
    
    summary_content = "# Summary\n\n"
    
    # Add main documentation links
    if (docs_dir / "SUMMARY.md").exists() or (docs_dir / "README.md").exists():
        summary_content += "* [Home](README.md)\n"

    # Add architecture versions (show only last 5 versions)
    arch_dir = docs_dir / "architecture"
    if arch_dir.exists():
        arch_files = sorted(arch_dir.glob("v*-architecture.md"), reverse=True)
        if arch_files:
            summary_content += "\n## Architecture\n"
            # Show only the most recent 5 versions to avoid clutter
            for arch_file in arch_files[:5]:
                # Extract version from v1.0-architecture.md format
                version_str = arch_file.stem.split("-")[0]
                summary_content += f"* [{version_str.upper()} Architecture](architecture/{arch_file.name})\n"

    # Add workflow versions (show only last 5 versions)
    workflow_dir = docs_dir / "workflow"
    if workflow_dir.exists():
        workflow_files = sorted(workflow_dir.glob("v*-workflow.md"), reverse=True)
        if workflow_files:
            summary_content += "\n## Workflow\n"
            # Show only the most recent 5 versions to avoid clutter
            for workflow_file in workflow_files[:5]:
                # Extract version from v1.0-workflow.md format
                version_str = workflow_file.stem.split("-")[0]
                summary_content += f"* [{version_str.upper()} Workflow](workflow/{workflow_file.name})\n"

    # Add API docs
    if (docs_dir / "api.md").exists():
        summary_content += "\n## API\n"
        summary_content += "* [API Documentation](api.md)\n"

    # Add changes (show only last 10 changes to avoid clutter)
    changes_dir = docs_dir / "changes"
    if changes_dir.exists():
        change_files = sorted(changes_dir.glob("*.md"), reverse=True)
        if change_files:
            summary_content += "\n## Recent Changes\n"
            for change_file in change_files[:10]:  # Latest 10 only
                # Extract title from filename (remove commit hash prefix)
                title = change_file.stem.split("-", 1)[-1].replace("-", " ").title()
                summary_content += f"* [{title}](changes/{change_file.name})\n"

    # Save SUMMARY.md
    summary_file = docs_dir / "SUMMARY.md"
    summary_file.write_text(summary_content)
    print(f"✅ Updated {summary_file} (showing only recent versions)")
