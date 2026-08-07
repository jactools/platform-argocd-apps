#!/usr/bin/env bash
# ============================================================================
# smoke_maas.sh — Smoke checks for metadata-as-a-service tenant
#
# Validates that MaaS services are deployed and healthy after ArgoCD sync.
# Runs against dev or test Kind cluster.
#
# Usage: scripts/smoke/smoke_maas.sh --env dev|test [options]
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ENVIRONMENT=""
NAMESPACE=""
KUBECONFIG=""
PASS=0
FAIL=0
TOTAL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

usage() {
  cat <<'USAGE'
Usage: scripts/smoke/smoke_maas.sh --env dev|test [options]

Smoke checks for metadata-as-a-service tenant.

Options:
  --env dev|test   Target environment (required)
  --kubeconfig P   Path to kubeconfig file
  --help           Show this help

Checks:
  [1] Namespace exists
  [2] All expected pods are running
  [3] ArgoCD Applications are Synced + Healthy
  [4] Health endpoints respond (via ingress)
USAGE
}

info()  { printf '  ✓ %s\n' "$*"; }
warn()  { printf '  ⚠ %s\n' "$*"; }
pass()  { ((PASS++)); ((TOTAL++)); info "$*"; }
fail()  { ((FAIL++)); ((TOTAL++)); printf '  ✗ %s\n' "$*"; }

check() {
  local desc="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    pass "$desc"
  else
    fail "$desc"
  fi
}

check_health_endpoint() {
  local host="$1"
  local path="$2"
  local desc="Health $path ($host)"

  if curl -sf --max-time 5 "https://${host}:10443${path}" >/dev/null 2>&1; then
    pass "$desc"
  else
    fail "$desc"
  fi
}

# ---------------------------------------------------------------------------
# Parse options
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      if [[ -z "${2:-}" ]]; then echo "--env requires a value"; exit 2; fi
      ENVIRONMENT="$2"; shift 2 ;;
    --kubeconfig)
      if [[ -z "${2:-}" ]]; then echo "--kubeconfig requires a path"; exit 2; fi
      KUBECONFIG="$2"; shift 2 ;;
    --help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 2 ;;
  esac
done

if [[ -z "$ENVIRONMENT" ]]; then
  echo "--env dev|test is required"
  usage
  exit 2
fi

# ---------------------------------------------------------------------------
# Environment defaults
# ---------------------------------------------------------------------------

case "$ENVIRONMENT" in
  dev)
    NAMESPACE="maas-dev"
    KUBECONFIG="${KUBECONFIG:-${REPO_ROOT}/tmp/kubeconfig/platform-dev-kubeconfig}"
    ;;
  test)
    NAMESPACE="maas-test"
    KUBECONFIG="${KUBECONFIG:-${REPO_ROOT}/tmp/kubeconfig/platform-test-kubeconfig}"
    ;;
esac

export KUBECONFIG

# ---------------------------------------------------------------------------
# Run checks
# ---------------------------------------------------------------------------

echo "=== Smoke checks: metadata-as-a-service ($ENVIRONMENT) ==="
echo ""

# [1] Namespace
echo "--- Namespace ---"
check "Namespace $NAMESPACE exists" kubectl get namespace "$NAMESPACE"

# [2] Pods — zone + central + frontend
echo ""
echo "--- Pods ---"
expected_pods=("maas-api" "maas-coordinator" "maas-control-plane" "maas-central-repo" "maas-scenario-catalog" "maas-orchestrator" "maas-bff" "maas-web")
for pod_prefix in "${expected_pods[@]}"; do
  check "Pod $pod_prefix is running" \
    kubectl get pods -n "$NAMESPACE" -l "platform.jaccloud.nl/service=${pod_prefix}" -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q Running || \
    kubectl get pods -n "$NAMESPACE" 2>/dev/null | grep -q "${pod_prefix}"
done

# [3] ArgoCD Applications
echo ""
echo "--- ArgoCD Applications ---"
argocd_apps=("tenant-maas-api" "tenant-maas-coordinator" "tenant-maas-control-plane" "tenant-maas-central-repo" "tenant-maas-scenario-catalog" "tenant-maas-orchestrator" "tenant-maas-bff" "tenant-maas-web")
if [[ "$ENVIRONMENT" == "test" ]]; then
  argocd_apps=("tenant-maas-api-test" "tenant-maas-coordinator-test" "tenant-maas-control-plane-test" "tenant-maas-central-repo-test" "tenant-maas-scenario-catalog-test" "tenant-maas-orchestrator-test" "tenant-maas-bff-test" "tenant-maas-web-test")
fi

for app in "${argocd_apps[@]}"; do
  check "ArgoCD app $app is Synced + Healthy" \
    kubectl get application "$app" -n argocd -o jsonpath='{.status.sync.status}{.status.health.status}' 2>/dev/null | grep -q "SyncedHealthy"
done

# [4] Health endpoints (via ingress)
echo ""
echo "--- Health endpoints ---"

if [[ "$ENVIRONMENT" == "dev" ]]; then
  check_health_endpoint "maas-api.dev.jac.dot" "/health"
  check_health_endpoint "maas-coordinator.dev.jac.dot" "/health"
  check_health_endpoint "maas-control-plane.dev.jac.dot" "/health"
  check_health_endpoint "maas-central-repo.dev.jac.dot" "/health"
  check_health_endpoint "maas-scenario-catalog.dev.jac.dot" "/health"
  check_health_endpoint "maas-orchestrator.dev.jac.dot" "/health"
  check_health_endpoint "maas-bff.dev.jac.dot" "/health"
  check_health_endpoint "maas-ui.dev.jac.dot" "/"
else
  check_health_endpoint "maas-api.jacloud.nl" "/health"
  check_health_endpoint "maas-coordinator.jacloud.nl" "/health"
  check_health_endpoint "maas-control-plane.jacloud.nl" "/health"
  check_health_endpoint "maas-central-repo.jacloud.nl" "/health"
  check_health_endpoint "maas-scenario-catalog.jacloud.nl" "/health"
  check_health_endpoint "maas-orchestrator.jacloud.nl" "/health"
  check_health_endpoint "maas-bff.jacloud.nl" "/health"
  check_health_endpoint "maas-ui.jacloud.nl" "/"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo ""
echo "=== Results: $PASS/$TOTAL passed, $FAIL failed ==="

if [[ $FAIL -gt 0 ]]; then
  echo "Smoke checks FAILED"
  exit 1
fi

echo "Smoke checks PASSED"
exit 0
