# processor.py
import os, subprocess, tempfile, shutil
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
    removed_files = set()
    # get list of changed files from commits
    for commit in payload.get("commits", []):
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))
        removed_files.update(commit.get("removed", []))

    if not changed_files:
        print("No changed files in push, skipping.")
        return

    print("Changed files in push:", sorted(list(changed_files)))
    if removed_files:
        print("Removed files in push:", sorted(list(removed_files)))

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

        docs_dir = Path(tmpdir) / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Idempotency guard: if we've already committed for this SHA, skip.
        try:
            if after_sha:
                # Look for our marker in recent history
                run_cmd("git log -n 50 --pretty=format:%s > .gitlog.tmp", cwd=tmpdir)
                with open(Path(tmpdir)/".gitlog.tmp", "r", encoding="utf-8", errors="ignore") as fh:
                    subjects = fh.read()
                if f"[sha:{after_sha}]" in subjects:
                    print("This push SHA already processed; skipping duplicate run:", after_sha)
                    return
        except Exception as e:
            print("Warning: could not check duplicate SHA in history:", e)

        supported_exts = [".py", ".js", ".ts", ".go", ".java", ".rs", ".cpp", ".c"]
        generated_files = []  # list of generated doc filenames
        generated_pairs = []  # (source_path, doc_filename)
        considered_files = []
        for f in changed_files:
            # only handle relevant extensions
            if any(f.endswith(ext) for ext in supported_exts):
                abs_path = Path(tmpdir) / f
                if not abs_path.exists(): 
                    print("file missing:", f); continue
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
                    code = fh.read()
                md = generate_doc_for_file(f, code)
                target = docs_dir / (f.replace("/", "__") + ".md")
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "w", encoding="utf-8") as out:
                    out.write(md)
                print("Wrote doc for", f, "->", target)
                generated_files.append(target.name)
                generated_pairs.append((f, target.name))
                considered_files.append(f)
            else:
                print("Skipping unsupported file (no matching extension):", f)

        # Remove docs for removed files
        removed_count = 0
        removed_pairs = []  # (source_path, doc_filename)
        for f in removed_files:
            if any(f.endswith(ext) for ext in supported_exts):
                target = docs_dir / (f.replace("/", "__") + ".md")
                if target.exists():
                    try:
                        target.unlink()
                        removed_count += 1
                        print("Removed doc for deleted file:", f, "->", target)
                        removed_pairs.append((f, target.name))
                    except Exception as e:
                        print("Failed to remove doc for", f, e)

        # Always (re)build README.md and SUMMARY.md from current docs directory
        all_pages = [p.name for p in docs_dir.glob("*.md") if p.name not in ("README.md", "SUMMARY.md")]
        all_pages.sort()

        readme_path = docs_dir / "README.md"
        readme_content = (
            "# Project Docs\n\n"
            "This documentation is generated automatically by DocAI from repository changes.\n\n"
            "Use the sidebar to navigate individual pages.\n"
        )
        with open(readme_path, "w", encoding="utf-8") as fh:
            fh.write(readme_content)

        summary_path = docs_dir / "SUMMARY.md"
        lines = ["# Summary\n", "\n", "* [Home](README.md)\n"]
        for name in all_pages:
            title = name.replace("__", "/").replace(".md", "")
            lines.append(f"* [{title}]({name})\n")
        with open(summary_path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)

        if not generated_files and removed_count == 0:
            print("No supported changes produced docs and no deletions. Commit may be a no-op.")

        # Append a run summary to a changelog for visibility
        try:
            import datetime
            log_path = docs_dir / "DOC_AI_RUN_LOG.md"
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            if generated_pairs or removed_pairs:
                with open(log_path, "a", encoding="utf-8") as fh:
                    fh.write(f"\n\n## Run {ts}\n")
                    fh.write(f"Repo: {repo_full}  Ref: {ref}  After: {after_sha}\n\n")
                    if generated_pairs:
                        fh.write("### Generated/Updated\n")
                        for src, doc in sorted(generated_pairs):
                            fh.write(f"- {src} -> {doc}\n")
                    if removed_pairs:
                        fh.write("\n### Removed\n")
                        for src, doc in sorted(removed_pairs):
                            fh.write(f"- {src} (removed) -> {doc}\n")
        except Exception as e:
            print("Warning: failed to append DOC_AI_RUN_LOG.md:", e)

        # commit & push back
        run_cmd("git config user.email 'docai@bots.local' && git config user.name 'docai-bot'", cwd=tmpdir)
        run_cmd("git add docs || true", cwd=tmpdir)
        # Only commit when there are staged changes; include SHA marker for idempotency
        commit_msg = f"docs: {len(generated_pairs)} updated, {removed_count} removed by DocAI [sha:{after_sha}]"
        run_cmd(f"sh -lc 'git diff --cached --quiet && echo no changes || git commit -m " + repr(commit_msg) + "'", cwd=tmpdir)
        run_cmd(f"git push https://x-access-token:{token}@github.com/{repo_full}.git HEAD:main", cwd=tmpdir)
        print("Docs committed and pushed.")
    finally:
        shutil.rmtree(tmpdir)


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