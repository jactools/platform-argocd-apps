# ArgoCD Application Rename Cutover

**Date:** 2026-08-12  
**Status:** Ready

## Objective

Cut over existing clusters from the old mixed ArgoCD Application naming scheme to the new consistent env-suffixed scheme:

- old mixed pattern: `platform-kong`, `platform-airflow`, `platform-kyverno`, ...
- new pattern: `platform-kong-dev`, `platform-airflow-dev`, `platform-kyverno-dev`, ...

This applies to env-specific platform Applications. `shared` and `ai-stor` were already env-suffixed and do not need renaming.

## Why this is needed

The old naming scheme reused the same ArgoCD Application name across `dev` and `test` manifests for most platform services. That made the repository inconsistent and prevented one clear naming rule.

The new rule is:

- `platform-<service>-dev`
- `platform-<service>-test`
- `platform-<service>-prod` when an environment-specific Application exists for prod

## Rename map

### Dev

| Old name | New name |
|---|---|
| `platform-airflow` | `platform-airflow-dev` |
| `platform-kafka` | `platform-kafka-dev` |
| `platform-keycloak` | `platform-keycloak-dev` |
| `platform-kong` | `platform-kong-dev` |
| `platform-kyverno` | `platform-kyverno-dev` |
| `platform-kyverno-policies` | `platform-kyverno-policies-dev` |
| `platform-observability` | `platform-observability-dev` |
| `platform-redis` | `platform-redis-dev` |
| `platform-trino` | `platform-trino-dev` |

### Test

| Old name | New name |
|---|---|
| `platform-airflow` | `platform-airflow-test` |
| `platform-kafka` | `platform-kafka-test` |
| `platform-keycloak` | `platform-keycloak-test` |
| `platform-kong` | `platform-kong-test` |
| `platform-kyverno` | `platform-kyverno-test` |
| `platform-kyverno-policies` | `platform-kyverno-policies-test` |
| `platform-observability` | `platform-observability-test` |
| `platform-redis` | `platform-redis-test` |
| `platform-trino` | `platform-trino-test` |

## Expected behavior from ApplicationSet

The bootstrap ApplicationSet reads the child Application name from each `apps/**/argocd/*-<env>.yml` file:

- `argocd/bootstrap/dev/platform-bootstrap-dev-applicationset.yml`
- `argocd/bootstrap/test/platform-bootstrap-test-applicationset.yml`

Because the desired child Application names changed in Git, the expected steady-state behavior is:

1. the ApplicationSet creates the new suffixed child Applications
2. the old unsuffixed child Applications stop being desired
3. ArgoCD removes the old unsuffixed child Applications during reconciliation

That is the happy path.

## Safe cutover sequence

### 1. Sync the bootstrap/root application first

Make sure the environment root ApplicationSet is reconciled before syncing individual platform apps.

For dev, that means the `platform-bootstrap-dev-appset` must see the renamed manifest files.

### 2. Verify the new Application names appear

Confirm the new suffixed Applications exist in ArgoCD before relying on them operationally.

Examples for dev:

- `platform-kong-dev`
- `platform-keycloak-dev`
- `platform-observability-dev`
- `platform-airflow-dev`

### 3. Verify the new Applications become healthy

Wait for the new suffixed Applications to reach `Synced` and `Healthy`.

Do not delete the old names first if the new ones have not been created yet.

### 4. Check whether the old Applications were pruned automatically

If the ApplicationSet reconciliation worked as expected, the old unsuffixed names should disappear on their own.

Examples of old names that should go away in dev and test:

- `platform-kong`
- `platform-keycloak`
- `platform-observability`
- `platform-airflow`

### 5. If old Applications remain, remove only the old Application CRs

If the old unsuffixed child Applications remain after the new ones are healthy, remove the old Application CRs from ArgoCD.

This is a cleanup of obsolete generated Application objects, not a new deployment path.

Do not remove the new suffixed Applications.

### 6. Use repo-driven sync after the rename

After the cutover, prefer repo-driven selection rather than hardcoded old app names:

```bash
./scripts/argocd_sync.sh --scope platform --env dev
./scripts/argocd_sync.sh --scope platform --env test
```

The repo helpers now select the suffixed names from the current manifests.

### 7. Run the rename verification helper

Use the helper script to verify that the new suffixed names exist and the old
unsuffixed names are gone:

```bash
./scripts/python_arm64.sh scripts/validate_argocd_application_rename.py --env dev

./scripts/python_arm64.sh scripts/validate_argocd_application_rename.py --env test
```

The helper reads `KUBECONFIG` from the matching `.env.<env>.local` file by default.
Use `--kubeconfig` only when you need to override that path.

## Fallback path if automatic pruning does not happen

If the ApplicationSet creates the new names but leaves the old names behind:

1. confirm the new suffixed Application is `Healthy`
2. confirm it targets the same destination namespace and source path as the old one
3. remove the old unsuffixed Application object from ArgoCD
4. recheck that only the suffixed Application remains

This avoids a gap in management while still cleaning up the stale name.

## Operational notes

- `platform-shared-dev`, `platform-shared-test`, and `platform-shared-prod` were already env-suffixed and are unchanged.
- `platform-ai-stor-dev`, `platform-ai-stor-test`, and `platform-ai-stor-prod` were already env-suffixed and are unchanged.
- `prod` currently only carries the shared Application in the bootstrap ApplicationSet, so this rename cutover is primarily a `dev` and `test` concern.

## Acceptance check

The cutover is complete when:

- all env-specific platform Applications use the `platform-<service>-<env>` pattern
- old unsuffixed Application CRs no longer exist in ArgoCD
- repo sync helpers operate only on the new suffixed names
- platform Applications remain `Synced` and `Healthy` after the rename