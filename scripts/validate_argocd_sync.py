#!/usr/bin/env python3
"""
validate_argocd_sync.py — ArgoCD sync validation.

Validates that all ArgoCD Applications in the cluster are Synced and Healthy.
Reports any apps that are OutOfSync, Degraded, Missing, or have other issues.

Usage:
    python3 scripts/validate_argocd_sync.py [--kubeconfig PATH] [--strict] [--help]

Checks:
    [S1] All ArgoCD Applications exist
    [S2] All Applications are Synced
    [S3] All Applications are Healthy
    [S4] No Applications have sync errors or warnings

Exit codes:
    0  All checks passed
    1  Sync validation failures found
    2  Usage error or cluster unreachable
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_kubectl(args: list[str], kubeconfig: str) -> subprocess.CompletedProcess:
    """Run a kubectl command and return the result."""
    cmd = ["kubectl", f"--kubeconfig={kubeconfig}"] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )


def get_argocd_apps(kubeconfig: str) -> list[dict]:
    """Get all ArgoCD Applications from the cluster."""
    result = run_kubectl(
        [
            "get", "applications", "-n", "argocd",
            "-o", "json",
        ],
        kubeconfig,
    )
    if result.returncode != 0:
        print(f"  ERROR: Failed to get ArgoCD applications: {result.stderr.strip()}", file=sys.stderr)
        return []

    try:
        data = json.loads(result.stdout)
        return data.get("items", [])
    except json.JSONDecodeError as e:
        print(f"  ERROR: Failed to parse ArgoCD applications: {e}", file=sys.stderr)
        return []


def check_app_status(app: dict, strict: bool = False) -> list[str]:
    """Check a single ArgoCD Application's sync and health status."""
    errors = []
    metadata = app.get("metadata", {}) or {}
    name = metadata.get("name", "<unknown>")
    status = app.get("status", {}) or {}
    sync = status.get("sync", {}) or {}
    health = status.get("health", {}) or {}
    sync_status = sync.get("status", "")
    health_status = health.get("status", "")

    # [S2] Check sync status
    if sync_status != "Synced":
        errors.append(
            f"[S2] {name}: sync status = '{sync_status}' (expected 'Synced')"
        )

    # [S3] Check health status
    if health_status != "Healthy":
        errors.append(
            f"[S3] {name}: health status = '{health_status}' (expected 'Healthy')"
        )

    # [S4] Check for sync errors or warnings (strict mode)
    if strict:
        # Check for resources with sync errors
        resources = status.get("resources", [])
        for res in resources:
            res_health = res.get("health", {}) or {}
            res_sync = res.get("sync", {}) or {}
            if res_health.get("status") == "Degraded":
                res_name = res.get("name", "<unknown>")
                errors.append(
                    f"[S4] {name} → {res_name}: resource health = 'Degraded'"
                )
            if res_sync.get("status") == "OutOfSync":
                res_name = res.get("name", "<unknown>")
                errors.append(
                    f"[S4] {name} → {res_name}: resource sync = 'OutOfSync'"
                )

        # Check for operation errors
        operation_state = status.get("operationState", {}) or {}
        if operation_state.get("phase") in ("Error", "Failed"):
            message = operation_state.get("message", "unknown error")
            errors.append(
                f"[S4] {name}: operation error = '{message}'"
            )

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate ArgoCD sync status (all apps synced and healthy)"
    )
    parser.add_argument(
        "--kubeconfig",
        default=None,
        help="Path to kubeconfig file (default: $KUBECONFIG)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also check individual resource health and sync errors",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only print summary table, not individual issues",
    )
    args = parser.parse_args()

    # Resolve kubeconfig
    kubeconfig = args.kubeconfig or ""
    if not kubeconfig:
        kubeconfig = "default"

    print(f"=== ArgoCD sync validation (kubeconfig={kubeconfig}) ===\n")

    # Check cluster connectivity
    result = run_kubectl(["cluster-info"], kubeconfig)
    if result.returncode != 0:
        print("  ERROR: Cannot connect to cluster", file=sys.stderr)
        print(f"  {result.stderr.strip()}", file=sys.stderr)
        return 2

    # Get ArgoCD Applications
    apps = get_argocd_apps(kubeconfig)
    if not apps:
        print("  No ArgoCD Applications found in cluster")
        print("  Make sure ArgoCD is installed and Apps are deployed")
        return 2

    # Validate each app
    all_errors = []
    synced_count = 0
    healthy_count = 0
    total = len(apps)

    for app in apps:
        metadata = app.get("metadata", {}) or {}
        name = metadata.get("name", "<unknown>")
        errors = check_app_status(app, args.strict)
        status = app.get("status", {}) or {}
        sync = status.get("sync", {}) or {}
        health = status.get("health", {}) or {}

        if sync.get("status") == "Synced":
            synced_count += 1
        if health.get("status") == "Healthy":
            healthy_count += 1

        if errors:
            all_errors.extend(errors)
            if not args.summary_only:
                for e in errors:
                    print(f"  {e}")

    # Print summary
    print(f"\n--- Summary ---\n")
    print(f"  Total Applications: {total}")
    print(f"  Synced:             {synced_count}/{total}")
    print(f"  Healthy:            {healthy_count}/{total}")
    print(f"  Issues found:       {len(all_errors)}")

    if apps and not args.summary_only:
        print(f"\n--- Application Details ---\n")
        for app in apps:
            metadata = app.get("metadata", {}) or {}
            name = metadata.get("name", "<unknown>")
            status = app.get("status", {}) or {}
            sync = status.get("sync", {}) or {}
            health = status.get("health", {}) or {}
            sync_status = sync.get("status", "Unknown")
            health_status = health.get("status", "Unknown")

            icon = "✓" if (sync_status == "Synced" and health_status == "Healthy") else "✗"
            print(f"  {icon} {name}: sync={sync_status}, health={health_status}")

    # Final result
    print(f"\n=== Results ===\n")

    if not apps:
        print("FAIL — no ArgoCD Applications found")
        return 2

    if synced_count != total or healthy_count != total:
        print("FAIL — not all applications are Synced and Healthy")
        if all_errors and not args.summary_only:
            print(f"\n  {len(all_errors)} issue(s) detected — see above")
        return 1

    print("PASS — all applications are Synced and Healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
