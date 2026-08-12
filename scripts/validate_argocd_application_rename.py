#!/usr/bin/env python3
"""
validate_argocd_application_rename.py — verify ArgoCD Application rename cutover.

Checks whether the renamed env-suffixed ArgoCD Applications exist in the
cluster, whether the old unsuffixed names still linger, and whether the new
Applications are healthy.

Usage:
    python scripts/validate_argocd_application_rename.py --env dev
    python scripts/validate_argocd_application_rename.py --env test
    python scripts/validate_argocd_application_rename.py --env dev --summary-only

Exit codes:
    0  Rename cutover is complete for the selected environment
    1  Old names still exist, new names are missing, or new apps are unhealthy
    2  Usage error or cluster access failure
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


RENAMED_BASE_NAMES = (
    "platform-airflow",
    "platform-kafka",
    "platform-keycloak",
    "platform-kong",
    "platform-kyverno",
    "platform-kyverno-policies",
    "platform-observability",
    "platform-redis",
    "platform-trino",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_kubectl(args: list[str], kubeconfig: str | None) -> subprocess.CompletedProcess[str]:
    cmd = ["kubectl"]
    if kubeconfig:
        cmd.append(f"--kubeconfig={kubeconfig}")
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


def load_env_file(environment: str) -> dict[str, str]:
    env_file = repo_root() / f".env.{environment}.local"
    if not env_file.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def resolve_kubeconfig(environment: str, cli_kubeconfig: str | None) -> str | None:
    if cli_kubeconfig:
        return cli_kubeconfig

    env_values = load_env_file(environment)
    kubeconfig = env_values.get("KUBECONFIG", "").strip()
    if kubeconfig:
        return kubeconfig

    return None


def get_argocd_apps(kubeconfig: str | None) -> list[dict]:
    result = run_kubectl(["get", "applications", "-n", "argocd", "-o", "json"], kubeconfig)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown kubectl error"
        raise RuntimeError(f"failed to get ArgoCD applications: {message}")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"failed to parse ArgoCD applications JSON: {exc}") from exc

    return payload.get("items", [])


def renamed_pairs(environment: str) -> list[tuple[str, str]]:
    suffix = f"-{environment}"
    return [(old_name, f"{old_name}{suffix}") for old_name in RENAMED_BASE_NAMES]


def evaluate_cutover(apps: list[dict], environment: str) -> dict[str, list[str]]:
    by_name = {app.get("metadata", {}).get("name", "<unknown>"): app for app in apps}

    lingering_old: list[str] = []
    missing_new: list[str] = []
    unhealthy_new: list[str] = []
    healthy_new: list[str] = []

    for old_name, new_name in renamed_pairs(environment):
        if old_name in by_name:
            lingering_old.append(old_name)

        new_app = by_name.get(new_name)
        if new_app is None:
            missing_new.append(new_name)
            continue

        status = new_app.get("status", {}) or {}
        sync_status = (status.get("sync", {}) or {}).get("status", "Unknown")
        health_status = (status.get("health", {}) or {}).get("status", "Unknown")

        if sync_status == "Synced" and health_status == "Healthy":
            healthy_new.append(new_name)
        else:
            unhealthy_new.append(f"{new_name} (sync={sync_status}, health={health_status})")

    return {
        "lingering_old": lingering_old,
        "missing_new": missing_new,
        "unhealthy_new": unhealthy_new,
        "healthy_new": healthy_new,
    }


def print_list(title: str, items: list[str]) -> None:
    print(title)
    if not items:
        print("  - none")
        return
    for item in items:
        print(f"  - {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the ArgoCD Application rename cutover for one environment")
    parser.add_argument("--env", choices=("dev", "test"), required=True, help="Environment to verify")
    parser.add_argument(
        "--kubeconfig",
        default=None,
        help="Optional kubeconfig override (default: KUBECONFIG from .env.<env>.local, then current kubectl context)",
    )
    parser.add_argument("--summary-only", action="store_true", help="Only print the summary counts")
    args = parser.parse_args()

    kubeconfig = resolve_kubeconfig(args.env, args.kubeconfig)

    print(f"=== ArgoCD Application rename validation (env={args.env}) ===\n")
    if kubeconfig:
        print(f"Using kubeconfig: {kubeconfig}\n")

    probe = run_kubectl(["cluster-info"], kubeconfig)
    if probe.returncode != 0:
        message = probe.stderr.strip() or probe.stdout.strip() or "cluster unreachable"
        print(f"ERROR: cannot connect to cluster: {message}", file=sys.stderr)
        return 2

    try:
        apps = get_argocd_apps(kubeconfig)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    result = evaluate_cutover(apps, args.env)
    total_pairs = len(RENAMED_BASE_NAMES)
    healthy_count = len(result["healthy_new"])
    missing_count = len(result["missing_new"])
    unhealthy_count = len(result["unhealthy_new"])
    lingering_count = len(result["lingering_old"])

    print("--- Summary ---\n")
    print(f"  Expected renamed apps: {total_pairs}")
    print(f"  New apps healthy:      {healthy_count}/{total_pairs}")
    print(f"  New apps missing:      {missing_count}")
    print(f"  New apps unhealthy:    {unhealthy_count}")
    print(f"  Old apps lingering:    {lingering_count}")

    if not args.summary_only:
        print("\n--- Details ---\n")
        print_list("Healthy renamed apps:", result["healthy_new"])
        print()
        print_list("Missing renamed apps:", result["missing_new"])
        print()
        print_list("Unhealthy renamed apps:", result["unhealthy_new"])
        print()
        print_list("Lingering old app names:", result["lingering_old"])

    print("\n=== Results ===\n")

    if missing_count or unhealthy_count or lingering_count:
        print("FAIL — rename cutover is incomplete for the selected environment")
        return 1

    print("PASS — rename cutover is complete for the selected environment")
    return 0


if __name__ == "__main__":
    sys.exit(main())