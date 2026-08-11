#!/usr/bin/env python3
"""
deploy_apps.py — sync ArgoCD Applications managed by this repository.

This script deploys apps by asking ArgoCD to sync existing Application
resources. It does not create Application CRs directly.

Examples:
    venv/bin/python scripts/deploy_apps.py --scope platform --env dev
    venv/bin/python scripts/deploy_apps.py --scope platform --env prod
    venv/bin/python scripts/deploy_apps.py --app platform-shared-prod

Exit codes:
    0  All requested apps synced and became healthy
    1  Sync failed for at least one app
    2  Usage error or CLI failure
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


VALID_SCOPES = {"platform", "tenants", "all"}
VALID_ENVS = {"dev", "test", "prod", "all"}
APP_SUFFIXES = {"dev", "test", "prod"}
AUTH_ERROR_MARKERS = (
    "Unauthenticated",
    "invalid session",
    "token has invalid claims",
    "token is expired",
)
BOOTSTRAP_ERROR_MARKERS = (
    'configmap "argocd-cm" not found',
    'configmap argocd-cm not found',
    'argocd-cm not found',
)


@dataclass(frozen=True)
class AppSpec:
    name: str
    manifest_path: Path
    scope: str
    environment: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True)


def is_auth_error(result: subprocess.CompletedProcess[str]) -> bool:
    combined_output = f"{result.stdout}\n{result.stderr}"
    return any(marker in combined_output for marker in AUTH_ERROR_MARKERS)


def is_bootstrap_missing_error(result: subprocess.CompletedProcess[str]) -> bool:
    combined_output = f"{result.stdout}\n{result.stderr}"
    return any(marker in combined_output for marker in BOOTSTRAP_ERROR_MARKERS)


def print_auth_error() -> None:
    print(
        "ERROR: ArgoCD authentication session is expired or invalid.",
        file=sys.stderr,
    )
    print(
        "Rerun ./scripts/argocd_sync.sh so the shell wrapper can refresh from tmp/.credentials, or use --core for direct cluster mode.",
        file=sys.stderr,
    )
    print(
        "Example: ./scripts/argocd_sync.sh --scope platform --env dev",
        file=sys.stderr,
    )
    print(
        "If you already refreshed the session, confirm the CLI points at the right context.",
        file=sys.stderr,
    )


def require_argocd_cli() -> None:
    result = run_command(["argocd", "version", "--client"])
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "argocd CLI is unavailable"
        print(f"ERROR: {message}", file=sys.stderr)
        raise SystemExit(2)


def is_argocd_installed() -> bool:
    result = run_command(["kubectl", "get", "configmap", "argocd-cm", "-n", "argocd"])
    return result.returncode == 0


def print_bootstrap_error() -> None:
    print(
        "ERROR: ArgoCD is not installed in the current Kubernetes cluster.",
        file=sys.stderr,
    )
    print(
        "This deploy helper can only sync existing ArgoCD Applications after the",
        file=sys.stderr,
    )
    print(
        "ArgoCD control plane has been bootstrapped.",
        file=sys.stderr,
    )
    print(
        "Run ./scripts/bootstrap_argocd.sh --env dev|test|prod first, then rerun ./scripts/argocd_sync.sh.",
        file=sys.stderr,
    )


def infer_scope(manifest_path: Path) -> str:
    parts = manifest_path.parts
    if "apps" not in parts:
        raise ValueError(f"Cannot infer scope for {manifest_path}")

    index = parts.index("apps")
    if len(parts) <= index + 1:
        raise ValueError(f"Cannot infer scope for {manifest_path}")

    scope = parts[index + 1]
    if scope not in {"platform", "tenants"}:
        raise ValueError(f"Unsupported scope '{scope}' in {manifest_path}")

    return scope


def infer_environment(manifest_path: Path) -> str:
    suffix = manifest_path.stem.rsplit("-", 1)[-1]
    if suffix in APP_SUFFIXES:
        return suffix
    return "all"


def load_application_specs(root: Path) -> list[AppSpec]:
    try:
        import yaml
    except Exception as exc:  # pragma: no cover - import failure is environment specific
        raise SystemExit(f"ERROR: PyYAML is required: {exc}") from exc

    specs: list[AppSpec] = []
    for manifest_path in sorted(root.glob("apps/**/argocd/*.yml")):
        if not manifest_path.is_file():
            continue

        scope = infer_scope(manifest_path)
        environment = infer_environment(manifest_path)

        with manifest_path.open() as handle:
            for document in yaml.safe_load_all(handle):
                if not document or document.get("kind") != "Application":
                    continue

                metadata = document.get("metadata") or {}
                name = metadata.get("name")
                if not name:
                    raise SystemExit(f"ERROR: missing metadata.name in {manifest_path}")

                specs.append(
                    AppSpec(
                        name=name,
                        manifest_path=manifest_path,
                        scope=scope,
                        environment=environment,
                    )
                )

    return specs


def select_apps(specs: list[AppSpec], scope: str, environment: str, app_names: list[str]) -> list[AppSpec]:
    if app_names:
        selected: list[AppSpec] = []
        missing: list[str] = []
        by_name = {spec.name: spec for spec in specs}
        for name in app_names:
            spec = by_name.get(name)
            if spec is None:
                missing.append(name)
                continue
            selected.append(spec)

        if missing:
            raise SystemExit(f"ERROR: unknown ArgoCD application(s): {', '.join(missing)}")

        return selected

    selected = []
    for spec in specs:
        if scope != "all" and spec.scope != scope:
            continue
        if environment != "all" and spec.environment != environment:
            continue
        selected.append(spec)

    return selected


def build_argocd_command(base_command: list[str], use_core: bool) -> list[str]:
    command = list(base_command)
    if use_core:
        command.append("--core")
    return command


def sync_app(app: AppSpec, prune: bool, wait_timeout: int, use_core: bool) -> None:
    sync_command = build_argocd_command(["argocd", "app", "sync", app.name], use_core)
    if prune:
        sync_command.append("--prune")

    print(f"==> Syncing {app.name} ({app.manifest_path.relative_to(repo_root())})")
    result = run_command(sync_command)
    if result.returncode != 0:
        if is_bootstrap_missing_error(result):
            print_bootstrap_error()
            raise SystemExit(2)
        if is_auth_error(result):
            if not use_core and not is_argocd_installed():
                print_bootstrap_error()
                raise SystemExit(2)
            print_auth_error()
            raise SystemExit(2)
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        raise SystemExit(1)

    wait_command = build_argocd_command(["argocd", "app", "wait", app.name, "--sync", "--health", "--timeout", str(wait_timeout)], use_core)
    result = run_command(wait_command)
    if result.returncode != 0:
        if is_bootstrap_missing_error(result):
            print_bootstrap_error()
            raise SystemExit(2)
        if is_auth_error(result):
            if not use_core and not is_argocd_installed():
                print_bootstrap_error()
                raise SystemExit(2)
            print_auth_error()
            raise SystemExit(2)
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        raise SystemExit(1)

    print(f"    OK {app.name} is Synced and Healthy")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync ArgoCD Applications managed by this repository")
    parser.add_argument(
        "--scope",
        choices=sorted(VALID_SCOPES),
        default="platform",
        help="Filter by repo scope (default: platform)",
    )
    parser.add_argument(
        "--env",
        choices=sorted(VALID_ENVS),
        default="all",
        help="Filter by environment suffix in the Application manifest filename (default: all)",
    )
    parser.add_argument(
        "--app",
        dest="apps",
        action="append",
        default=[],
        help="Sync only the named ArgoCD Application (repeatable)",
    )
    parser.add_argument(
        "--no-prune",
        action="store_true",
        help="Sync without pruning removed resources",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=600,
        help="Seconds to wait for each app to become Synced and Healthy (default: 600)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the selected apps without syncing them",
    )
    parser.add_argument(
        "--core",
        action="store_true",
        help="Use ArgoCD core mode directly against the Kubernetes cluster",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    require_argocd_cli()

    if not args.list and not is_argocd_installed():
        print_bootstrap_error()
        return 2

    root = repo_root()
    specs = load_application_specs(root)
    selected = select_apps(specs, args.scope, args.env, args.apps)

    if not selected:
        print("ERROR: no ArgoCD Applications matched the requested filters", file=sys.stderr)
        return 2

    print("Selected ArgoCD Applications:")
    for app in selected:
        print(f"  - {app.name} [{app.scope}/{app.environment}] -> {app.manifest_path.relative_to(root)}")

    if args.list:
        return 0

    prune = not args.no_prune
    for app in selected:
        sync_app(app, prune=prune, wait_timeout=args.wait_timeout, use_core=args.core)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())