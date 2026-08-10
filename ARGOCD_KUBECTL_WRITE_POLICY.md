# ArgoCD and kubectl Write Policy

## Purpose

This repository should treat Git as the source of truth for every ArgoCD-managed workload. Direct `kubectl` writes to those resources should be blocked by default so that live cluster state does not drift away from Git.

## Recommendation

Block human write access to ArgoCD-managed resources in both platform and tenant namespaces. Keep `kubectl` available for read-only debugging and diagnostics, and use a documented break-glass flow for emergencies.

## Namespaces in scope

### Platform project

From [argocd/config/projects/platform-project.yml](argocd/config/projects/platform-project.yml):

- `platform-kong`
- `platform-keycloak`
- `platform-observability`
- `platform-redis`
- `platform-tls`
- `kyverno`

### Tenant project

From [argocd/config/projects/tenant-project.yml](argocd/config/projects/tenant-project.yml):

- `dq-dev`
- `dq-test`
- `maas-dev`
- `maas-test`

### Shared control namespace

- `argocd`

`argocd` should remain tightly restricted because it hosts the ArgoCD control plane, not application ownership.

## Policy matrix

| Namespace group | `kubectl get/list/watch` | `kubectl logs/exec` | `kubectl apply/edit/patch/delete` | Notes |
|---|---|---|---|---|
| `argocd` | Allow | Allow, where needed | Deny for non-admins | Control plane only |
| Platform namespaces | Allow | Allow | Deny by default | Changes go through Git |
| Tenant namespaces | Allow | Allow | Deny by default | Same GitOps rule |
| Break-glass operators | Allow | Allow | Allow temporarily | Must follow emergency workflow |

## Enforcement model

### 1. RBAC first

Default human roles should be read-only in ArgoCD-managed namespaces. If someone needs to troubleshoot, they should be able to inspect workloads, logs, and pod shells without being able to mutate the desired state.

### 2. Admission control second

Use Kyverno or OPA to block direct writes to resources that ArgoCD is managing. A practical match is the ArgoCD tracking annotation or instance label on the live object. That keeps the policy aligned with actual ownership instead of only namespace membership.

### 3. Self-healing stays on

Keep ArgoCD self-heal enabled on production-like applications so that any accidental mutation that slips through is quickly reverted.

### 4. Shared ownership must be explicit

If a field is legitimately owned by another controller, do not rely on ad hoc `kubectl` edits. Declare the exception in Git with `ignoreDifferences` or a controller-specific ownership rule.

Typical examples are fields such as:

- HPA-managed replica counts
- controller-managed annotations
- other narrowly scoped runtime fields that are intentionally not Git-owned

## Break-glass workflow

If a live change is truly required:

1. Temporarily disable auto-sync for the affected application.
2. Apply the emergency change.
3. Open and merge the matching Git change immediately.
4. Re-enable auto-sync.
5. Verify the application is back in sync.

This keeps `kubectl` as an exception path, not a parallel deployment mechanism.

## Namespace-specific guidance

### Platform namespaces

Treat the platform namespaces as owned by the platform foundation team. These namespaces should have the strictest write controls because they usually host shared infrastructure and security-sensitive components.

### Tenant namespaces

Treat tenant namespaces the same way from a GitOps perspective. The ownership boundary is different, but the operating rule is the same: Git changes first, cluster writes only through break-glass.

## Suggested rollout order

1. Make namespace RBAC read-only for most humans.
2. Add an admission policy in audit mode to confirm what would be blocked.
3. Move the admission policy to enforce once the false-positive set is understood.
4. Add any required `ignoreDifferences` rules for intentional shared ownership.
5. Keep a small, documented break-glass group for emergencies.

## Bottom line

Yes, blocking `kubectl` writes to ArgoCD-managed resources is the right default for this repository. Use Git for all lasting changes, reserve `kubectl` for inspection and emergency intervention, and make any exceptions explicit in policy rather than informal practice.
