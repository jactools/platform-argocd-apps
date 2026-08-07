# Secrets and Ingress Hostname Contract

**Status**: Draft  
**Date**: 2026-08-06

Defines how consumer tenants consume secrets and ingress hostnames from the ArgoCD overlay.

## Ingress hostnames

### Naming convention

| Component | Pattern | dev example | test example |
|---|---|---|---|
| Tenant service | `<service>.<env>.jac.dot` | `dq-api.dev.jac.dot` | `dq-api.jacloud.nl` |
| Platform service | `<service>.<env>.jac.dot` | `kong.dev.jac.dot` | `kong.jacloud.nl` |

### How consumers define hostnames

Consumer Kustomize overlays patch the base ingress manifest with environment-specific hostnames:

```yaml
# dq-made-easy/k8s/overlays/dev/kustomization.yml
patches:
  - target:
      kind: Ingress
      name: dq-api
    patch: |
      - op: replace
        path: /spec/rules/0/host
        value: dq-api.dev.jac.dot
  - target:
      kind: Ingress
      name: dq-ui
    patch: |
      - op: replace
        path: /spec/rules/0/host
        value: dq-ui.dev.jac.dot
  - target:
      kind: Ingress
      name: dq-engine
    patch: |
      - op: replace
        path: /spec/rules/0/host
        value: dq-engine.dev.jac.dot
```

### Platform-managed TLS

The platform creates `kubernetes.io/tls` Secrets for every service in `tmp/certs/`. The Ingress resource references them:

```yaml
# Consumer base ingress (dq-made-easy/k8s/base/dq-api/ingress.yml)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dq-api
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - dq-api.dev.jac.dot
      secretName: dq-api.dev.jac.dot-tls
  rules:
    - host: dq-api.dev.jac.dot
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: dq-api
                port:
                  name: https
```

The TLS secret `dq-api.dev.jac.dot-tls` is created by the platform during cluster provisioning (`scripts/kind.sh create`). The consumer only references it.

### DNS resolution

In Kind clusters, DNS resolution is handled by `/etc/hosts` entries or local DNS. The platform ensures that the ingress controller (ingress-nginx) routes traffic to the correct service based on the `Host` header.

## Secrets

### Secret ownership model

| Secret type | Owner | Namespace | How consumer gets it |
|---|---|---|---|
| TLS certificates | Platform | Tenant namespace | Auto-created by `kind.sh create` |
| Platform DB credentials | Platform | Tenant namespace | Platform deploys via ArgoCD |
| Tenant app secrets | Consumer | Tenant namespace | Consumer defines in Kustomize overlay |
| Registry pull secrets | Platform | Tenant namespace | Platform configures for image pulls |
| SSO/OIDC config | Consumer | Tenant namespace | Consumer defines in Kustomize overlay |

### How consumers define secrets

Consumers include secrets in their Kustomize overlays using `secretGenerator` or inline `Secret` resources:

#### Option A: Kustomize `secretGenerator` (dev/testing)

```yaml
# dq-made-easy/k8s/overlays/dev/kustomization.yml
secretGenerator:
  - name: dq-api-db-credentials
    literals:
      - username=dq_user
      - password=dq_dev_password
    behavior: create
  - name: dq-api-encryption-key
    literals:
      - encryption_key=dev-encryption-key-change-in-prod
    behavior: create
  - name: dq-api-sso-config
    literals:
      - SSO_ISSUER=https://keycloak.dev.jac.dot/auth/realms/jaccloud
      - SSO_CLIENT_ID=dq-api
    behavior: create
```

> **Note**: `secretGenerator` adds a hash suffix to the secret name. Consumers must use `generatorOptions` to control this:
> ```yaml
> generatorOptions:
>   disableNameSuffixHash: true
> ```

#### Option B: Inline Secret resources (explicit control)

```yaml
# dq-made-easy/k8s/overlays/dev/secrets.yml
---
apiVersion: v1
kind: Secret
metadata:
  name: dq-api-db-credentials
  namespace: dq-dev
type: Opaque
stringData:
  username: dq_user
  password: dq_dev_password
---
apiVersion: v1
kind: Secret
metadata:
  name: dq-api-sso-config
  namespace: dq-dev
type: Opaque
stringData:
  SSO_ISSUER: https://keycloak.dev.jac.dot/auth/realms/jaccloud
  SSO_CLIENT_ID: dq-api
```

#### Option C: External Secrets (production — future)

When the platform adopts `ExternalSecretsOperator` or `SOPS`, consumers will reference external secret stores:

```yaml
# dq-made-easy/k8s/overlays/test/external-secrets.yml
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: dq-api-db-credentials
  namespace: dq-test
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: dq-api-db-credentials
  data:
    - secretKey: username
      remoteRef:
        key: dq/dev/db
        property: username
    - secretKey: password
      remoteRef:
        key: dq/dev/db
        property: password
```

### How consumers reference secrets in deployments

Deployments reference secrets via environment variables or volume mounts:

```yaml
# dq-made-easy/k8s/base/dq-api/deployment.yml
spec:
  template:
    spec:
      containers:
        - name: dq-api
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: dq-api-db-credentials
                  key: connection_string
            - name: APP_CONFIG_ENCRYPTION_KEY
              valueFrom:
                secretKeyRef:
                  name: dq-api-encryption-key
                  key: encryption_key
            - name: SSO_ISSUER
              valueFrom:
                secretKeyRef:
                  name: dq-api-sso-config
                  key: SSO_ISSUER
```

### Platform-provided secrets (available to consumers)

The platform creates these secrets that consumers can reference:

| Secret name | Namespace | Contents | Purpose |
|---|---|---|---|
| `dq-api.dev.jac.dot-tls` | `dq-dev` | `tls.crt`, `tls.key` | TLS for ingress |
| `maas-api.dev.jac.dot-tls` | `maas-dev` | `tls.crt`, `tls.key` | TLS for ingress |

Platform-managed dependencies (Kong, Keycloak, observability) are reachable via their Kubernetes service names:

| Service | DNS name (dev) | Port | Purpose |
|---|---|---|---|
| Kong proxy | `kong-proxy.platform-kong.svc.cluster.local` | 8000 | API gateway |
| Keycloak | `keycloak.platform-keycloak.svc.cluster.local` | 8443 | SSO/OIDC |
| OTel collector | `otel-collector.platform-observability.svc.cluster.local` | 4317 | Telemetry (gRPC) |
| Loki | `loki.platform-observability.svc.cluster.local` | 3100 | Logs |
| Prometheus | `prometheus.platform-observability.svc.cluster.local` | 9090 | Metrics |
| Tempo | `tempo.platform-observability.svc.cluster.local` | 3200 | Traces |

## Consumer overlay structure example

```
dq-made-easy/k8s/
├── base/
│   ├── kustomization.yml
│   ├── dq-api/
│   │   ├── deployment.yml          # references secrets by name
│   │   ├── service.yml
│   │   ├── ingress.yml             # references TLS secret by name
│   │   └── configmap.yml           # non-sensitive config
│   └── dq-ui/
│       ├── deployment.yml
│       ├── service.yml
│       └── ingress.yml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yml       # patches hostnames, images
│   │   └── secrets.yml             # dev secrets (Option B)
│   └── test/
│       ├── kustomization.yml       # patches hostnames, images
│       └── secrets.yml             # test secrets
```

## Rules

1. **No embedded secrets in base manifests**: Base manifests reference secrets by name only. Secrets are defined in overlays.
2. **TLS secrets are platform-managed**: Consumers reference TLS secrets created by the platform. They do not create their own TLS certificates.
3. **SSO config points to platform Keycloak**: Consumer SSO/OIDC settings reference the platform Keycloak service URL, not a separate instance.
4. **Environment-specific secrets only**: Each overlay defines its own secrets. Dev secrets are never committed to version control in production overlays.
5. **Secret names follow convention**: `<tenant>-<service>-<purpose>` (e.g. `dq-api-db-credentials`).
6. **Consumers reference platform services via DNS**: No manual port-forwarding or external URLs — all service-to-service communication uses Kubernetes DNS (`<service>.<namespace>.svc.cluster.local`).
