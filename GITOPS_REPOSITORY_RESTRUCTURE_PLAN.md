# GitOps Repository Restructure Plan

**Status**: In Progress  
**Date**: 2026-08-09

## Objective and scope

This plan restructures `platform-argocd-apps` so it remains the canonical GitOps source for ArgoCD bootstrap resources and platform-managed Application CRs.

The target state should match a per-cluster ArgoCD model more closely while preserving the existing split between:

- platform-managed services
- per-environment overlays and source paths
- repository-local bootstrap and project definitions

This plan covers dev, test, and prod.

Tenant Application CRs are not currently modeled in this repository and remain out of scope unless a later cutover explicitly imports them here.

## Current issues

- Application manifests are organized close to services instead of under a single obvious ArgoCD tree
- root applications now exist for dev, test, and prod, but the repository still does not present a single obvious application layer
- AppProject ownership is centralized, but the canonical projects still live under `argocd/config/projects/` rather than the simplified path the plan originally assumed
- platform Application CRs still live in service-local `apps/platform/<service>/argocd/` directories, so the repo does not yet present a single obvious ArgoCD application layer
- the repository layout still does not make the remaining migration work equally obvious

## Target structure

The repository should evolve toward this shape:

```text
argocd/
  bootstrap/
    root-app-dev.yml
    root-app-test.yml
    root-app-prod.yml
  config/
    projects/
    platform-project.yml
    dq-project.yml
    maas-project.yml

apps/
  platform/
    <service>/
      argocd/
      base/
      overlays/

tenants/
  optional shared tenant metadata only
```

The `apps/platform/` tree remains a good place for the actual Kustomize sources of platform services. The main change is to keep the bootstrap path canonical under `argocd/bootstrap/`, keep projects centralized under `argocd/config/projects/`, and make the service-local `argocd/` Application locations explicit and consistent.

## Progress summary

| Workstream | Status | Tasks | Complete | Progress |
|---|---|---:|---:|---:|
| W1. Canonical ArgoCD tree | Partially complete | 5 | 2 | 40% |
| W2. Root applications and projects | Partially complete | 7 | 5 | 71% |
| W3. Platform Application normalization | Not started | 5 | 0 | 0% |
| W4. Validation and cutover | Not started | 6 | 0 | 0% |

## Workstream 1: Canonical ArgoCD tree

### Goal

Introduce one obvious home for all ArgoCD-specific resources.

### Tasks

- [x] Create and standardize `argocd/bootstrap/`
- [x] Keep AppProjects under `argocd/config/projects/`
- [ ] Document the dev/test/prod bootstrap handoff in this repository
- [ ] Keep bootstrap and project paths stable across environments
- [ ] Decide whether any future centralization of platform Application CRs is worth the churn

### Deliverable

ArgoCD bootstrap, AppProjects, and platform Application CRs are easy to find in the repository's actual layout.

## Workstream 2: Root applications and projects

### Goal

Make this repository the canonical home of the root applications and AppProjects used during bootstrap.

### Tasks

- [x] Add `root-app-dev.yml`
- [x] Add `root-app-test.yml`
- [x] Add `root-app-prod.yml`
- [x] Keep canonical `platform-project.yml`, `dq-project.yml`, and `maas-project.yml` under `argocd/config/projects/`
- [x] Add kustomization or aggregation manifests needed by the root apps
- [ ] Document the expected bootstrap path for dev, test, and prod
- [ ] Align the root apps with the current `file:///repos/...` versus GitHub source split

### Deliverable

Fresh cluster bootstrap can start from one environment-specific root application hosted in this repository.

## Workstream 3: Platform and tenant Application migration

### Goal

Normalize the platform Application CR locations that already live under `apps/platform/<service>/argocd/` without breaking their current source paths.

### Tasks

- [ ] Audit the platform Application CRs under `apps/platform/<service>/argocd/`
- [ ] Keep the `spec.source.path` values stable while the target repos migrate
- [ ] Remove or deprecate any duplicated platform Application CR locations
- [ ] Keep naming clear across the platform service groups
- [ ] Document any sync-wave or ordering requirements between applications

### Deliverable

Every platform Application CR has one canonical location under the existing service-local `apps/platform/<service>/argocd/` layout, while source manifests remain stable.

## Workstream 4: Validation and cutover

### Goal

Prove the new repository layout supports bootstrap and reconciliation cleanly.

### Tasks

- [ ] Validate that the dev root application reconciles the expected Application set
- [ ] Validate that the test root application reconciles the expected Application set
- [ ] Validate that the prod root application reconciles the expected Application set
- [ ] Validate that platform Applications remain healthy after relocation
- [ ] Update README and onboarding docs to reflect the new structure
- [ ] Capture an implementation summary after the cutover completes

### Deliverable

`platform-argocd-apps` becomes the clear, canonical GitOps source for both bootstrap and steady-state ArgoCD reconciliation.

## Acceptance criteria

- [x] Root applications for dev and test exist in this repository
- [x] Root applications for prod exist in this repository
- [x] AppProjects are canonically defined in this repository
- [ ] Platform Application CRs are consistently organized under the service-local `apps/platform/<service>/argocd/` layout
- [ ] Platform source paths remain understandable after migration
- [ ] The repository README reflects the new structure

## Next steps

1. Keep `argocd/bootstrap/` and `argocd/config/projects/` as the canonical bootstrap and project locations.
2. Add any missing documentation for the dev/test/prod bootstrap handoff.
3. Normalize the service-local platform Application CR layout under `apps/platform/<service>/argocd/`.
4. Validate bootstrap and reconciliation before removing any duplicated paths.