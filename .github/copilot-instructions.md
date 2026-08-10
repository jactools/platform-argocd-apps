# Copilot Instructions for platform-argocd-apps

## Operating rules

- Treat Git as the source of truth for all ArgoCD-managed resources.
- Do not recommend or perform direct `kubectl` writes to ArgoCD-managed namespaces unless the task is explicitly a break-glass emergency.
- Use `kubectl` for read-only inspection, debugging, and verification.
- For any lasting change, update the Git manifests and keep ArgoCD reconciliation as the deployment path.
- Shared ownership must be explicit in manifests through `ignoreDifferences` or a controller-specific rule, not handled ad hoc in the cluster.

## Namespaces to treat as ArgoCD-managed

- Platform: `platform-kong`, `platform-keycloak`, `platform-observability`, `platform-redis`, `platform-tls`, `kyverno`
- Tenants: `dq-dev`, `dq-test`, `maas-dev`, `maas-test`
- Control plane: `argocd`

## Repo-specific reminders

- Refer to [ARGOCD_KUBECTL_WRITE_POLICY.md](../ARGOCD_KUBECTL_WRITE_POLICY.md) for the full policy and break-glass workflow.
- Prefer small, local edits that preserve the existing layout.
- When changing manifests, check whether the repository validation scripts or sync checks are affected.
