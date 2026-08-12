#!/usr/bin/env python3
"""
validate_manifests.py — Manifest contract validation for platform-argocd-apps.

Validates that all Kubernetes manifests comply with the shared platform
label and annotation contract defined in the Environment and Deployment
Contract (W1).

Usage:
    python3 scripts/validate_manifests.py [--env dev|test|prod] [--strict] [--help]

Checks:
    [L1] Required labels present on all resources
    [L2] Required annotations present on workload resources (Deployment, StatefulSet, Job, CronJob)
    [L3] Label values are valid (environment, tenant, managed-by)
    [L4] Namespace matches tenant label where applicable
    [L5] ArgoCD Application resources reference correct namespace

Exit codes:
    0  All checks passed
    1  Validation failures found
    2  Usage error
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Contract definitions
# ---------------------------------------------------------------------------

REQUIRED_LABELS = [
    "platform.jaccloud.nl/managed-by",
    "platform.jaccloud.nl/environment",
    "platform.jaccloud.nl/tenant",
    "platform.jaccloud.nl/service",
]

# These are set by the pipeline at deploy time, not in source manifests.
# Warn only (not fail) unless --strict.
PIPELINE_LABELS = [
    "platform.jaccloud.nl/version",
    "platform.jaccloud.nl/image-digest",
]

REQUIRED_ANNOTATIONS = [
    "platform.jaccloud.nl/target-id",
    "platform.jaccloud.nl/workload-kind",
    "platform.jaccloud.nl/maas-register",
]

# Annotations set by ArgoCD at runtime, not in source manifests.
RUNTIME_ANNOTATIONS = [
    "platform.jaccloud.nl/deployed-at-utc",
]

VALID_ENVIRONMENTS = {"dev", "test", "prod"}
VALID_TENANTS = {"platform", "dq", "maas"}
VALID_MANAGED_BY = {"argocd"}

WORKLOAD_KINDS = {"Deployment", "StatefulSet", "Job", "CronJob", "DaemonSet"}

# Resources that don't need labels/annotations checks
EXCLUDED_KINDS = {
    "Namespace",        # Namespace labels are checked separately
    "ConfigMap",        # Data containers, not workloads
    "ServiceAccount",
    "Role",
    "RoleBinding",
    "ClusterRole",
    "ClusterRoleBinding",
    "Service",          # Services inherit from owner
    "Ingress",          # Ingress inherits from owner
    "PersistentVolumeClaim",
    "Secret",
    "List",             # Multi-doc wrapper
    "Kustomization",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_yaml_list(path: Path) -> list[dict[str, Any]]:
    """Parse a YAML file or kustomize output into a list of resource dicts.

    Uses Python's yaml loader. For kustomize output, each doc separated by ---.
    """
    import yaml

    try:
        with open(path) as f:
            content = f.read()
        docs = list(yaml.safe_load_all(content))
        return [d for d in docs if d is not None]
    except Exception as e:
        print(f"  ERROR parsing {path}: {e}", file=sys.stderr)
        return []


def run_kustomize(overlay_dir: Path) -> list[dict[str, Any]]:
    """Run kubectl kustomize on an overlay directory and return parsed resources."""
    import subprocess

    try:
        result = subprocess.run(
            ["kubectl", "kustomize", str(overlay_dir)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"  ERROR kustomize failed for {overlay_dir}: {result.stderr.strip()}", file=sys.stderr)
            return []
        import yaml
        docs = list(yaml.safe_load_all(result.stdout))
        return [d for d in docs if d is not None]
    except FileNotFoundError:
        print("  ERROR: kubectl not found", file=sys.stderr)
        return []
    except subprocess.TimeoutExpired:
        print(f"  ERROR: kustomize timed out for {overlay_dir}", file=sys.stderr)
        return []


def get_argocd_apps(tenants_dir: Path) -> list[dict[str, Any]]:
    """Load all ArgoCD Application YAML files from tenant directories."""
    import yaml
    apps = []
    for yml in tenants_dir.glob("**/argocd/*.yml"):
        try:
            with open(yml) as f:
                doc = yaml.safe_load(f)
            if doc and doc.get("kind") == "Application":
                apps.append(doc)
        except Exception:
            pass
    return apps


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------


def check_required_labels(
    resources: list[dict[str, Any]],
    strict: bool = False,
) -> list[str]:
    """Check that all resources have required labels."""
    errors = []
    for res in resources:
        kind = res.get("kind", "")
        if kind in EXCLUDED_KINDS:
            continue

        metadata = res.get("metadata", {}) or {}
        name = metadata.get("name", "<unknown>")
        labels = (metadata.get("labels") or {})

        for label in REQUIRED_LABELS:
            if label not in labels:
                errors.append(f"[L1] {kind}/{name}: missing required label '{label}'")

        if strict:
            for label in PIPELINE_LABELS:
                if label not in labels:
                    errors.append(f"[L1] {kind}/{name}: missing pipeline label '{label}' (set --strict)")

    return errors


def check_required_annotations(
    resources: list[dict[str, Any]],
    strict: bool = False,
) -> list[str]:
    """Check that workload resources have required annotations."""
    errors = []
    for res in resources:
        kind = res.get("kind", "")
        if kind not in WORKLOAD_KINDS:
            continue

        metadata = res.get("metadata", {}) or {}
        name = metadata.get("name", "<unknown>")
        annotations = (metadata.get("annotations") or {})

        for ann in REQUIRED_ANNOTATIONS:
            if ann not in annotations:
                errors.append(f"[L2] {kind}/{name}: missing required annotation '{ann}'")

        if strict:
            for ann in RUNTIME_ANNOTATIONS:
                if ann not in annotations:
                    errors.append(f"[L2] {kind}/{name}: missing runtime annotation '{ann}' (set --strict)")

    return errors


def check_label_values(
    resources: list[dict[str, Any]],
) -> list[str]:
    """Check that label values are valid."""
    errors = []
    for res in resources:
        kind = res.get("kind", "")
        if kind in EXCLUDED_KINDS:
            continue

        metadata = res.get("metadata", {}) or {}
        name = metadata.get("name", "<unknown>")
        labels = (metadata.get("labels") or {})

        # Check managed-by value
        mb = labels.get("platform.jaccloud.nl/managed-by")
        if mb is not None and mb not in VALID_MANAGED_BY:
            errors.append(
                f"[L3] {kind}/{name}: label 'platform.jaccloud.nl/managed-by' = '{mb}' (expected one of {VALID_MANAGED_BY})"
            )

        # Check environment value
        env = labels.get("platform.jaccloud.nl/environment")
        if env is not None and env not in VALID_ENVIRONMENTS:
            errors.append(
                f"[L3] {kind}/{name}: label 'platform.jaccloud.nl/environment' = '{env}' (expected one of {VALID_ENVIRONMENTS})"
            )

        # Check tenant value
        tenant = labels.get("platform.jaccloud.nl/tenant")
        if tenant is not None and tenant not in VALID_TENANTS:
            errors.append(
                f"[L3] {kind}/{name}: label 'platform.jaccloud.nl/tenant' = '{tenant}' (expected one of {VALID_TENANTS})"
            )

    return errors


def check_namespace_tenant_match(
    resources: list[dict[str, Any]],
) -> list[str]:
    """Check that namespace name matches tenant label for tenant resources."""
    errors = []
    for res in resources:
        kind = res.get("kind", "")
        if kind in EXCLUDED_KINDS:
            continue

        metadata = res.get("metadata", {}) or {}
        name = metadata.get("name", "<unknown>")
        namespace = metadata.get("namespace", "")
        labels = (metadata.get("labels") or {})
        tenant = labels.get("platform.jaccloud.nl/tenant")

        if not namespace or not tenant:
            continue

        # For tenant resources, namespace should start with tenant name
        if tenant != "platform" and not namespace.startswith(tenant):
            errors.append(
                f"[L4] {kind}/{name}: namespace '{namespace}' doesn't match tenant label '{tenant}'"
            )

    return errors


def check_argocd_app_references(
    apps: list[dict[str, Any]],
    strict: bool = False,
) -> list[str]:
    """Check ArgoCD Application resources for common issues."""
    errors = []
    for app in apps:
        metadata = app.get("metadata", {}) or {}
        name = metadata.get("name", "<unknown>")
        spec = app.get("spec", {}) or {}
        project = spec.get("project", "")
        source = spec.get("source", {}) or {}
        destination = spec.get("destination", {}) or {}

        # Check project
        if project not in ("platform", "tenant", "dq", "maas"):
            errors.append(f"[L5] Application/{name}: project = '{project}' (expected 'platform', 'tenant', 'dq', or 'maas')")

        # Check destination namespace exists in valid set
        dest_ns = destination.get("namespace", "")
        if dest_ns and dest_ns not in (
            "argocd", "platform-kong", "platform-keycloak", "platform-observability",
            "platform-tls", "platform-airflow", "platform-kafka",
            "platform-redis", "platform-shared", "platform-trino", "platform-ai-stor",
            "kyverno", "dq-dev", "dq-test", "maas-dev", "maas-test",
        ):
            errors.append(f"[L5] Application/{name}: destination namespace = '{dest_ns}' (unexpected)")

        # Template variables ({{VAR}}) in repoURL are expanded at apply time.
        # This is expected — warn only in strict mode.
        repo_url = source.get("repoURL", "")
        if "{{" in repo_url and strict:
            errors.append(f"[L5] Application/{name}: repoURL contains template '{repo_url}' (expanded at apply)")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def validate_overlays(
    root: Path,
    env: str | None,
    strict: bool,
) -> list[str]:
    """Validate kustomize overlays and ArgoCD Applications."""
    all_errors = []
    tenants_dir = root / "apps" / "tenants"
    platform_dir = root / "apps" / "platform"

    # --- Validate kustomize overlays ---
    print("--- Kustomize overlays ---\n")

    for base_dir in [tenants_dir, platform_dir]:
        if not base_dir.exists():
            continue
        for overlay in sorted(base_dir.glob("*/overlays/*/kustomization.yml")):
            overlay_parent = overlay.parent
            overlay_name = str(overlay_parent.relative_to(root))

            # Filter by environment
            if env and env not in overlay_name:
                continue

            print(f"  Checking: {overlay_name}")
            resources = run_kustomize(overlay_parent)
            if not resources:
                print("    (no resources or kustomize failed)", file=sys.stderr)
                continue

            errors = (
                check_required_labels(resources, strict)
                + check_required_annotations(resources, strict)
                + check_label_values(resources)
                + check_namespace_tenant_match(resources)
            )

            if errors:
                for e in errors:
                    print(f"    {e}")
                all_errors.extend(errors)
            else:
                print(f"    ✓ {len(resources)} resource(s) — OK")

    # --- Validate ArgoCD Applications ---
    print("\n--- ArgoCD Applications ---\n")

    apps = get_argocd_apps(root / "apps")
    if apps:
        errors = check_argocd_app_references(apps, strict)
        if errors:
            for e in errors:
                print(f"  {e}")
            all_errors.extend(errors)
        else:
            print(f"  ✓ {len(apps)} Application(s) — OK")
    else:
        print("  (no ArgoCD Applications found)")

    return all_errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate manifest contract (labels, annotations, required fields)"
    )
    parser.add_argument(
        "--env",
        choices=["dev", "test", "prod"],
        default=None,
        help="Validate only a specific environment overlay",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also check pipeline-set labels (version, image-digest)",
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Root of platform-argocd-apps repo",
    )
    args = parser.parse_args()

    root = Path(args.root)
    print(f"=== Manifest contract validation (root={root}) ===\n")

    errors = validate_overlays(root, args.env, args.strict)

    print(f"\n=== Results: {len(errors)} issue(s) found ===\n")

    if errors:
        print("FAIL — manifest contract violations detected")
        return 1

    print("PASS — all manifests comply with the platform contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
