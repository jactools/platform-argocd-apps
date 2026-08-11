#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/bootstrap_argocd.sh --env dev|test|prod [--install-url URL]

Bootstraps ArgoCD into the cluster, then applies the repo-managed root
Application for the selected environment.

Options:
  --env         Required. Bootstrap environment: dev, test, or prod.
  --install-url Optional. ArgoCD install manifest URL.
               Default: https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
EOF
}

install_url="https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"
env=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      env="${2:-}"
      shift 2
      ;;
    --install-url)
      install_url="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$env" != "dev" && "$env" != "test" && "$env" != "prod" ]]; then
  echo "ERROR: --env dev|test|prod is required" >&2
  usage >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
root_app="$repo_root/argocd/bootstrap/root-app-${env}.yml"

if [[ ! -f "$root_app" ]]; then
  echo "ERROR: missing bootstrap root app: $root_app" >&2
  exit 2
fi

echo "==> Installing ArgoCD from $install_url"
kubectl apply -n argocd -f "$install_url"

echo "==> Waiting for ArgoCD control plane"
kubectl wait --for=condition=Available deployment/argocd-server -n argocd --timeout=300s
kubectl wait --for=condition=Available deployment/argocd-repo-server -n argocd --timeout=300s
kubectl wait --for=condition=Available deployment/argocd-application-controller -n argocd --timeout=300s

if kubectl -n argocd get configmap argocd-cm >/dev/null 2>&1; then
  echo "==> ArgoCD configmap is present"
fi

echo "==> Applying bootstrap root app: ${root_app##$repo_root/}"
kubectl apply -f "$root_app"

echo "==> Bootstrap completed"
