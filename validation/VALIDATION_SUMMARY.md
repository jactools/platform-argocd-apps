# W4 Consumer Onboarding — Validation Summary

**Date**: 2026-08-06  
**Status**: Contract validated (pre-deployment)

## What was validated

Both `dq-made-easy` and `metadata-as-a-service` can be deployed from the same ArgoCD contract. The following artifacts were validated:

### ArgoCD Applications (21 files — all pass)

| Tenant | Dev apps | Test apps | Status |
|---|---|---|---|
| `dq-made-easy` | `tenant-dq-dev` | `tenant-dq-test` | ✓ All parse correctly |
| `metadata-as-a-service` | `tenant-maas-api`, `tenant-maas-coordinator`, `tenant-maas-control-plane`, `tenant-maas-central-repo`, `tenant-maas-scenario-catalog`, `tenant-maas-orchestrator`, `tenant-maas-bff`, `tenant-maas-web` | Same 8 with `-test` suffix | ✓ All parse correctly |

### Kustomize overlays (4 directories — all pass)

| Overlay | Output |
|---|---|
| `apps/tenants/dq/overlays/dev` | Namespace `dq-dev` with `environment: dev`, `tenant: dq` labels |
| `apps/tenants/dq/overlays/test` | Namespace `dq-test` with `environment: test`, `tenant: dq` labels |
| `apps/tenants/maas/overlays/dev` | Namespace `maas-dev` with `environment: dev`, `tenant: maas` labels |
| `apps/tenants/maas/overlays/test` | Namespace `maas-test` with `environment: test`, `tenant: maas` labels |

### Image registry config (2 files — all pass)

| File | Entries |
|---|---|
| `environments/dev/image-registry-config.yml` | 3 platform + 4 dq + 8 maas + 7 base images |
| `environments/test/image-registry-config.yml` | Same structure, `docker-registry.jacloud.nl:5000` |

### Shared ArgoCD contract

| Contract element | Value |
|---|---|
| Project | `tenant` (shared by both consumers) |
| Destination server | `https://kubernetes.default.svc` |
| Sync policy | Auto-sync, prune, self-heal |
| Namespace creation | `CreateNamespace=true` |
| Source repo | `{{DQ_MADE_EASY_REPO_URL}}` / `{{MAAS_REPO_URL}}` |
| Source path | `k8s/overlays/<env>` |

### Smoke check scripts (2 scripts — both valid)

| Script | Checks |
|---|---|
| `scripts/smoke/smoke_dq.sh` | Namespace, pods, ArgoCD apps, health endpoints |
| `scripts/smoke/smoke_maas.sh` | Namespace, pods, ArgoCD apps, health endpoints |

## What blocks full deployment

Both consumers share the same ArgoCD contract but cannot be fully deployed yet because:

1. **Consumer K8s manifests missing**: The `dq-made-easy` and `metadata-as-a-service` repos don't yet have the full `k8s/overlays/<env>/` deployment roots wired up consistently. The ArgoCD Applications reference `{{REPO_URL}}/k8s/overlays/<env>` which must exist for deployment.
2. **Consumer images not published**: Tenant images (e.g. `dq-api:0.1.0`) are not yet published to the shared registry.
3. **Consumer secrets not defined**: Tenant-specific secrets (DB credentials, SSO config) are not yet created in the overlays.

These are **consumer-owned items** that block actual deployment but do not block the contract definition.

## Validation command

```bash
cd platform-argocd-apps

# Validate all ArgoCD Applications
find apps/tenants -name "*.yml" -path "*/argocd/*" -exec kubectl apply --dry-run=client -f {} \;

# Validate all Kustomize overlays
kubectl kustomize apps/tenants/dq/overlays/dev
kubectl kustomize apps/tenants/dq/overlays/test
kubectl kustomize apps/tenants/maas/overlays/dev
kubectl kustomize apps/tenants/maas/overlays/test

# Validate smoke scripts (syntax only)
bash -n scripts/smoke/smoke_dq.sh
bash -n scripts/smoke/smoke_maas.sh
```

## Next steps

1. Consumer repos create `k8s/base/` and `k8s/overlays/` with Kubernetes manifests
2. Consumer repos publish images to shared registry
3. ArgoCD Applications are applied to the cluster
4. Smoke checks run against the deployed services
