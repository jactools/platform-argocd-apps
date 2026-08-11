#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

should_refresh_argocd_session() {
	local arg
	for arg in "$@"; do
		case "$arg" in
			--core|--list|-h|--help)
				return 1
				;;
		esac
	done

	return 0
}

refresh_argocd_session() {
	local credentials_file="$repo_root/tmp/.credentials"

	if [[ ! -f "$credentials_file" ]]; then
		return 0
	fi

	if ! kubectl get configmap argocd-cm -n argocd >/dev/null 2>&1; then
		return 0
	fi

	# shellcheck disable=SC1090
	source "$credentials_file"

	if [[ -z "${argocd_url:-}" || -z "${argocd_password:-}" ]]; then
		echo "ERROR: tmp/.credentials must define argocd_url and argocd_password" >&2
		exit 2
	fi

	local argocd_server="$argocd_url"
	argocd_server="${argocd_server#https://}"
	argocd_server="${argocd_server#http://}"
	argocd_server="${argocd_server%/}"

	argocd login "$argocd_server" \
		--username "${argocd_username:-admin}" \
		--password "$argocd_password" \
		--grpc-web \
		--insecure
}

if should_refresh_argocd_session "$@"; then
	refresh_argocd_session
fi

exec python3 "$repo_root/scripts/deploy_apps.py" "$@"