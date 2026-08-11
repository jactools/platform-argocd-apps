#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

selected_env="dev"

resolve_selected_env() {
	local arg
	local expect_env_value=false

	for arg in "$@"; do
		if [[ "$expect_env_value" == true ]]; then
			selected_env="$arg"
			return 0
		fi

		case "$arg" in
			--env)
				expect_env_value=true
				;;
			--env=*)
				selected_env="${arg#--env=}"
				return 0
				;;
		esac
	done

	return 0
}

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

resolve_credentials_file() {
	case "$selected_env" in
		dev|all|"")
			if [[ -f "$repo_root/tmp/.credentials.dev" ]]; then
				echo "$repo_root/tmp/.credentials.dev"
			else
				echo "$repo_root/tmp/.credentials"
			fi
			;;
		test)
			echo "$repo_root/tmp/.credentials.test"
			;;
		prod)
			echo "$repo_root/tmp/.credentials.prod"
			;;
		*)
			echo "ERROR: unsupported --env value for auth refresh: $selected_env" >&2
			exit 2
			;;
	esac
}

refresh_argocd_session() {
	local credentials_file
	credentials_file="$(resolve_credentials_file)"

	if [[ ! -f "$credentials_file" ]]; then
		if [[ "$selected_env" == "test" || "$selected_env" == "prod" ]]; then
			echo "ERROR: missing ArgoCD credentials file for env '$selected_env': $credentials_file" >&2
			echo "Create the file with argocd_url and argocd_password, or rerun with the matching env." >&2
			exit 2
		fi

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

resolve_selected_env "$@"

if should_refresh_argocd_session "$@"; then
	refresh_argocd_session
fi

exec python3 "$repo_root/scripts/deploy_apps.py" "$@"