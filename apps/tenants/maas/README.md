# Tenant: maas (metadata-as-a-service)

Tenant overlay and service mapping for the `metadata-as-a-service` consumer.

## Namespace convention

| Environment | Namespace | Owner |
|---|---|---|
| dev | `maas-dev` | metadata-as-a-service |
| test | `maas-test` | metadata-as-a-service |

## Service mapping

Each row maps a docker-compose service to its Kubernetes representation. The `workload-kind` column determines MaaS registration behaviour: `service` instances register with MaaS on startup, `job` instances do not.

### Zone services (one per target)

| Service | workload-kind | MaaS register | Description | Image (Dockerfile) |
|---|---|---|---|---|
| `maas-api` | service | true | Zone API per target (AZ-EU, EC-EU, AZ-RANZ, etc.) | `Dockerfile.api` |
| `maas-coordinator` | service | true | Zone coordinator per target (conflict resolution) | `Dockerfile.coordinator` |

### Central services

| Service | workload-kind | MaaS register | Description | Image (Dockerfile) |
|---|---|---|---|---|
| `maas-control-plane` | service | true | Telemetry ingestion + status | `Dockerfile.control-plane` |
| `maas-central-repo` | service | true | Delivery state + catalog | `Dockerfile.central-repo` |
| `maas-scenario-catalog` | service | true | Scenario catalog service | `Dockerfile.scenario-catalog` |
| `maas-orchestrator` | service | true | Cross-zone orchestration | `Dockerfile.orchestrator` |

### Frontend

| Service | workload-kind | MaaS register | Description | Image (Dockerfile) |
|---|---|---|---|---|
| `maas-bff` | service | true | Backend For Frontend (API proxy) | `Dockerfile.bff` |
| `maas-web` | service | true | React UI (nginx) | `Dockerfile.web` |

### Ephemeral workloads (no MaaS registration)

| Workload | workload-kind | Description |
|---|---|---|
| ETL/DQ jobs | job | Ephemeral jobs spawned by orchestrator or API |

These emit `job.runner.*` telemetry events but never register with MaaS.

## Ingress hostnames

| Service | dev | test |
|---|---|---|
| maas-api | `maas-api.dev.jac.dot` | `maas-api.jacloud.nl` |
| maas-coordinator | `maas-coordinator.dev.jac.dot` | `maas-coordinator.jacloud.nl` |
| maas-control-plane | `maas-control-plane.dev.jac.dot` | `maas-control-plane.jacloud.nl` |
| maas-central-repo | `maas-central-repo.dev.jac.dot` | `maas-central-repo.jacloud.nl` |
| maas-scenario-catalog | `maas-scenario-catalog.dev.jac.dot` | `maas-scenario-catalog.jacloud.nl` |
| maas-orchestrator | `maas-orchestrator.dev.jac.dot` | `maas-orchestrator.jacloud.nl` |
| maas-bff | `maas-bff.dev.jac.dot` | `maas-bff.jacloud.nl` |
| maas-web | `maas-ui.dev.jac.dot` | `maas-ui.jacloud.nl` |

## MaaS target mapping

The `metadata-as-a-service` tenant maps directly to the 16-target model. Each zone service (API + coordinator) is deployed per target. Central services and frontend run once per cluster.

| Service type | Placement | target_id |
|---|---|---|
| Zone API + Coordinator | One per target | `AZ-EU`, `EC-EU`, `AZ-RANZ`, ... (all 16) |
| Central services | Once per cluster | Cluster-wide |
| Frontend (BFF + Web) | Once per cluster | Cluster-wide |

### Dev/test target IDs

| Environment | target_id | Region | Provider |
|---|---|---|---|
| dev | `DEV-LOCAL` | N/A | Kind (local) |
| test | `TEST-REMOTE` | N/A | Kind (Debian) |

Each zone service registers its instance as:
```
maas-api-AZ-EU-0
maas-coordinator-AZ-EU-0
maas-api-EC-EU-0
maas-coordinator-EC-EU-0
```

## Shared platform services

The following services are **platform-managed** and consumed by `maas` but **not** owned by the tenant:

| Service | Namespace | Consumed by |
|---|---|---|
| Kong (API Gateway) | `platform-kong` | All tenant services (ingress) |
| Keycloak (SSO) | `platform-keycloak` | maas-api, maas-web |
| Observability stack | `platform-observability` | All tenant services (telemetry) |
| PostgreSQL | — | Zone DBs + central DBs (platform or tenant TBD) |
| MinIO (object storage) | — | Zone storage (platform or tenant TBD) |

## Required labels and annotations

All resources in the `maas-dev` and `maas-test` namespaces must carry the shared platform labels and annotations defined in the [Environment and Deployment Contract](../../../../docs/infra/LOCAL_TO_PRODUCTION_HANDBOFF_CONTRACT.md):

### Required labels
```yaml
labels:
  platform.jaccloud.nl/managed-by: argocd
  platform.jaccloud.nl/environment: dev    # or test
  platform.jaccloud.nl/tenant: maas
  platform.jaccloud.nl/service: <service-name>
  platform.jaccloud.nl/version: <semver>
  platform.jaccloud.nl/image-digest: <sha256:...>
```

### Required annotations
```yaml
annotations:
  platform.jaccloud.nl/target-id: AZ-EU     # zone services: target-specific
  platform.jaccloud.nl/target-id: CLUSTER    # central services: cluster-wide
  platform.jaccloud.nl/workload-kind: service   # or job
  platform.jaccloud.nl/maas-register: "true"    # or "false"
  platform.jaccloud.nl/deployed-at-utc: <iso-8601>
```

## Consumer repo expectations

The `metadata-as-a-service` repository must provide Kubernetes manifests under `k8s/`:

```
metadata-as-a-service/k8s/
├── base/
│   ├── kustomization.yml
│   ├── maas-api/
│   │   ├── deployment.yml
│   │   ├── service.yml
│   │   ├── ingress.yml
│   │   └── configmap.yml
│   ├── maas-coordinator/
│   │   ├── deployment.yml
│   │   ├── service.yml
│   │   ├── ingress.yml
│   │   └── configmap.yml
│   ├── maas-control-plane/
│   ├── maas-central-repo/
│   ├── maas-scenario-catalog/
│   ├── maas-orchestrator/
│   ├── maas-bff/
│   └── maas-web/
├── overlays/
│   ├── dev/
│   │   └── kustomization.yml    # patches hostnames, replicas, resources
│   └── test/
│       └── kustomization.yml    # patches hostnames, replicas, resources
```

The ArgoCD Applications in this tenant overlay reference `{{MAAS_REPO_URL}}/k8s/overlays/<env>` as their source.

## Image contract

Tenant images follow the shared image promotion contract:

| Service | dev registry | test registry |
|---|---|---|
| maas-api | `docker-registry.dev.jac.dot:5000/jacbeekers/maas-api:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/maas-api:0.1.0` |
| maas-coordinator | `docker-registry.dev.jac.dot:5000/jacbeekers/maas-coordinator:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/maas-coordinator:0.1.0` |
| maas-control-plane | `docker-registry.dev.jac.dot:5000/jacbeekers/maas-control-plane:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/maas-control-plane:0.1.0` |
| maas-central-repo | `docker-registry.dev.jac.dot:5000/jacbeekers/maas-central-repo:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/maas-central-repo:0.1.0` |
| maas-scenario-catalog | `docker-registry.dev.jac.dot:5000/jacbeekers/maas-scenario-catalog:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/maas-scenario-catalog:0.1.0` |
| maas-orchestrator | `docker-registry.dev.jac.dot:5000/jacbeekers/maas-orchestrator:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/maas-orchestrator:0.1.0` |
| maas-bff | `docker-registry.dev.jac.dot:5000/jacbeekers/maas-bff:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/maas-bff:0.1.0` |
| maas-web | `docker-registry.dev.jac.dot:5000/jacbeekers/maas-web:0.1.0` | `docker-registry.jacloud.nl:5000/jacbeekers/maas-web:0.1.0` |

Images are built once and promoted by immutable tag or digest. No per-environment rebuilds.

## Secret references

Tenant services must reference secrets, never embed them. Expected secrets in the tenant namespace:

| Secret name | Type | Contents | Provider |
|---|---|---|---|
| `maas-api-db-credentials` | Opaque | `username`, `password` | Platform or tenant |
| `maas-coordinator-db-credentials` | Opaque | `username`, `password` | Platform or tenant |
| `maas-control-plane-db-credentials` | Opaque | `username`, `password` | Platform or tenant |
| `maas-central-repo-db-credentials` | Opaque | `username`, `password` | Platform or tenant |
| `maas-minio-credentials` | Opaque | `access_key`, `secret_key` | Platform or tenant |
| `maas-sso-config` | Opaque | SSO/OIDC settings | Tenant |

## Overlay structure

```
apps/tenants/maas/
├── argocd/                       # ArgoCD Application resources (stays in argocd namespace)
│   ├── maas-api-dev.yml
│   ├── maas-api-test.yml
│   ├── maas-coordinator-dev.yml
│   ├── maas-coordinator-test.yml
│   ├── maas-control-plane-dev.yml
│   ├── maas-control-plane-test.yml
│   ├── maas-central-repo-dev.yml
│   ├── maas-central-repo-test.yml
│   ├── maas-scenario-catalog-dev.yml
│   ├── maas-scenario-catalog-test.yml
│   ├── maas-orchestrator-dev.yml
│   ├── maas-orchestrator-test.yml
│   ├── maas-bff-dev.yml
│   ├── maas-bff-test.yml
│   ├── maas-web-dev.yml
│   └── maas-web-test.yml
├── base/
│   ├── kustomization.yml         # Shared labels, generic namespace template
│   └── namespace.yml             # Namespace 'maas' (renamed per overlay)
├── overlays/
│   ├── dev/
│   │   └── kustomization.yml     # Patches namespace → maas-dev, adds dev labels
│   └── test/
│       └── kustomization.yml     # Patches namespace → maas-test, adds test labels
└── README.md                     # This file
```
