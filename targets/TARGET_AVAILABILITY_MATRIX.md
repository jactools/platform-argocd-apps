# Per-Target Service and Service-Instance Availability Matrix

**Status**: Draft  
**Date**: 2026-08-06

Maps every service and service instance across all 16 MaaS targets. This is the authoritative reference for what runs where.

## 16 MaaS targets

| target_id | Region | Provider | Code |
|---|---|---|---|
| `AZ-EU` | Europe | Azure | EU / AZ-EU |
| `AWS-EU` | Europe | AWS | EU / AWS-EU |
| `EC-EU` | Europe | European Cloud | EU / EC-EU |
| `OP-EU` | Europe | Oracle | EU / OP-EU |
| `AZ-RANZ` | Australia & New Zealand | Azure | RANZ / AZ-RANZ |
| `AWS-RANZ` | Australia & New Zealand | AWS | RANZ / AWS-RANZ |
| `EC-RANZ` | Australia & New Zealand | European Cloud | RANZ / EC-RANZ |
| `OP-RANZ` | Australia & New Zealand | Oracle | RANZ / OP-RANZ |
| `AZ-NA` | North America | Azure | NA / AZ-NA |
| `AWS-NA` | North America | AWS | NA / AWS-NA |
| `EC-NA` | North America | European Cloud | NA / EC-NA |
| `OP-NA` | North America | Oracle | NA / OP-NA |
| `AZ-SA` | South America | Azure | SA / AZ-SA |
| `AWS-SA` | South America | AWS | SA / AWS-SA |
| `EC-SA` | South America | European Cloud | SA / EC-SA |
| `OP-SA` | South America | Oracle | SA / OP-SA |

## Zone services (per-target)

Zone services are deployed once per target. Each target runs its own API and coordinator.

### `dq-made-easy`

| Service | target_id | Instance name | MaaS register | Replicas (dev/test) | Replicas (prod) |
|---|---|---|---|---|---|
| `dq-api` | any | `dq-api-<target_id>-0` | true | 1 | 1+ |
| `dq-engine` | any | `dq-engine-<target_id>-0` | true | 1 | 1+ |

> `dq-ui` is cluster-wide (single frontend), not per-target.

### `metadata-as-a-service`

| Service | target_id | Instance name | MaaS register | Replicas (dev/test) | Replicas (prod) |
|---|---|---|---|---|---|
| `maas-api` | any | `maas-api-<target_id>-0` | true | 1 | 1+ |
| `maas-coordinator` | any | `maas-coordinator-<target_id>-0` | true | 1 | 1+ |

> Central services (control-plane, central-repo, orchestrator, scenario-catalog, bff, web) are cluster-wide, not per-target.

## Central services (cluster-wide)

Central services run once per cluster regardless of the number of targets.

### `dq-made-easy`

| Service | Placement | Instance name | MaaS register |
|---|---|---|---|
| `dq-ui` | Cluster-wide | `dq-ui-CLUSTER-0` | true |

### `metadata-as-a-service`

| Service | Placement | Instance name | MaaS register |
|---|---|---|---|
| `maas-control-plane` | Cluster-wide | `maas-control-plane-CLUSTER-0` | true |
| `maas-central-repo` | Cluster-wide | `maas-central-repo-CLUSTER-0` | true |
| `maas-scenario-catalog` | Cluster-wide | `maas-scenario-catalog-CLUSTER-0` | true |
| `maas-orchestrator` | Cluster-wide | `maas-orchestrator-CLUSTER-0` | true |
| `maas-bff` | Cluster-wide | `maas-bff-CLUSTER-0` | true |
| `maas-web` | Cluster-wide | `maas-web-CLUSTER-0` | true |

## Dev/test targets

Dev and test Kind clusters use synthetic target IDs:

| target_id | Environment | Description |
|---|---|---|
| `DEV-LOCAL` | dev | Local Kind cluster (single target, all services) |
| `TEST-REMOTE` | test | Remote Kind cluster (Debian, single target, all services) |

In dev/test, all zone services are deployed with the synthetic target_id. The cluster topology mirrors production but with a single target.

## Full service-instance matrix (all 16 targets, production)

### `metadata-as-a-service` — zone services

| target_id | maas-api instance | maas-coordinator instance |
|---|---|---|
| `AZ-EU` | `maas-api-AZ-EU-0` | `maas-coordinator-AZ-EU-0` |
| `AWS-EU` | `maas-api-AWS-EU-0` | `maas-coordinator-AWS-EU-0` |
| `EC-EU` | `maas-api-EC-EU-0` | `maas-coordinator-EC-EU-0` |
| `OP-EU` | `maas-api-OP-EU-0` | `maas-coordinator-OP-EU-0` |
| `AZ-RANZ` | `maas-api-AZ-RANZ-0` | `maas-coordinator-AZ-RANZ-0` |
| `AWS-RANZ` | `maas-api-AWS-RANZ-0` | `maas-coordinator-AWS-RANZ-0` |
| `EC-RANZ` | `maas-api-EC-RANZ-0` | `maas-coordinator-EC-RANZ-0` |
| `OP-RANZ` | `maas-api-OP-RANZ-0` | `maas-coordinator-OP-RANZ-0` |
| `AZ-NA` | `maas-api-AZ-NA-0` | `maas-coordinator-AZ-NA-0` |
| `AWS-NA` | `maas-api-AWS-NA-0` | `maas-coordinator-AWS-NA-0` |
| `EC-NA` | `maas-api-EC-NA-0` | `maas-coordinator-EC-NA-0` |
| `OP-NA` | `maas-api-OP-NA-0` | `maas-coordinator-OP-NA-0` |
| `AZ-SA` | `maas-api-AZ-SA-0` | `maas-coordinator-AZ-SA-0` |
| `AWS-SA` | `maas-api-AWS-SA-0` | `maas-coordinator-AWS-SA-0` |
| `EC-SA` | `maas-api-EC-SA-0` | `maas-coordinator-EC-SA-0` |
| `OP-SA` | `maas-api-OP-SA-0` | `maas-coordinator-OP-SA-0` |

### `metadata-as-a-service` — central services

| Service | Instance name |
|---|---|
| `maas-control-plane` | `maas-control-plane-CLUSTER-0` |
| `maas-central-repo` | `maas-central-repo-CLUSTER-0` |
| `maas-scenario-catalog` | `maas-scenario-catalog-CLUSTER-0` |
| `maas-orchestrator` | `maas-orchestrator-CLUSTER-0` |
| `maas-bff` | `maas-bff-CLUSTER-0` |
| `maas-web` | `maas-web-CLUSTER-0` |

### `dq-made-easy` — zone services

| target_id | dq-api instance | dq-engine instance |
|---|---|---|
| `AZ-EU` | `dq-api-AZ-EU-0` | `dq-engine-AZ-EU-0` |
| `AWS-EU` | `dq-api-AWS-EU-0` | `dq-engine-AWS-EU-0` |
| `EC-EU` | `dq-api-EC-EU-0` | `dq-engine-EC-EU-0` |
| `OP-EU` | `dq-api-OP-EU-0` | `dq-engine-OP-EU-0` |
| `AZ-RANZ` | `dq-api-AZ-RANZ-0` | `dq-engine-AZ-RANZ-0` |
| `AWS-RANZ` | `dq-api-AWS-RANZ-0` | `dq-engine-AWS-RANZ-0` |
| `EC-RANZ` | `dq-api-EC-RANZ-0` | `dq-engine-EC-RANZ-0` |
| `OP-RANZ` | `dq-api-OP-RANZ-0` | `dq-engine-OP-RANZ-0` |
| `AZ-NA` | `dq-api-AZ-NA-0` | `dq-engine-AZ-NA-0` |
| `AWS-NA` | `dq-api-AWS-NA-0` | `dq-engine-AWS-NA-0` |
| `EC-NA` | `dq-api-EC-NA-0` | `dq-engine-EC-NA-0` |
| `OP-NA` | `dq-api-OP-NA-0` | `dq-engine-OP-NA-0` |
| `AZ-SA` | `dq-api-AZ-SA-0` | `dq-engine-AZ-SA-0` |
| `AWS-SA` | `dq-api-AWS-SA-0` | `dq-engine-AWS-SA-0` |
| `EC-SA` | `dq-api-EC-SA-0` | `dq-engine-EC-SA-0` |
| `OP-SA` | `dq-api-OP-SA-0` | `dq-engine-OP-SA-0` |

### `dq-made-easy` — cluster-wide services

| Service | Instance name |
|---|---|
| `dq-ui` | `dq-ui-CLUSTER-0` |

## Ephemeral jobs (all targets)

Ephemeral workloads run on demand in any target. They do not register with MaaS.

| Workload | Spawns in | MaaS register | Telemetry |
|---|---|---|---|
| Spark jobs | `dq-engine` pod's target | false | `job.runner.*` |
| Profiling workers | `dq-api` pod's target | false | `job.runner.*` |
| Airflow DAGs | Any target (scheduled) | false | `job.runner.*` |

## Service availability by target summary

A service is **available** in a target when at least one registered instance exists there.

| Target | Platform services | `dq-made-easy` services | `metadata-as-a-service` services |
|---|---|---|---|
| `AZ-EU` | Kong, Keycloak, Observability | `dq-api-AZ-EU-0`, `dq-engine-AZ-EU-0`, `dq-ui-CLUSTER-0` | `maas-api-AZ-EU-0`, `maas-coordinator-AZ-EU-0`, + central services |
| `AWS-EU` | Kong, Keycloak, Observability | `dq-api-AWS-EU-0`, `dq-engine-AWS-EU-0`, `dq-ui-CLUSTER-0` | `maas-api-AWS-EU-0`, `maas-coordinator-AWS-EU-0`, + central services |
| `EC-EU` | Kong, Keycloak, Observability | `dq-api-EC-EU-0`, `dq-engine-EC-EU-0`, `dq-ui-CLUSTER-0` | `maas-api-EC-EU-0`, `maas-coordinator-EC-EU-0`, + central services |
| `OP-EU` | Kong, Keycloak, Observability | `dq-api-OP-EU-0`, `dq-engine-OP-EU-0`, `dq-ui-CLUSTER-0` | `maas-api-OP-EU-0`, `maas-coordinator-OP-EU-0`, + central services |
| `AZ-RANZ` | Kong, Keycloak, Observability | `dq-api-AZ-RANZ-0`, `dq-engine-AZ-RANZ-0`, `dq-ui-CLUSTER-0` | `maas-api-AZ-RANZ-0`, `maas-coordinator-AZ-RANZ-0`, + central services |
| `AWS-RANZ` | Kong, Keycloak, Observability | `dq-api-AWS-RANZ-0`, `dq-engine-AWS-RANZ-0`, `dq-ui-CLUSTER-0` | `maas-api-AWS-RANZ-0`, `maas-coordinator-AWS-RANZ-0`, + central services |
| `EC-RANZ` | Kong, Keycloak, Observability | `dq-api-EC-RANZ-0`, `dq-engine-EC-RANZ-0`, `dq-ui-CLUSTER-0` | `maas-api-EC-RANZ-0`, `maas-coordinator-EC-RANZ-0`, + central services |
| `OP-RANZ` | Kong, Keycloak, Observability | `dq-api-OP-RANZ-0`, `dq-engine-OP-RANZ-0`, `dq-ui-CLUSTER-0` | `maas-api-OP-RANZ-0`, `maas-coordinator-OP-RANZ-0`, + central services |
| `AZ-NA` | Kong, Keycloak, Observability | `dq-api-AZ-NA-0`, `dq-engine-AZ-NA-0`, `dq-ui-CLUSTER-0` | `maas-api-AZ-NA-0`, `maas-coordinator-AZ-NA-0`, + central services |
| `AWS-NA` | Kong, Keycloak, Observability | `dq-api-AWS-NA-0`, `dq-engine-AWS-NA-0`, `dq-ui-CLUSTER-0` | `maas-api-AWS-NA-0`, `maas-coordinator-AWS-NA-0`, + central services |
| `EC-NA` | Kong, Keycloak, Observability | `dq-api-EC-NA-0`, `dq-engine-EC-NA-0`, `dq-ui-CLUSTER-0` | `maas-api-EC-NA-0`, `maas-coordinator-EC-NA-0`, + central services |
| `OP-NA` | Kong, Keycloak, Observability | `dq-api-OP-NA-0`, `dq-engine-OP-NA-0`, `dq-ui-CLUSTER-0` | `maas-api-OP-NA-0`, `maas-coordinator-OP-NA-0`, + central services |
| `AZ-SA` | Kong, Keycloak, Observability | `dq-api-AZ-SA-0`, `dq-engine-AZ-SA-0`, `dq-ui-CLUSTER-0` | `maas-api-AZ-SA-0`, `maas-coordinator-AZ-SA-0`, + central services |
| `AWS-SA` | Kong, Keycloak, Observability | `dq-api-AWS-SA-0`, `dq-engine-AWS-SA-0`, `dq-ui-CLUSTER-0` | `maas-api-AWS-SA-0`, `maas-coordinator-AWS-SA-0`, + central services |
| `EC-SA` | Kong, Keycloak, Observability | `dq-api-EC-SA-0`, `dq-engine-EC-SA-0`, `dq-ui-CLUSTER-0` | `maas-api-EC-SA-0`, `maas-coordinator-EC-SA-0`, + central services |
| `OP-SA` | Kong, Keycloak, Observability | `dq-api-OP-SA-0`, `dq-engine-OP-SA-0`, `dq-ui-CLUSTER-0` | `maas-api-OP-SA-0`, `maas-coordinator-OP-SA-0`, + central services |

## Instance naming rules

1. **Zone services**: `<service_name>-<target_id>-<replica_index>`
2. **Central services**: `<service_name>-CLUSTER-<replica_index>`
3. **Ephemeral jobs**: No fixed name — created dynamically by the spawning service
4. **Replica index**: Starts at 0, increments for additional replicas

## Dev/test mapping

In dev/test Kind clusters, the synthetic target replaces all 16 production targets:

| Service | dev instance | test instance |
|---|---|---|
| `dq-api` | `dq-api-DEV-LOCAL-0` | `dq-api-TEST-REMOTE-0` |
| `dq-engine` | `dq-engine-DEV-LOCAL-0` | `dq-engine-TEST-REMOTE-0` |
| `dq-ui` | `dq-ui-CLUSTER-0` | `dq-ui-CLUSTER-0` |
| `maas-api` | `maas-api-DEV-LOCAL-0` | `maas-api-TEST-REMOTE-0` |
| `maas-coordinator` | `maas-coordinator-DEV-LOCAL-0` | `maas-coordinator-TEST-REMOTE-0` |
| `maas-control-plane` | `maas-control-plane-CLUSTER-0` | `maas-control-plane-CLUSTER-0` |
| `maas-central-repo` | `maas-central-repo-CLUSTER-0` | `maas-central-repo-CLUSTER-0` |
| `maas-scenario-catalog` | `maas-scenario-catalog-CLUSTER-0` | `maas-scenario-catalog-CLUSTER-0` |
| `maas-orchestrator` | `maas-orchestrator-CLUSTER-0` | `maas-orchestrator-CLUSTER-0` |
| `maas-bff` | `maas-bff-CLUSTER-0` | `maas-bff-CLUSTER-0` |
| `maas-web` | `maas-web-CLUSTER-0` | `maas-web-CLUSTER-0` |
