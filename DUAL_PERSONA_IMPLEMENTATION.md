# Dual Persona Documentation Implementation

## Overview

This document describes the implementation of the dual persona documentation system, which supports generating and serving documentation for two distinct personas:

1. **Internal** (`internal`) - Private documentation for authenticated users
2. **Developer** (`dev`) - Public documentation for unauthenticated users

The implementation follows a "Hub-and-Spoke" directory structure within the `pustak-docbook` repository, where:
- `internal/` docs are private and require authentication
- `dev/` docs are public and accessible without authentication

## Implementation Details

### Phase 1: Backend Refactor

#### 1. Modified `app/services/event/smart_processor.py`

- Updated `handle_push_event()` to support multiple personas
- Changed parameter from `doc_persona: str = "internal"` to `doc_personas: list[str] = ["internal", "dev"]`
- Added a loop to generate documentation for each persona
- Created persona-specific directories (`docs/internal` and `docs/dev`)

```python
# Generate documentation for each persona
for persona in doc_personas:
    print(f"\n{'=' * 80}")
    print(f"📚 Generating {persona} documentation")
    print(f"{'=' * 80}")
    
    # Create persona-specific docs directory
    persona_docs_dir = repo_path / "docs" / persona
    persona_docs_dir.mkdir(parents=True, exist_ok=True)
    
    await generate_smart_documentation(
        repo_path,
        analysis,
        commit_sha,
        ref,
        persona
    )
```

#### 2. Modified `app/services/documentation/comprehensive.py`

- Updated `generate_comprehensive_documentation()` to use persona-specific paths
- Changed docs directory from `docs_dir = Path(repo_dir) / "docs"` to `docs_dir = Path(repo_dir) / "docs" / doc_persona`
- Updated `check_documentation_quality()` to accept a `doc_persona` parameter
- Enhanced `update_summary_navigation()` to handle persona-specific paths and add persona information to SUMMARY.md

```python
def update_summary_navigation(docs_dir: Path) -> None:
    """Update SUMMARY.md navigation with links to all documentation files."""
    # Get persona from path if available
    persona = "" 
    if "internal" in str(docs_dir) or "dev" in str(docs_dir):
        persona = docs_dir.name
        print(f"📚 Updating SUMMARY.md for persona: {persona}")
    
    # ... (existing code)
    
    # Add persona information if applicable
    if persona:
        summary.append(f"\n## Documentation Info")
        summary.append(f"* Persona: **{persona}**")
        summary.append(f"* Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
```

#### 3. Modified `app/services/docbook/publisher.py`

- Enhanced `_sync_docs()` to maintain the nested persona structure
- Added detection for legacy structure (no internal/dev folders)
- Implemented handling for both legacy and new structure
- For legacy repos, copies content to `internal/` and creates a minimal `dev/` folder

```python
def _sync_docs(self, repo_dir: Path, source_repo_name: str, docs_dir: Path) -> None:
    # Create target repo directory
    target_dir = repo_dir / source_repo_name
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Create docs directory inside target repo directory
    target_docs_dir = target_dir / "docs"
    target_docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we're dealing with legacy structure (no internal/dev folders)
    is_legacy = not any((docs_dir / persona).exists() for persona in ["internal", "dev"])
    
    if is_legacy:
        # Legacy mode: Copy everything to internal folder
        internal_target_dir = target_docs_dir / "internal"
        internal_target_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all files from docs_dir to internal_target_dir
        for item in docs_dir.glob("**/*"):
            if item.is_file():
                rel_path = item.relative_to(docs_dir)
                dest_path = internal_target_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_path)
                
        # Create minimal dev folder with README
        dev_target_dir = target_docs_dir / "dev"
        dev_target_dir.mkdir(parents=True, exist_ok=True)
        with open(dev_target_dir / "README.md", "w") as f:
            f.write(f"# {source_repo_name}\n\nPublic documentation is not available for this repository.")
    else:
        # New structure: Copy persona folders directly
        shutil.copytree(docs_dir, target_docs_dir, dirs_exist_ok=True)
```

#### 4. Modified `app/services/documentation/quality_integration.py`

- Updated `read_generated_docs()` to handle persona-specific paths
- Added detection for new persona-based structure
- Prioritizes `internal` docs for quality checks
- Falls back to first available persona if `internal` doesn't exist

```python
def read_generated_docs(repo_dir: str) -> Dict[str, str]:
    """Collect generated documentation artefacts from disk."""
    docs: Dict[str, str] = {}
    base_docs_path = Path(repo_dir) / "docs"
    
    # Check if we're using the new persona-based structure
    personas = ["internal", "dev"]
    persona_paths = [base_docs_path / persona for persona in personas if (base_docs_path / persona).exists()]
    
    if persona_paths:
        # New structure: Read from persona-specific directories
        # Prioritize internal docs for quality checks
        internal_path = base_docs_path / "internal"
        if internal_path.exists():
            docs_path = internal_path
        else:
            # Fall back to first available persona
            docs_path = persona_paths[0]
            
        print(f"📚 Reading docs from persona directory: {docs_path.name}")
    else:
        # Legacy structure: Read from base docs directory
        docs_path = base_docs_path
        print("📚 Reading docs from legacy directory structure")
```

- Updated `save_quality_report()` to handle persona-specific paths
- Saves quality report to the appropriate persona directory

## Testing

A test script (`test_dual_persona_simple.py`) was created to verify the dual persona documentation structure:

1. Creates a simulated repository with sample files
2. Generates documentation for both `internal` and `dev` personas
3. Verifies the directory structure for each persona
4. Simulates publishing to a docbook repository
5. Verifies the published structure maintains the persona directories

The test confirms that:
- Both persona directories are created correctly
- Each persona has its own SUMMARY.md, README.md, etc.
- The publishing process preserves the nested structure
- Legacy repositories are handled correctly

## Next Steps

### Phase 2: Frontend Routing & Middleware

The next phase will involve updating the frontend to support the new URL structure:
- Update middleware.ts to parse {repo} and {persona} from URL path
- Default to 'dev' persona if missing
- For 'internal' persona, add auth guard
- Update docs page routing to src/app/docs/[org]/[repo]/[persona]/[...slug]/page.tsx
- Update API calls to include persona parameter
- Show helpful 404 if persona folder missing

## Conclusion

Phase 1 of the dual persona implementation is complete. The backend now generates documentation for both internal and developer personas, and the publishing pipeline preserves this structure. The system is backward compatible with legacy repositories, automatically converting them to the new structure during publishing.
