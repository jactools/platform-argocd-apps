# Externalize Registry Services Plan

**Date:** 2026-08-12  
**Status:** Proposed

## Objective

Move `docker-registry` and `pypi-server` out of the Kubernetes clusters and run them as externally managed Docker containers. After the cutover, the clusters should consume both services as stable external dependencies rather than hosting them as ArgoCD-managed workloads.

Ownership note: the external runtime now lives in `platform-foundation`. This repository retains only the cluster-facing contract and GitOps cleanup work.

## Scope

In scope:

- retire the in-cluster ArgoCD Applications for `docker-registry` and `pypi-server`
- preserve or replace the current registry and package endpoints with externally reachable equivalents
- remove cluster bootstrap dependencies that exist only to stand up these two services
- update GitOps contracts, validation rules, and operator documentation

Out of scope:

- changing tenant image names or tag semantics
- redesigning the broader ArgoCD bootstrap layout
- changing unrelated platform services

## Current state

The current repository still models both services as in-cluster Applications:

- `apps/platform/docker-registry/argocd/docker-registry-dev.yml`
- `apps/platform/pypi-server/argocd/pypi-dev.yml`
- `apps/platform/docker-registry/base/` contains the Deployment, Service, Ingress, and TLS-init Job
- `apps/platform/pypi-server/base/` contains the Deployment, Service, Ingress, and auth-init Job

The cleanest migration seam is already present: consumers mostly reference external hostnames rather than Kubernetes Service DNS.

- Docker images already use `docker-registry.dev.jac.dot:5000` and `docker-registry.jacloud.nl:5000` via `environments/*/image-registry-config.yml`
- PyPI ingress already exposes environment-specific public package hosts, and the target naming now converges on `packages.<env>.jac.dot`

The remaining cluster coupling is operational rather than contractual:

- ArgoCD still deploys both apps into `platform-registry`
- `argocd/config/projects/platform-project.yml` still allows the `platform-registry` namespace
- `scripts/validate_manifests.py` still treats the registry apps and namespace as expected platform targets
- `apps/platform/kyverno/base/policies/block-dockerhub-images.yml` still describes the registry as cluster-local
- bootstrap and shared-secret flows still account for `platform-registry`

## Target state

After migration:

- `docker-registry` runs as an external Docker container with persistent storage, TLS, and authentication
- `pypi-server` runs as an external Docker container with persistent package storage, TLS, and authentication
- clusters reach both services through stable DNS names that resolve from cluster nodes and developer hosts
- this repository keeps only the endpoint contracts and consumer references, not the runtime manifests for these two services
- ArgoCD no longer needs to order, heal, or bootstrap these services inside any cluster

### DNS and protocol convention

Use HTTPS for both services in every environment.

- Dev:
   - `https://packages.dev.jac.dot`
   - `https://docker-registry.dev.jac.dot:5000`
- Test:
   - `https://packages.test.jac.dot`
   - `https://docker-registry.test.jac.dot:5000`
- Prod:
   - `https://packages.prod.jac.dot`
   - `https://docker-registry.prod.jac.dot:5000`

If the final test or prod domains differ from this pattern, keep the same structure in the startup script and environment contracts: one HTTPS package host and one HTTPS registry host per environment.

## Design principles

1. Preserve the public hostnames and naming pattern. Reusing `docker-registry.<env>.jac.dot` and `packages.<env>.jac.dot` minimizes manifest churn.
2. Move runtime ownership out of GitOps. This repo should describe how workloads consume the services, not how the services are hosted.
3. Keep image and package contracts stable. Tenants should not need to redesign their overlays just because the hosting model changes.
4. Start registries before cluster reconciliation. The platform bootstrap path must treat registry readiness as a hard prerequisite.
5. Remove cluster-only setup logic after cutover. Init Jobs, in-cluster TLS generation, and namespace exceptions should disappear once external services are authoritative.

## Workstream 1: External runtime definition

### Goal

Define the new operational home for both services before changing GitOps.

### Tasks

1. Choose the external host for each environment.
   - Dev can run on the Docker host or a dedicated utility VM.
   - Test should run on the environment host or another always-on node reachable from the test cluster.
2. Package the services as externally managed Docker workloads.
   - Prefer `docker compose` with named volumes and a small operational wrapper.
   - Ensure automatic restart, log capture, and backup procedures.
3. Define persistent data locations.
   - Registry storage for image layers and manifests.
   - PyPI storage for package files and indexes.
4. Define authentication and TLS.
   - Registry: HTTPS plus authenticated push and pull as needed.
   - PyPI: HTTPS plus authenticated upload, controlled read access, and a clear pip configuration story.
5. Add health checks and a small recovery runbook.
6. Define machine-checkable readiness probes for the startup script.
   - Registry: `GET /v2/` over HTTPS should return a valid registry response, typically `200` or `401`.
   - PyPI: `GET /simple/` or the configured landing page over HTTPS should return `200`.

### Deliverable

Both services can be started, restarted, backed up, and monitored without Kubernetes.

Ownership outcome:

- runtime implementation should live in `platform-foundation`
- this repository should retain only the cluster-facing contract

## Workstream 2: Networking and endpoint cutover

### Goal

Make the external services reachable through stable names before retiring the in-cluster copies.

### Tasks

1. Preserve existing hostnames where feasible.
   - Registry: keep `docker-registry.<env>.jac.dot:5000`.
   - PyPI: keep `packages.<env>.jac.dot`.
2. Ensure cluster nodes resolve those names to the external host, not to `127.0.0.1` or an ingress IP that depends on the cluster.
   - This directly addresses the failure mode documented in `docs/implementation/lessons-learned/2026-08-11_gitops-bootstrap-and-kong-repair.md`.
3. Validate TLS trust from three paths.
   - developer host
   - cluster nodes or container runtime
   - CI or automation hosts that publish images or packages
4. Freeze ingress changes only after the external endpoints are proven reachable.

### Deliverable

Consumers can use the same endpoint names before and after the hosting cutover.

## Workstream 2A: Startup orchestration

### Goal

Guarantee that external registries are started and healthy before ArgoCD bootstrap or platform app sync begins.

### Tasks

1. Use the `platform-foundation` startup orchestration entrypoint for registry-first startup.
2. Make the script environment-aware with `--env dev|test|prod`.
3. Start the external registry containers first.
   - Prefer `docker compose up -d` from an external runtime directory.
4. Wait for HTTPS readiness before touching the cluster.
   - Registry check: `https://docker-registry.<env>.jac.dot:5000/v2/`
   - PyPI check: `https://packages.<env>.jac.dot/simple/`
5. Only after both checks pass, continue with cluster startup.
   - Run `scripts/bootstrap_argocd.sh --env <env>` when ArgoCD is not installed yet.
   - Run `scripts/argocd_sync.sh --scope platform --env <env>` for steady-state reconciliation.
6. Fail fast with a clear message if either external service is unavailable.
7. Keep the orchestration idempotent so reruns do not break existing healthy services.

### Deliverable

One operator command can start the external registries, wait for readiness, then continue with cluster bootstrap and application sync.

Ownership note:

That startup behavior is now owned by `platform-foundation`, not this repository.

## Workstream 3: GitOps repository cleanup

### Goal

Remove in-cluster ownership from this repository while preserving consumption contracts.

### Tasks

1. Remove the registry Applications from the platform aggregation.
   - Drop `docker-registry/argocd/*` and `pypi-server/argocd/*` references from `apps/platform/kustomization.yml`.
2. Retire the in-cluster manifests.
   - Remove or archive `apps/platform/docker-registry/` and `apps/platform/pypi-server/` once the external runtime is accepted.
   - If temporary retention is needed, mark them deprecated and stop referencing them from ArgoCD.
3. Remove validation assumptions tied to the old apps.
   - Update `scripts/validate_manifests.py` so the retired app names and destinations are no longer expected.
4. Reassess the `platform-registry` namespace.
   - If nothing else uses it, remove it from `argocd/config/projects/platform-project.yml` and the bootstrap project manifests.
   - If another shared component still needs it, narrow ownership to that remaining use only.
5. Update policy and contract docs.
   - `images/IMAGE_REFERENCE_CONTRACT.md`
   - `apps/platform/kyverno/base/policies/block-dockerhub-images.yml`
   - tenant READMEs that explain where images are pulled from
6. Remove cluster bootstrap logic that exists only for these services.
   - TLS secret generation for the registry
   - PyPI auth bootstrap job
   - any shared-secret setup that only served `platform-registry`

### Deliverable

This repo describes external dependency contracts instead of deploying the registry runtimes.

## Workstream 4: Consumer and pipeline alignment

### Goal

Ensure build, publish, and install flows still work after the hosting model changes.

### Tasks

1. Keep `environments/dev/image-registry-config.yml` and `environments/test/image-registry-config.yml` unchanged if hostnames are preserved.
2. Update those files only if endpoint names or ports must change.
3. Update any image publish automation to push to the external registry host.
4. Replace cluster-local PyPI URLs with external package endpoints in developer and automation credentials.
   - The current local credential example still points at `pypi-server.platform-registry.svc.cluster.local`.
   - Switch those credentials to `https://packages.<env>.jac.dot`.
5. Verify that container runtimes can pull images without `kind load docker-image` as the primary path.
   - Keep `kind load docker-image` only as an explicit fallback for offline debugging.
6. Verify that pip and build tooling can install from the external package index.

### Deliverable

Image publishing, image pulling, and Python package installation no longer depend on cluster-internal services.

## Workstream 5: Cutover and decommission

### Goal

Move production traffic to the external services and remove the old cluster workloads cleanly.

### Tasks

1. Stand up the external containers and verify health.
2. Copy existing registry and package data into the new persistent stores.
3. Run parallel verification.
   - push and pull a test image
   - upload and install a test Python package
   - run the startup orchestration script end to end from a clean environment
4. Switch DNS or reverse-proxy routing to the external runtime.
5. Remove the ArgoCD Application references and sync the platform app set.
6. Observe cluster pulls and package installs through one full deployment cycle.
7. Delete the old in-cluster namespace and secrets only after successful steady-state validation.

### Deliverable

The external services are authoritative, and the cluster no longer hosts duplicate copies.

## Validation checklist

1. `docker login`, `docker push`, and `docker pull` work against the final registry endpoint from a developer host.
2. A cluster workload can pull an updated image from the final registry endpoint without manual preloading.
3. `pip install` from the final PyPI endpoint works from developer automation and from any in-cluster build path that still needs it.
4. The startup orchestration script waits for both HTTPS endpoints and only then starts cluster reconciliation.
5. ArgoCD no longer shows `platform-docker-registry` or `platform-pypi-server` as managed Applications.
6. Repo validation passes after the Application and namespace cleanup.
7. Documentation reflects the new source of truth for registry operations.

## Rollback plan

If the external services fail validation after cutover:

1. restore DNS or reverse-proxy routing to the in-cluster ingress
2. re-enable the registry Applications in `apps/platform/kustomization.yml`
3. resync ArgoCD
4. keep external data intact for another migration attempt

Rollback should remain available until one full publish-and-consume cycle succeeds in both dev and test.

## Acceptance criteria

- no ArgoCD Application in this repo deploys `docker-registry` or `pypi-server`
- cluster consumers use stable HTTPS external endpoints for image and package access
- startup orchestration starts the registries first and blocks cluster app startup until both are healthy
- no cluster bootstrap dependency remains that exists only for the two registry services
- repo validation and platform documentation match the externalized model
- dev and test both complete one successful image publish, image pull, package upload, and package install cycle

## Recommended execution order

1. Finalize hostname and runtime ownership decisions.
2. Implement the startup orchestration path that starts registries first.
3. Stand up the external containers and validate HTTPS reachability.
4. Switch consumers to the proven external endpoints.
5. Remove ArgoCD ownership and cluster bootstrap logic.
6. Delete any now-unused namespace and validation exceptions.