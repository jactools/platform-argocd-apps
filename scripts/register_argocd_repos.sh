#!/usr/bin/env bash
set -euo pipefail

usage() {
	cat <<'EOF'
Usage: ./scripts/register_argocd_repos.sh --env dev|test|prod

Registers the Git repositories that ArgoCD needs to resolve these
Applications. The script loads the matching repo-root env file:

	.env.dev.local
	.env.test.local
	.env.prod.local

You can also export variables in the shell before running the script, but the
selected env file is loaded first.

Required environment variables:
  ARGOCD_PLATFORM_ARGOCD_APPS_REPO_URL
  ARGOCD_DQ_MADE_EASY_REPO_URL
  ARGOCD_METADATA_AS_A_SERVICE_REPO_URL

Optional environment variables:
	ARGOCD_REPO_USERNAME
	ARGOCD_REPO_PASSWORD
  ARGOCD_REPO_INSECURE_SKIP_SERVER_VERIFICATION=true|false

Example:
  ./scripts/register_argocd_repos.sh --env dev
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

selected_env=""

while [[ $# -gt 0 ]]; do
	case "$1" in
		--env)
			shift
			selected_env="${1:-}"
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
	shift
done

case "$selected_env" in
	dev|test|prod)
		;;
	*)
		echo "ERROR: --env must be one of: dev, test, prod" >&2
		usage >&2
		exit 2
		;;
esac

env_file="$repo_root/.env.${selected_env}.local"

if [[ ! -f "$env_file" ]]; then
	echo "ERROR: env file not found: $env_file" >&2
	exit 2
fi

set -a
# shellcheck disable=SC1090
source "$env_file"
set +a

require_env() {
	local name="$1"
	local value="${!name:-}"
	if [[ -z "$value" ]]; then
		echo "ERROR: missing required environment variable: $name" >&2
		exit 2
	fi

	printf '%s' "$value"
}

requires_git_auth() {
	case "$1" in
		file://*)
			return 1
			;;
		*)
			return 0
			;;
	esac
}

add_repo() {
	local repo_url="$1"
	local repo_label="$2"
	local username="${3:-}"
	local password="${4:-}"

	echo "==> Registering $repo_label"
	if requires_git_auth "$repo_url"; then
		if [[ -z "$username" || -z "$password" ]]; then
			echo "ERROR: $repo_label requires ARGOCD_REPO_USERNAME and ARGOCD_REPO_PASSWORD" >&2
			exit 2
		fi

		if [[ "${ARGOCD_REPO_INSECURE_SKIP_SERVER_VERIFICATION:-false}" == "true" ]]; then
			argocd repo add "$repo_url" \
				--username "$username" \
				--password "$password" \
				--upsert \
				--insecure-skip-server-verification
		else
			argocd repo add "$repo_url" \
				--username "$username" \
				--password "$password" \
				--upsert
		fi
	else
		argocd repo add "$repo_url" \
			--upsert
	fi
}

platform_repo_url="$(require_env ARGOCD_PLATFORM_ARGOCD_APPS_REPO_URL)"
dq_repo_url="$(require_env ARGOCD_DQ_MADE_EASY_REPO_URL)"
maas_repo_url="$(require_env ARGOCD_METADATA_AS_A_SERVICE_REPO_URL)"
repo_username="${ARGOCD_REPO_USERNAME:-}"
repo_password="${ARGOCD_REPO_PASSWORD:-}"

add_repo "$platform_repo_url" "platform-argocd-apps" "$repo_username" "$repo_password"
add_repo "$dq_repo_url" "dq-made-easy" "$repo_username" "$repo_password"
add_repo "$maas_repo_url" "metadata-as-a-service" "$repo_username" "$repo_password"