import argparse
import asyncio
import datetime
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

from core.app_installation_service import AppInstallationService
from utilities.github_dual_app_helper import get_github_dual_app_helper


def run_cmd(cmd: str, cwd: str | None = None) -> None:
    print(f"RUN: {cmd}")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)


async def resolve_docbook_repo(pool: asyncpg.Pool, org_id: str, explicit: str | None) -> str:
    if explicit:
        return explicit

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT docbook_full_name
            FROM docbook_repos
            WHERE org_id = $1 AND is_active = TRUE
            ORDER BY updated_at DESC NULLS LAST, created_at DESC
            LIMIT 1
            """,
            org_id,
        )

    if not row:
        raise SystemExit(f"No active docbook repo found for org '{org_id}'.")

    return row["docbook_full_name"]


async def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Verify writer app push access.")
    parser.add_argument("--org", required=True, help="Organization slug (e.g. jai-mahakal-poc)")
    parser.add_argument("--repo", help="Docbook repo full name (org/repo). Auto-detected if omitted.")
    parser.add_argument("--branch", default="staging", help="Branch to push to (default: staging)")
    parser.add_argument(
        "--message",
        default="test: writer token verification",
        help="Commit message to use.",
    )
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not configured.")

    pool = await asyncpg.create_pool(database_url)

    try:
        org_id = args.org
        docbook_full_name = await resolve_docbook_repo(pool, org_id, args.repo)
        print(f"📦 Target docbook repo: {docbook_full_name}")

        dual_app = get_github_dual_app_helper()
        if not dual_app.writer_app_id:
            raise SystemExit("Writer app is not configured in environment variables.")

        app_install_service = AppInstallationService(pool)

        print("🔍 Fetching accessible repos for writer app from DB...")
        accessible = await app_install_service.get_app_accessible_repos(
            org_id, int(dual_app.writer_app_id)
        )
        if accessible:
            print(f"📚 Writer app can access {len(accessible)} repo(s):")
            for repo_name in sorted(accessible):
                print(f"   • {repo_name}")
        else:
            print("⚠️  No repos stored for writer app in DB (webhook may not have run?)")

        installation_id = await app_install_service.get_app_installation_id(
            org_id, int(dual_app.writer_app_id)
        )

        if not installation_id:
            raise SystemExit(
                f"Writer app installation not found for org '{org_id}'. Reinstall pustak-publisher-ai."
            )

        print(f"🔗 Writer installation ID: {installation_id}")

        print("🔐 Requesting writer installation token from GitHub...")
        writer_token = await dual_app.get_writer_token(installation_id)
        if not writer_token:
            raise SystemExit("Failed to obtain writer installation token.")

        tmpdir = tempfile.mkdtemp(prefix="docai_writer_test_")
        try:
            clone_url = f"https://x-access-token:{writer_token}@github.com/{docbook_full_name}.git"
            run_cmd(f"git clone {clone_url} {tmpdir}")

            branch = args.branch
            try:
                run_cmd(f"git checkout {branch}", cwd=tmpdir)
            except subprocess.CalledProcessError:
                run_cmd("git checkout main", cwd=tmpdir)
                run_cmd(f"git checkout -b {branch}", cwd=tmpdir)

            readme_path = Path(tmpdir) / "README.md"
            if readme_path.exists():
                existing = readme_path.read_text(encoding="utf-8")
            else:
                existing = ""

            timestamp = datetime.datetime.utcnow().isoformat()
            marker = f"<!-- docai writer test {timestamp} -->"
            newline = "\n" if existing and not existing.endswith("\n") else ""
            readme_path.write_text(f"{existing}{newline}{marker}\n", encoding="utf-8")

            run_cmd("git add README.md", cwd=tmpdir)
            run_cmd(f"git commit -m \"{args.message}\"", cwd=tmpdir)
            run_cmd(f"git push origin HEAD:{branch}", cwd=tmpdir)

            print("✅ Writer push succeeded.")
            print(f"   Repo: {docbook_full_name}")
            print(f"   Branch: {branch}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
