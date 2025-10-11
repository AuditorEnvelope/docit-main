# processor.py

_Automatic doc generation failed._

Error: NotFound: 404 models/gemini-1.5-flash-latest is not found for API version v1beta, or is not supported for generateContent. Call ListModels to see the list of available models and their supported methods.

## Code (truncated)

````
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
 
````
