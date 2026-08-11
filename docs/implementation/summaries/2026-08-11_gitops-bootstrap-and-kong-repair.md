# GitOps Bootstrap and Kong Repair

**Date:** 2026-08-11  
**Status:** Complete

## Objective

Restore the dev GitOps flow so repo registration is env-driven, dev continues to use `file:///repos`, test and prod use GitHub URLs, and Kong dev starts with a mirrored PostgreSQL image plus working shared secrets.

## Results

| Check | Before | After |
| --- | --- | --- |
| ArgoCD repo registration | Git URL and token were tracked in YAML | Repo inputs are sourced from environment files |
| Dev bootstrap source | Mixed local and remote repo URLs | Dev uses `file:///repos` consistently |
| Test/prod bootstrap source | Local repo URLs leaked into higher environments | Test and prod use GitHub repo URLs |
| Kong database image | Image pull failed from the host-local registry path inside Kind | `postgres:17-bookworm` is mirrored and preloaded into Kind for dev |
| Shared secret bootstrap | Secret generation was brittle and order-dependent | Namespace-aware secret lookup and stable sync ordering now work |
| App health | Kong was stuck in crash loops and image-pull retries | `platform-kong` and `platform-shared-dev` sync cleanly in dev |

## Files Updated

- `scripts/register_argocd_repos.sh`
- `.env.dev.local`
- `.env.test.local`
- `.env.prod.local`
- `argocd/bootstrap/dev/platform-bootstrap-dev-applicationset.yml`
- `argocd/bootstrap/test/platform-bootstrap-test-applicationset.yml`
- `argocd/bootstrap/prod/platform-bootstrap-prod-applicationset.yml`
- `argocd/bootstrap/root-app-test.yml`
- `argocd/bootstrap/root-app-prod.yml`
- `apps/platform/kong/base/kong-db.yml`
- `apps/platform/kong/base/kong-migrations.yml`
- `apps/platform/shared/base/configmaps/secret-init-script.yml`
- `apps/platform/shared/base/jobs/secret-init-job.yml`

## Remaining Work

None for this slice.

## Next Steps

If registry endpoints or repo hosts change again, update the environment files first, then rerun repo registration and the upstream image publish flow before syncing Kong.
