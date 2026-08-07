#!/usr/bin/env bash
# ============================================================================
# smoke_dq.sh — Smoke checks for dq-made-easy tenant
#
# Validates that dq-made-easy services are deployed and healthy after ArgoCD
# sync. Runs against dev or test Kind cluster.
#
# Usage: scripts/smoke/smoke_dq.sh --env dev|test [options]
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
# Defaults
# ---------------------------------------------------------------------------

case "${ENVIRONMENT:-}" in
  dev)
    NAMESPACE="dq-dev"
    KUBECONFIG="${REPO_ROOT}/tmp/kubeconfig/platform-dev-kubeconfig"
    ;;
  test)
    NAMESPACE="dq-test"
    KUBECONFIG="${REPO_ROOT}/tmp/kubeconfig/platform-test-kubeconfig"
    ;;
esac

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

usage() {
  cat <<'USAGE'
Usage: scripts/smoke/smoke_dq.sh --env dev|test [options]

Smoke checks for dq-made-easy tenant.

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

# Re-evaluate after parsing
case "$ENVIRONMENT" in
  dev)
    NAMESPACE="dq-dev"
    KUBECONFIG="${KUBECONFIG:-${REPO_ROOT}/tmp/kubeconfig/platform-dev-kubeconfig}"
    ;;
  test)
    NAMESPACE="dq-test"
    KUBECONFIG="${KUBECONFIG:-${REPO_ROOT}/tmp/kubeconfig/platform-test-kubeconfig}"
    ;;
esac

# ---------------------------------------------------------------------------
# Run checks
# ---------------------------------------------------------------------------

export KUBECONFIG

echo "=== Smoke checks: dq-made-easy ($ENVIRONMENT) ==="
echo ""

# [1] Namespace
echo "--- Namespace ---"
check "Namespace $NAMESPACE exists" kubectl get namespace "$NAMESPACE"

# [2] Pods
echo ""
echo "--- Pods ---"
expected_pods=("dq-api" "dq-ui" "dq-engine")
for pod_prefix in "${expected_pods[@]}"; do
  check "Pod $pod_prefix is running" \
    kubectl get pods -n "$NAMESPACE" -l "platform.jaccloud.nl/service=${pod_prefix}" -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q Running || \
    kubectl get pods -n "$NAMESPACE" 2>/dev/null | grep -q "${pod_prefix}"
done

# [3] ArgoCD Applications
echo ""
echo "--- ArgoCD Applications ---"
argocd_apps=("tenant-dq-api" "tenant-dq-ui" "tenant-dq-engine")
if [[ "$ENVIRONMENT" == "test" ]]; then
  argocd_apps=("tenant-dq-api-test" "tenant-dq-ui-test" "tenant-dq-engine-test")
fi

for app in "${argocd_apps[@]}"; do
  check "ArgoCD app $app is Synced + Healthy" \
    kubectl get application "$app" -n argocd -o jsonpath='{.status.sync.status}{.status.health.status}' 2>/dev/null | grep -q "SyncedHealthy"
done

# [4] Health endpoints (via ingress)
echo ""
echo "--- Health endpoints ---"

if [[ "$ENVIRONMENT" == "dev" ]]; then
  check_health_endpoint "dq-api.dev.jac.dot" "/health"
  check_health_endpoint "dq-ui.dev.jac.dot" "/"
  check_health_endpoint "dq-engine.dev.jac.dot" "/docs"
else
  check_health_endpoint "dq-api.jacloud.nl" "/health"
  check_health_endpoint "dq-ui.jacloud.nl" "/"
  check_health_endpoint "dq-engine.jacloud.nl" "/docs"
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
