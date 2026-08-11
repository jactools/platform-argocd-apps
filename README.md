# Platform ArgoCD Applications

This repository contains all ArgoCD Application definitions for the platform-foundation Kind clusters.

## Plans

- [GitOps Repository Restructure Plan](./GITOPS_REPOSITORY_RESTRUCTURE_PLAN.md)
- [ArgoCD and kubectl Write Policy](./ARGOCD_KUBECTL_WRITE_POLICY.md)

## Structure

```
apps/
├── platform/          # Platform services (owned by platform-foundation)
│   ├── kong/
│   ├── keycloak/
│   └── observability/
└── tenants/           # Tenant workloads (owned by consumer repos)
    ├── dq/
    └── maas/

argocd/
├── bootstrap/      # One-time ArgoCD bootstrap root apps and kustomizations
└── config/
    └── projects/      # ArgoCD Project definitions

environments/
├── dev/               # Dev environment values
└── test/              # Test environment values
```

## Environments

| Environment | Cluster | Overlay | Sync |
|---|---|---|---|
| dev | Kind (local) | `apps/*/overlays/dev/` | Auto |
| test | Kind (Debian) | `apps/*/overlays/test/` | Auto |

## Adding a new platform service

1. Create `apps/platform/<service>/base/` with Kubernetes manifests
2. Create `apps/platform/<service>/overlays/dev/` with dev kustomization
3. Create `apps/platform/<service>/overlays/test/` with test kustomization
4. Create `apps/platform/<service>/argocd-app.yml`
5. Commit and push — ArgoCD will sync automatically

## Adding a new tenant

1. Create `apps/tenants/<tenant>/` with the tenant's ArgoCD Applications
2. Reference the tenant's git repository as the source
3. Commit and push — ArgoCD will sync automatically

## Deploying apps

Use the deploy helper to sync existing ArgoCD Applications after the manifests
are committed:

```bash
./scripts/argocd_sync.sh --scope platform --env dev
./scripts/argocd_sync.sh --scope platform --env prod
./scripts/argocd_sync.sh --app platform-shared-prod
./scripts/argocd_sync.sh --core --scope platform --env dev

venv/bin/python scripts/deploy_apps.py --scope platform --env dev
venv/bin/python scripts/deploy_apps.py --scope platform --env prod
venv/bin/python scripts/deploy_apps.py --app platform-shared-prod
venv/bin/python scripts/deploy_apps.py --core --scope platform --env dev
```

The script syncs ArgoCD Applications that already exist in the cluster. It does
not bootstrap the initial Application CRs.

## Bootstrapping ArgoCD

For a fresh cluster, install ArgoCD first and then apply the bootstrap root app
for the target environment:

```bash
./scripts/bootstrap_argocd.sh --env dev
./scripts/bootstrap_argocd.sh --env test
./scripts/bootstrap_argocd.sh --env prod
```

The bootstrap script installs ArgoCD from the upstream manifest, waits for the
control plane to become available, and then applies the repo-managed root
ApplicationSet that seeds the AppProjects and generates the repo-managed
Applications.
