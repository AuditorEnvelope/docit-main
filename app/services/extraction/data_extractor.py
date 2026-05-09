"""
Data Extractor - Phase 3

Detects database and ORM patterns.
Lightweight dependency and file scanning.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .base_extractor import BaseExtractor, ExtractionResult


class DataExtractor(BaseExtractor):
    """
    Extracts data layer signals from repository.

    Detects:
    - ORM frameworks (SQLAlchemy, Prisma, Mongoose, etc.)
    - Database types (PostgreSQL, MySQL, MongoDB, etc.)
    - Migration tools
    - Connection patterns
    """

    # ORM patterns by language
    ORM_PATTERNS = {
        "python": {
            "sqlalchemy": ["sqlalchemy", "declarative_base", "Column", "relationship"],
            "django_orm": ["django.db", "models.Model", "models.CharField"],
            "tortoise": ["tortoise", "Model", "fields"],
            "peewee": ["peewee", "Model", "CharField"],
        },
        "javascript": {
            "prisma": ["@prisma/client", "prisma", "PrismaClient"],
            "mongoose": ["mongoose", "Schema", "model"],
            "sequelize": ["sequelize", "Sequelize", "define"],
            "typeorm": ["typeorm", "Entity", "Column"],
        },
    }

    # Database detection patterns
    DATABASE_PATTERNS = {
        "postgresql": ["postgresql", "postgres", "psycopg", "asyncpg"],
        "mysql": ["mysql", "pymysql", "aiomysql", "mysql-connector"],
        "mongodb": ["mongodb", "mongo", "pymongo", "motor"],
        "redis": ["redis", "aioredis"],
        "sqlite": ["sqlite", "sqlite3"],
        "dynamodb": ["dynamodb", "boto3"],
        "elasticsearch": ["elasticsearch", "es"],
    }

    # Migration tool patterns
    MIGRATION_TOOLS = {
        "alembic": ["alembic", "alembic.ini", "versions/"],
        "django_migrations": ["migrations/", "0001_initial.py"],
        "prisma_migrate": ["prisma/migrations"],
        "typeorm_migrations": ["migrations/", "Migration"],
        "flyway": ["flyway", "V1__"],
    }

    def can_run(self, repo_analysis: Dict[str, Any]) -> bool:
        """Always run - data layer detection is lightweight."""
        return True

    def extract(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
    ) -> ExtractionResult:
        """Extract data layer signals."""
        signals = {
            "data_layer": None,
            "database_type": None,
            "orm_patterns": [],
        }

        files_scanned = 0
        found_orms: Set[str] = set()
        found_databases: Set[str] = set()

        # Detect ORM from dependencies
        orm_from_deps = self._detect_orm_from_dependencies(repo_path)
        found_orms.update(orm_from_deps)

        # Detect database from dependencies
        db_from_deps = self._detect_database_from_dependencies(repo_path)
        found_databases.update(db_from_deps)

        # Scan model files
        model_files = self._find_model_files(repo_path)
        for file_path in model_files[:8]:  # Limit files
            orm, db = self._scan_file_for_data_patterns(file_path)
            if orm:
                found_orms.add(orm)
            if db:
                found_databases.add(db)
            files_scanned += 1

        # Detect migration tools
        migration_tools = self._detect_migration_tools(repo_path)
        found_orms.update(migration_tools)

        # Set primary signals
        if found_orms:
            # Pick most common ORM
            signals["data_layer"] = self._pick_primary_orm(found_orms)
            signals["orm_patterns"] = sorted(found_orms)

        if found_databases:
            # Pick most likely database
            signals["database_type"] = self._pick_primary_database(
                found_databases)

        return ExtractionResult(
            success=True,
            signals=signals,
            files_scanned=files_scanned,
        )

    def _detect_orm_from_dependencies(self, repo_path: Path) -> Set[str]:
        """Detect ORM from dependency files."""
        orms = set()

        # Python requirements.txt
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            content = self.safe_read_file(req_file, max_bytes=5000).lower()

            orm_libs = {
                "sqlalchemy": "sqlalchemy",
                "django": "django_orm",
                "tortoise": "tortoise",
                "peewee": "peewee",
                "pony": "pony",
            }

            for lib, orm_name in orm_libs.items():
                if lib in content:
                    orms.add(orm_name)

        # Node package.json
        package_file = repo_path / "package.json"
        if package_file.exists():
            content = self.safe_read_file(package_file, max_bytes=5000).lower()

            orm_libs = {
                "prisma": "prisma",
                "mongoose": "mongoose",
                "sequelize": "sequelize",
                "typeorm": "typeorm",
                "knex": "knex",
            }

            for lib, orm_name in orm_libs.items():
                if lib in content:
                    orms.add(orm_name)

        return orms

    def _detect_database_from_dependencies(self, repo_path: Path) -> Set[str]:
        """Detect database from dependency files."""
        databases = set()

        # Python requirements.txt
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            content = self.safe_read_file(req_file, max_bytes=5000).lower()

            db_libs = {
                "psycopg": "postgresql",
                "asyncpg": "postgresql",
                "pymongo": "mongodb",
                "motor": "mongodb",
                "pymysql": "mysql",
                "aiomysql": "mysql",
                "redis": "redis",
                "aioredis": "redis",
                "sqlite": "sqlite",
            }

            for lib, db_name in db_libs.items():
                if lib in content:
                    databases.add(db_name)

        # Node package.json
        package_file = repo_path / "package.json"
        if package_file.exists():
            content = self.safe_read_file(package_file, max_bytes=5000).lower()

            db_libs = {
                "pg": "postgresql",
                "mysql": "mysql",
                "mongodb": "mongodb",
                "redis": "redis",
                "sqlite3": "sqlite",
                "@prisma/client": "postgresql",  # Prisma usually implies SQL
            }

            for lib, db_name in db_libs.items():
                if lib in content:
                    databases.add(db_name)

        return databases

    def _find_model_files(self, repo_path: Path) -> List[Path]:
        """Find files likely to contain data models."""
        files = []

        # Target directories
        target_dirs = ["models", "db", "database", "schema", "entities"]

        for dir_name in target_dirs:
            dir_path = repo_path / dir_name
            if dir_path.exists():
                files.extend(dir_path.glob("*.py"))
                files.extend(dir_path.glob("*.js"))
                files.extend(dir_path.glob("*.ts"))

        # Look for files with "model" in name
        for path in repo_path.rglob("*model*.py"):
            if path.is_file():
                files.append(path)

        # Deduplicate and limit
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen and len(unique_files) < 12:
                seen.add(f)
                unique_files.append(f)

        return unique_files

    def _scan_file_for_data_patterns(
        self,
        file_path: Path,
    ) -> tuple[Optional[str], Optional[str]]:
        """Scan file for ORM and database patterns."""
        orm_found = None
        db_found = None

        try:
            content = self.safe_read_file(file_path, max_bytes=20000)
            if not content:
                return None, None

            content_lower = content.lower()
            suffix = file_path.suffix.lower()

            # Determine language
            if suffix == '.py':
                lang = "python"
            elif suffix in ['.js', '.ts']:
                lang = "javascript"
            else:
                return None, None

            # Check ORM patterns
            if lang in self.ORM_PATTERNS:
                for orm_name, patterns in self.ORM_PATTERNS[lang].items():
                    for pattern in patterns:
                        if pattern.lower() in content_lower:
                            orm_found = orm_name
                            break
                    if orm_found:
                        break

            # Check database patterns
            for db_name, patterns in self.DATABASE_PATTERNS.items():
                for pattern in patterns:
                    if pattern in content_lower:
                        db_found = db_name
                        break
                if db_found:
                    break

        except Exception:
            pass

        return orm_found, db_found

    def _detect_migration_tools(self, repo_path: Path) -> Set[str]:
        """Detect database migration tools."""
        tools = set()

        # Alembic
        if (repo_path / "alembic.ini").exists():
            tools.add("alembic")
        if (repo_path / "alembic").exists():
            tools.add("alembic")

        # Django migrations
        migration_dirs = list(repo_path.rglob("migrations"))
        for mdir in migration_dirs:
            if any(f.name.startswith("0001_") for f in mdir.glob("*.py")):
                tools.add("django_migrations")
                break

        # Prisma
        if (repo_path / "prisma" / "schema.prisma").exists():
            tools.add("prisma")

        # TypeORM
        if (repo_path / "ormconfig.json").exists():
            tools.add("typeorm")

        return tools

    def _pick_primary_orm(self, orms: Set[str]) -> str:
        """Pick the primary ORM from detected set."""
        # Priority order
        priority = [
            "sqlalchemy", "django_orm", "prisma", "mongoose",
            "sequelize", "typeorm", "tortoise", "peewee"
        ]

        for orm in priority:
            if orm in orms:
                return orm

        return list(orms)[0] if orms else "unknown"

    def _pick_primary_database(self, databases: Set[str]) -> str:
        """Pick the primary database from detected set."""
        # Priority order (production databases first)
        priority = [
            "postgresql", "mysql", "mongodb", "redis",
            "dynamodb", "elasticsearch", "sqlite"
        ]

        for db in priority:
            if db in databases:
                return db

        return list(databases)[0] if databases else "unknown"
