# processor.py
import os, subprocess, tempfile, shutil, datetime, google.generativeai as genai
from github_app import get_installation_token
from llm_provider import generate_doc_for_file
from pathlib import Path

def run_cmd(cmd, cwd=None):
    print("RUN:", cmd)
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)

def clone_repo_via_token(repo_full_name, token, target_dir):
    # clone using token in URL - token as username 'x-access-token' works for GitHub
    url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
    run_cmd(f"git clone --depth 1 {url} {target_dir}")

def handle_push_event(payload):
    # parse payload
    repo = payload.get("repository", {})
    repo_full = repo.get("full_name")  # "org/name"
    installation = payload.get("installation", {})
    installation_id = installation.get("id")
    changed_files = set()
    # get list of changed files from commits
    for commit in payload.get("commits", []):
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))

    if not changed_files:
        print("No changed files in push, skipping.")
        return

    print("Changed files in push:", sorted(list(changed_files)))

    # get token for this installation
    token = get_installation_token(installation_id)

    tmpdir = tempfile.mkdtemp(prefix="docai_")
    try:
        clone_repo_via_token(repo_full, token, tmpdir)

        # Checkout the exact ref/commit from the push for correctness on branches
        ref = payload.get("ref")  # e.g., refs/heads/feature-x
        after_sha = payload.get("after")  # commit SHA after push
        try:
            if ref:
                run_cmd(f"git fetch origin {ref}", cwd=tmpdir)
            if after_sha:
                run_cmd(f"git checkout --detach {after_sha}", cwd=tmpdir)
            elif ref and ref.startswith("refs/heads/"):
                branch = ref.split("/", 2)[-1]
                run_cmd(f"git checkout {branch}", cwd=tmpdir)
        except Exception as e:
            print("Warning: failed to checkout pushed ref/sha:", ref, after_sha, e)

        # Check if we've already processed this exact push (same SHA and same files)
        if has_already_processed_push(tmpdir, after_sha, changed_files):
            print(f"Push {after_sha} with these files already processed; skipping.")
            return

        # NEW: Analyze the entire change, not individual files
        change_summary = analyze_push_change(payload, tmpdir, changed_files)
        
        if not change_summary["is_significant"]:
            print("Change not significant enough for documentation:", change_summary["reason"])
            return

        # Generate ONE MD for the entire change (not per webhook call)
        changes_dir = Path(tmpdir) / "changes"
        changes_dir.mkdir(parents=True, exist_ok=True)
        
        # Use commit SHA as filename to ensure uniqueness per actual change
        change_file = changes_dir / f"{after_sha}-{change_summary['type']}.md"
        
        with open(change_file, "w", encoding="utf-8") as fh:
            fh.write(f"# {change_summary['title']}\n\n")
            fh.write(f"**Type:** {change_summary['type']}\n")
            fh.write(f"**Date:** {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            fh.write(f"**Commit:** {after_sha}\n")
            fh.write(f"**Branch:** {ref}\n\n")
            fh.write(f"## Summary\n{change_summary['summary']}\n\n")
            fh.write(f"## Files Changed\n")
            for f in sorted(changed_files):
                fh.write(f"- {f}\n")
            fh.write(f"\n## Technical Details\n{change_summary['details']}\n")

        print(f"Wrote change documentation: {change_file}")

        # Update changes/README.md with all changes
        update_changes_readme(changes_dir, change_summary, after_sha)

        # Mark this push as processed
        mark_push_processed(tmpdir, after_sha, changed_files)

        # commit & push back
        run_cmd("git config user.email 'docai@bots.local' && git config user.name 'docai-bot'", cwd=tmpdir)
        run_cmd("git add changes || true", cwd=tmpdir)
        commit_msg = f"docs: {change_summary['type']} - {change_summary['title']} [sha:{after_sha}]"
        run_cmd(f"git commit -m '{commit_msg}' || echo 'no changes'", cwd=tmpdir)
        run_cmd(f"git push https://x-access-token:{token}@github.com/{repo_full}.git HEAD:main", cwd=tmpdir)
        print("Change docs committed and pushed.")
    finally:
        shutil.rmtree(tmpdir)


def has_already_processed_push(repo_dir, sha, changed_files):
    """Check if we've already processed this exact push."""
    try:
        # Check git log for this SHA
        run_cmd("git log -n 20 --pretty=format:%s > .gitlog.tmp", cwd=repo_dir)
        with open(Path(repo_dir)/".gitlog.tmp", "r", encoding="utf-8", errors="ignore") as fh:
            subjects = fh.read()
        if f"[sha:{sha}]" in subjects:
            return True
        
        # Also check if a file with this SHA already exists
        changes_dir = Path(repo_dir) / "changes"
        if changes_dir.exists():
            for f in changes_dir.glob(f"{sha}-*.md"):
                return True
    except Exception as e:
        print("Warning: could not check if push already processed:", e)
    return False


def mark_push_processed(repo_dir, sha, changed_files):
    """Mark this push as processed to prevent duplicates."""
    # The commit itself with [sha:xxx] serves as the marker
    pass


def analyze_push_change(payload, repo_dir, changed_files):
    """Use LLM to analyze the entire push and determine if it's significant."""
    # Get commit message and recent context
    commits = payload.get("commits", [])
    commit_msg = commits[-1].get("message", "") if commits else ""
    
    # Get diff context (simplified - could be enhanced with git diff)
    context = f"""
    Commit message: {commit_msg}
    Files changed: {', '.join(changed_files)}
    Files removed: {', '.join(removed_files)}
    
    Analyze this code change and determine:
    1. What type of change is this? (feature, bug_fix, refactor, test, chore, docs)
    2. Is it significant enough to document? (major features, bug fixes, API changes)
    3. What is the main purpose/title of this change?
    4. Provide a summary of what was implemented/changed
    5. Technical details about the implementation
    
    Respond in JSON format:
    {{
        "type": "feature|bug_fix|refactor|test|chore|docs",
        "is_significant": true|false,
        "reason": "brief explanation if not significant",
        "title": "short descriptive title",
        "summary": "2-3 sentence summary of the change",
        "details": "technical implementation details"
    }}
    """
    
    try:
        prompt = f"You are DocAI analyzing code changes. {context}"
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        resp = model.generate_content(prompt)
        result = getattr(resp, "text", None) or str(resp)
        
        # Simple JSON parsing (in production, use proper JSON parsing)
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            # Basic eval for demo - use json.loads in production
            result = eval(json_match.group())
            return result
    except Exception as e:
        print("Error analyzing change:", e)
    
    # Fallback if LLM fails
    return {
        "type": "unknown",
        "is_significant": True,
        "reason": "LLM analysis failed, defaulting to significant",
        "title": f"Code change in {len(changed_files)} files",
        "summary": f"Modified {len(changed_files)} files. Removed {len(removed_files)} files.",
        "details": f"Files: {', '.join(changed_files)}"
    }


def update_changes_readme(changes_dir, change_summary, timestamp):
    """Update changes/README.md with list of all changes."""
    readme_path = changes_dir / "README.md"
    
    # Get existing changes
    existing_changes = []
    if readme_path.exists():
        with open(readme_path, "r", encoding="utf-8") as fh:
            content = fh.read()
            # Simple parsing - look for existing entries
            import re
            existing_changes = re.findall(r'- \d{4}-\d{2}-\d{2}.*?\n', content)
    
    # Add new change at the top
    new_entry = f"- {timestamp} - {change_summary['type']}: {change_summary['title']}\n"
    all_changes = [new_entry] + existing_changes[:10]  # Keep last 10
    
    readme_content = "# Changes\n\nRecent changes documented by DocAI:\n\n" + "".join(all_changes)
    
    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write(readme_content)


def rebuild_all_for_repo(repo_full: str, installation_id: int):
    """Generate docs for all supported files in a repository and push to docs/.

    Intended for first-time seeding or manual rebuilds.
    """
    token = get_installation_token(installation_id)
    tmpdir = tempfile.mkdtemp(prefix="docai_full_")
    try:
        clone_repo_via_token(repo_full, token, tmpdir)

        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        supported_exts = [".py", ".js", ".ts", ".go", ".java", ".rs", ".cpp", ".c"]
        generated_files = []

        for path in Path(tmpdir).rglob("*"):
            if path.is_file() and any(str(path).endswith(ext) for ext in supported_exts):
                rel = path.relative_to(tmpdir).as_posix()
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        code = fh.read()
                except Exception as e:
                    print("skip unreadable:", rel, e)
                    continue
                md = generate_doc_for_file(rel, code)
                target = docs_dir / (rel.replace("/", "__") + ".md")
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "w", encoding="utf-8") as out:
                    out.write(md)
                print("Wrote doc for", rel, "->", target)
                generated_files.append(target.name)

        if generated_files:
            readme_path = docs_dir / "README.md"
            readme_content = (
                "# Project Docs\n\n"
                "This documentation is generated automatically by DocAI.\n\n"
                "Use the sidebar to navigate pages.\n"
            )
            with open(readme_path, "w", encoding="utf-8") as fh:
                fh.write(readme_content)

            summary_path = docs_dir / "SUMMARY.md"
            generated_files.sort()
            lines = ["# Summary\n", "\n", "* [Home](README.md)\n"]
            for name in generated_files:
                title = name.replace("__", "/").replace(".md", "")
                lines.append(f"* [{title}]({name})\n")
            with open(summary_path, "w", encoding="utf-8") as fh:
                fh.writelines(lines)

        run_cmd("git config user.email 'docai@bots.local' && git config user.name 'docai-bot'", cwd=tmpdir)
        run_cmd("git add docs || true", cwd=tmpdir)
        run_cmd("git commit -m 'docs: full rebuild by DocAI' || echo 'no changes'", cwd=tmpdir)
        run_cmd(f"git push https://x-access-token:{token}@github.com/{repo_full}.git HEAD:main", cwd=tmpdir)
        print("Full docs committed and pushed.")
    finally:
        shutil.rmtree(tmpdir)