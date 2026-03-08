"""
Infra Extractor - Phase 3

Detects deployment infrastructure and CI/CD patterns.
Lightweight file presence and content scanning.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .base_extractor import BaseExtractor, ExtractionResult


class InfraExtractor(BaseExtractor):
    """
    Extracts infrastructure and deployment signals.

    Detects:
    - Docker/containerization
    - Kubernetes
    - CI/CD pipelines
    - Infrastructure as Code (Terraform, Pulumi)
    - Cloud platforms
    """

    # Infrastructure file patterns
    INFRA_FILES = {
        "docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore"],
        "kubernetes": ["*.yaml", "*.yml"],  # In k8s/ or manifests/ dirs
        "github_actions": [".github/workflows/*.yml", ".github/workflows/*.yaml"],
        "gitlab_ci": [".gitlab-ci.yml"],
        "terraform": ["*.tf", "*.tfvars"],
        "pulumi": ["Pulumi.yaml", "Pulumi.yml"],
        "helm": ["Chart.yaml", "values.yaml"],
        "serverless": ["serverless.yml", "serverless.yaml"],
    }

    # Cloud platform detection
    CLOUD_PATTERNS = {
        "aws": ["aws", "amazon", "lambda", "ecs", "eks", "s3", "dynamodb"],
        "gcp": ["gcp", "google cloud", "app engine", "cloud run", "gke"],
        "azure": ["azure", "azurerm", "aks", "app service"],
        "vercel": ["vercel", "now.json"],
        "netlify": ["netlify", "netlify.toml"],
        "heroku": ["heroku", "Procfile", "app.json"],
    }

    def can_run(self, repo_analysis: Dict[str, Any]) -> bool:
        """Always run - infra detection is lightweight."""
        return True

    def extract(
        self,
        repo_path: Path,
        repo_analysis: Dict[str, Any],
    ) -> ExtractionResult:
        """Extract infrastructure signals."""
        signals = {
            "infra_features": [],
            "deployment_target": None,
        }

        files_scanned = 0
        found_features: Set[str] = set()

        # Detect containerization
        if self._detect_docker(repo_path):
            found_features.add("docker")
            files_scanned += 1

        # Detect Kubernetes
        if self._detect_kubernetes(repo_path):
            found_features.add("kubernetes")
            found_features.add("container_orchestration")
            files_scanned += 1

        # Detect CI/CD
        cicd_features = self._detect_cicd(repo_path)
        found_features.update(cicd_features)
        files_scanned += len(cicd_features)

        # Detect IaC
        iac_features = self._detect_iac(repo_path)
        found_features.update(iac_features)
        files_scanned += len(iac_features)

        # Detect cloud platform
        cloud = self._detect_cloud_platform(repo_path)
        if cloud:
            signals["deployment_target"] = cloud
            found_features.add(cloud)

        # Convert to sorted list
        signals["infra_features"] = sorted(found_features)

        return ExtractionResult(
            success=True,
            signals=signals,
            files_scanned=files_scanned,
        )

    def _detect_docker(self, repo_path: Path) -> bool:
        """Detect Docker usage."""
        for filename in self.INFRA_FILES["docker"]:
            if (repo_path / filename).exists():
                return True
        return False

    def _detect_kubernetes(self, repo_path: Path) -> bool:
        """Detect Kubernetes manifests."""
        # Check for k8s directories
        k8s_dirs = ["k8s", "kubernetes", "manifests", "deploy", "deployment"]

        for dir_name in k8s_dirs:
            dir_path = repo_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                # Check for yaml files
                yaml_files = list(dir_path.glob("*.yaml")) + \
                    list(dir_path.glob("*.yml"))
                if yaml_files:
                    # Quick check for k8s keywords in first file
                    sample = yaml_files[0]
                    content = self.safe_read_file(sample, max_bytes=2000)
                    k8s_keywords = ["apiVersion:", "kind:",
                                    "Deployment", "Service", "Pod"]
                    if any(kw in content for kw in k8s_keywords):
                        return True

        return False

    def _detect_cicd(self, repo_path: Path) -> Set[str]:
        """Detect CI/CD configurations."""
        features = set()

        # GitHub Actions
        github_workflows = repo_path / ".github" / "workflows"
        if github_workflows.exists():
            workflow_files = list(github_workflows.glob(
                "*.yml")) + list(github_workflows.glob("*.yaml"))
            if workflow_files:
                features.add("github_actions")
                features.add("ci_cd")

        # GitLab CI
        if (repo_path / ".gitlab-ci.yml").exists():
            features.add("gitlab_ci")
            features.add("ci_cd")

        # Jenkins
        jenkins_files = ["Jenkinsfile", "jenkinsfile"]
        if any((repo_path / f).exists() for f in jenkins_files):
            features.add("jenkins")
            features.add("ci_cd")

        # CircleCI
        if (repo_path / ".circleci" / "config.yml").exists():
            features.add("circleci")
            features.add("ci_cd")

        # Travis CI
        if (repo_path / ".travis.yml").exists():
            features.add("travis_ci")
            features.add("ci_cd")

        return features

    def _detect_iac(self, repo_path: Path) -> Set[str]:
        """Detect Infrastructure as Code."""
        features = set()

        # Terraform
        tf_files = list(repo_path.glob("*.tf"))
        if tf_files:
            features.add("terraform")
            features.add("infrastructure_as_code")

        # Pulumi
        if (repo_path / "Pulumi.yaml").exists() or (repo_path / "Pulumi.yml").exists():
            features.add("pulumi")
            features.add("infrastructure_as_code")

        # Helm
        if (repo_path / "Chart.yaml").exists():
            features.add("helm")

        # Serverless Framework
        if (repo_path / "serverless.yml").exists() or (repo_path / "serverless.yaml").exists():
            features.add("serverless_framework")
            features.add("serverless")

        # AWS CDK
        cdk_files = list(repo_path.rglob("cdk.json"))
        if cdk_files:
            features.add("aws_cdk")
            features.add("infrastructure_as_code")

        return features

    def _detect_cloud_platform(self, repo_path: Path) -> Optional[str]:
        """Detect target cloud platform."""
        scores = {platform: 0 for platform in self.CLOUD_PATTERNS.keys()}

        # Scan terraform files for cloud provider
        tf_files = list(repo_path.glob("*.tf"))
        for tf_file in tf_files[:3]:  # Limit files
            content = self.safe_read_file(tf_file, max_bytes=10000).lower()

            if "aws" in content or "amazon" in content:
                scores["aws"] += 2
            if "azurerm" in content or "azure" in content:
                scores["azure"] += 2
            if "google" in content or "gcp" in content:
                scores["gcp"] += 2

        # Check for platform-specific files
        if (repo_path / "vercel.json").exists():
            scores["vercel"] += 3

        if (repo_path / "netlify.toml").exists():
            scores["netlify"] += 3

        if (repo_path / "Procfile").exists():
            scores["heroku"] += 2

        # Check requirements/package files for cloud SDKs
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            content = self.safe_read_file(req_file, max_bytes=3000).lower()
            if "boto3" in content:
                scores["aws"] += 1
            if "azure" in content:
                scores["azure"] += 1
            if "google-cloud" in content:
                scores["gcp"] += 1

        # Return platform with highest score (if any)
        max_score = max(scores.values()) if scores else 0
        if max_score > 0:
            return max(scores.keys(), key=lambda k: scores[k])

        return None
