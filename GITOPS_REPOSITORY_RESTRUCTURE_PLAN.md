# GitOps Repository Restructure Plan

**Status**: Draft  
**Date**: 2026-08-09

## Objective and scope

This plan restructures `platform-argocd-apps` so it becomes the single canonical GitOps source for ArgoCD Applications, AppProjects, and per-environment root applications.

The target state should match a per-cluster ArgoCD model more closely while preserving the existing split between:

- platform-managed services
- tenant-managed Applications
- per-environment overlays and source paths

This plan covers dev and test only.

## Current issues

- Application manifests are organized close to services and tenants instead of under a single environment-first ArgoCD tree
- root applications per environment are not yet the canonical bootstrap path in this repository
- AppProject ownership is not yet clearly centralized here
- the repository layout does not make cluster bootstrap and ongoing reconciliation equally obvious

## Target structure

The repository should evolve toward this shape:

```text
argocd/
  bootstrap/
    root-app-dev.yml
    root-app-test.yml
  projects/
    platform-project.yml
    tenant-project.yml
  applications/
    dev/
      platform/
      tenants/
        dq/
        maas/
    test/
      platform/
      tenants/
        dq/
        maas/

apps/
  platform/
    <service>/
      base/
      overlays/

tenants/
  optional shared tenant metadata only
```

The `apps/platform/` tree remains a good place for the actual Kustomize sources of platform services. The main change is that ArgoCD Application CRs should become environment-first and canonical under `argocd/applications/`.

## Progress summary

| Workstream | Status | Tasks | Complete | Progress |
|---|---|---:|---:|---:|
| W1. Canonical ArgoCD tree | Not started | 6 | 0 | 0% |
| W2. Root applications and projects | Not started | 6 | 0 | 0% |
| W3. Platform and tenant Application migration | Not started | 7 | 0 | 0% |
| W4. Validation and cutover | Not started | 6 | 0 | 0% |

## Workstream 1: Canonical ArgoCD tree

### Goal

Introduce one obvious home for all ArgoCD-specific resources.

### Tasks

- [ ] Create `argocd/bootstrap/`
- [ ] Create `argocd/projects/`
- [ ] Create `argocd/applications/dev/platform/`
- [ ] Create `argocd/applications/dev/tenants/`
- [ ] Create `argocd/applications/test/platform/`
- [ ] Create `argocd/applications/test/tenants/`

### Deliverable

ArgoCD bootstrap, AppProjects, and Application CRs live in one environment-first tree.

## Workstream 2: Root applications and projects

### Goal

Make this repository the canonical home of the root applications and AppProjects used during bootstrap.

### Tasks

- [ ] Add `root-app-dev.yml`
- [ ] Add `root-app-test.yml`
- [ ] Move or recreate canonical `platform-project.yml` under `argocd/projects/`
- [ ] Move or recreate canonical `tenant-project.yml` under `argocd/projects/`
- [ ] Add kustomization or aggregation manifests needed by the root apps
- [ ] Document the expected bootstrap path for dev and test

### Deliverable

Fresh cluster bootstrap can start from one environment-specific root application hosted in this repository.

## Workstream 3: Platform and tenant Application migration

### Goal

Relocate existing Application CRs into the canonical ArgoCD tree without losing the current source paths.

### Tasks

- [ ] Move platform Application CRs from service-local `argocd/` folders into `argocd/applications/<env>/platform/`
- [ ] Move DQ tenant Application CRs into `argocd/applications/<env>/tenants/dq/`
- [ ] Move MaaS tenant Application CRs into `argocd/applications/<env>/tenants/maas/`
- [ ] Keep the `spec.source.path` values stable while the target repos migrate
- [ ] Remove or deprecate the old duplicated Application CR locations
- [ ] Keep naming clear between platform services and tenant services
- [ ] Document any sync-wave or ordering requirements between applications

### Deliverable

Every Application CR has one canonical location under the ArgoCD tree, while platform and tenant source manifests remain stable.

## Workstream 4: Validation and cutover

### Goal

Prove the new repository layout supports bootstrap and reconciliation cleanly.

### Tasks

- [ ] Validate that the dev root application reconciles the expected Application set
- [ ] Validate that the test root application reconciles the expected Application set
- [ ] Validate that platform Applications remain healthy after relocation
- [ ] Validate that tenant Applications still point to the expected consumer repo overlays
- [ ] Update README and onboarding docs to reflect the new structure
- [ ] Capture an implementation summary after the cutover completes

### Deliverable

`platform-argocd-apps` becomes the clear, canonical GitOps source for both bootstrap and steady-state ArgoCD reconciliation.

## Acceptance criteria

- [ ] Root applications for dev and test exist in this repository
- [ ] AppProjects are canonically defined in this repository
- [ ] Application CRs are grouped by environment and scope
- [ ] Platform and tenant source paths remain understandable after migration
- [ ] The repository README reflects the new structure

## Next steps

1. Create the canonical `argocd/bootstrap`, `argocd/projects`, and `argocd/applications` tree.
2. Add root applications for dev and test.
3. Relocate platform and tenant Application CRs into the new tree.
4. Validate bootstrap and reconciliation before removing old paths.