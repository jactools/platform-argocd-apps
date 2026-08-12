# Registry Runtime Handoff Plan

**Date:** 2026-08-12  
**Status:** Complete

## Objective

Move external runtime ownership for `docker-registry` and `pypi-server` from this repository into `platform-foundation`, while keeping `platform-argocd-apps` as the GitOps and consumption-contract repository.

## Decision

`platform-argocd-apps` should not be the long-term owner of:

- Docker Compose for external registries
- host-side TLS and auth material
- runtime start and stop commands for external registries
- smoke checks for external registry and package publishing

Those concerns belong in `platform-foundation`, because that repository already owns host-side environment files, local runtime startup scripts, certificate generation, and exported credentials.

`platform-argocd-apps` should remain the owner of:

- ArgoCD bootstrap and sync flows for cluster-managed applications
- Application manifests and Kustomize overlays
- cluster-facing endpoint contracts
- validation and documentation for how workloads consume the registry and package services

## Current overlap

This repository previously contained transitional runtime ownership in these paths:

- `runtime/registries/docker-compose.yml`
- `runtime/registries/nginx/`
- `runtime/registries/registries.env.example`
- `scripts/registry_runtime.sh`
- `scripts/start_platform_stack.sh`

These files were useful to prove the externalized design and startup order, but they crossed the repo boundary by owning host-side runtime behavior.

The runtime assets have now been moved into `platform-foundation` and removed from this repository.

## Target ownership split

### `platform-foundation`

Move these concerns there:

1. external registry Docker Compose files
2. TLS gateway configs and certificate expectations
3. runtime env contract for dev, test, and prod
4. start and stop scripts for the registries
5. startup orchestration that waits for registry readiness before cluster bootstrap
6. smoke checks for `docker login`/`push`/`pull` and package upload/install
7. generated credentials for registry and PyPI auth

### `platform-argocd-apps`

Keep these concerns here:

1. image and package endpoint references used by workloads
2. ArgoCD Application cleanup for the retired in-cluster registry apps
3. validator and policy updates tied to external endpoints
4. docs that describe the platform contract from the cluster's point of view

## Migration steps

### Phase 1: Duplicate runtime in `platform-foundation`

1. Copy the registry runtime assets into `platform-foundation`.
2. Rename commands there to match local conventions if needed.
3. Point the `platform-foundation` startup path at the external registries first.
4. Keep behavior equivalent to the current transitional files in this repo.

### Phase 2: Switch operational entrypoints

1. Make `platform-foundation` the documented place to run the registries.
2. Make `platform-foundation` the documented place to run the startup orchestration.
3. Keep the local copies here only as a short-lived compatibility bridge.

### Phase 3: Demote local ownership in this repo

1. Marked the local runtime paths as transitional.
2. Marked the local registry startup helper as transitional.
3. Marked the local platform startup helper as transitional.

### Phase 4: Remove local runtime implementation

1. Removed the local runtime directory from this repo.
2. Removed the local registry runtime helper from this repo.
3. Removed the local platform startup helper from this repo.
4. Kept only the contract docs and cluster GitOps content here.

## Acceptance criteria

- operators start and manage external registries from `platform-foundation`
- this repo no longer owns Docker Compose or host-side registry startup logic
- this repo still documents the registry and package endpoints that cluster workloads consume
- the externalization plan and repo README make the ownership split explicit

## Result

The runtime implementation no longer lives in this repository. `platform-argocd-apps` now keeps only the cluster-facing contract and GitOps responsibilities.