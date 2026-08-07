# Consumer-Specific Exceptions

**Status**: Draft  
**Date**: 2026-08-06

Documents unavoidable consumer-specific exceptions to the shared ArgoCD deployment contract.

Both consumers (`dq-made-easy` and `metadata-as-a-service`) follow the same deployment model, but their domain requirements create structural differences. These are documented here so operators know what to expect.

## Shared contract (both consumers)

| Element | Value |
|---|---|
| ArgoCD project | `tenant` |
| Namespace pattern | `<tenant>-dev`, `<tenant>-test` |
| Kustomize overlays | `k8s/overlays/<env>/` in consumer repo |
| Image promotion | Pinned tags via `environments/<env>/image-registry-config.yml` |
| Ingress | `ingressClassName: nginx`, TLS via platform secrets |
| Secrets | Consumer-defined in overlay, referenced by name |
| Labels/annotations | Platform-defined shared set |
| MaaS registration | Long-lived services register, ephemeral jobs do not |
| Telemetry | `job.runner.*` events for ephemeral workloads |

## Consumer-specific exceptions

### 1. Service count and structure

| Aspect | `dq-made-easy` | `metadata-as-a-service` |
|---|---|---|
| Total services | 3 (api, ui, engine) | 8 (api, coordinator, control-plane, central-repo, scenario-catalog, orchestrator, bff, web) |
| Zone services | `dq-api`, `dq-engine` (2 per target) | `maas-api`, `maas-coordinator` (2 per target) |
| Central services | None | 4 (control-plane, central-repo, scenario-catalog, orchestrator) |
| Frontend | `dq-ui` (single React UI) | `maas-bff` + `maas-web` (BFF proxy + React UI) |

**Reason**: MaaS has a multi-service central plane (telemetry, catalog, orchestration) while DQ has a single frontend.

### 2. Database topology

| Aspect | `dq-made-easy` | `metadata-as-a-service` |
|---|---|---|
| DB pattern | Single shared DB | Per-zone DBs (postgres per target) + central DBs |
| Storage | Shared | Per-zone MinIO + shared |
| DB count (prod) | 1 | 16 (zone) + 3 (central) = 19 |

**Reason**: MaaS requires data isolation per zone (no cross-zone state). DQ has a single database for all targets.

### 3. Ephemeral workload types

| Aspect | `dq-made-easy` | `metadata-as-a-service` |
|---|---|---|
| Ephemeral jobs | Spark jobs, profiling workers, Airflow DAGs | ETL/DQ jobs |
| Job spawner | `dq-engine` (Spark REST API) | `maas-orchestrator` or `maas-api` |
| Resource profile | High (Spark executors need JVM, large memory) | Low-medium (standard Python/workload) |

**Reason**: DQ runs Spark-based data processing with heavy resource requirements. MaaS runs lighter ETL tasks.

### 4. Frontend architecture

| Aspect | `dq-made-easy` | `metadata-as-a-service` |
|---|---|---|
| Frontend pattern | Direct UI → API | UI → BFF → Central services |
| Ingress count | 1 (dq-ui) | 2 (maas-bff, maas-web) |
| BFF | No | Yes (API proxy to central services) |

**Reason**: MaaS central services are internal — the BFF proxies API calls. DQ UI talks directly to the API.

### 5. Cross-zone coordination

| Aspect | `dq-made-easy` | `metadata-as-a-service` |
|---|---|---|
| Coordinators | None | `maas-coordinator` per target (conflict resolution) |
| Conflict resolution | N/A | Coordinators run conflict resolution between zones |

**Reason**: MaaS manages metadata across zones and needs conflict resolution. DQ processes data independently per target.

### 6. ArgoCD Application count

| Tenant | Dev apps | Test apps | Total |
|---|---|---|---|
| `dq-made-easy` | 3 | 3 | 6 |
| `metadata-as-a-service` | 8 | 8 | 16 |

**Reason**: MaaS has more services, so more ArgoCD Applications. This is a natural consequence, not a contract deviation.

### 7. Ingress hostnames

| Tenant | Hostname pattern | Count (dev) |
|---|---|---|
| `dq-made-easy` | `dq-<service>.dev.jac.dot` | 3 (api, ui, engine) |
| `metadata-as-a-service` | `maas-<service>.dev.jac.dot` | 8 (api, coordinator, control-plane, central-repo, scenario-catalog, orchestrator, bff, ui) |

**Reason**: Different service sets → different hostname counts. TLS secrets must be generated for each hostname.

## What is NOT an exception (both consumers share)

| Element | Reason |
|---|---|
| Namespace pattern | `<tenant>-<env>` for both |
| Kustomize overlay structure | `base/` + `overlays/<env>/` for both |
| Image promotion | Pinned tags, same registry for both |
| Secret ownership model | Consumer-defined, platform-managed TLS for both |
| MaaS registration rules | Long-lived services register, jobs do not |
| Label/annotation contract | Shared platform labels for both |
| Smoke check pattern | Namespace → pods → ArgoCD apps → health endpoints |
| Target mapping | 16 targets, zone + central + frontend split |

## Summary

Both consumers use the **same ArgoCD deployment contract** with the same overlay structure, image promotion, secret handling, and label/annotation conventions. The differences are:

1. **Service count**: 3 vs 8 (natural domain difference)
2. **Database topology**: single vs per-zone (data isolation requirements)
3. **Ephemeral workload types**: Spark vs ETL (processing model)
4. **Frontend pattern**: direct UI vs BFF + UI (API architecture)
5. **Cross-zone coordination**: none vs per-zone coordinators (conflict resolution)

These are **domain-driven differences**, not contract deviations. The ArgoCD contract, overlay structure, and deployment mechanism are identical.
