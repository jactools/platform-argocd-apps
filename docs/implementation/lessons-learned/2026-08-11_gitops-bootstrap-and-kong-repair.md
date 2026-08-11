# Lessons Learned — GitOps Bootstrap and Kong Repair

**Date**: 2026-08-11  
**Context**: Env-driven ArgoCD repo registration, dev/test/prod bootstrap alignment, Kong dev image sourcing, and shared secret bootstrap repair  
**Audience**: Platform team, future on-call operators

---

## Summary

This work fixed the dev GitOps path from repo registration through Kong startup. The biggest issues were not in Kong itself at first, but in the surrounding control plane: source URLs were tracked in YAML, the Kind node could not reach the host-local registry directly, and the shared secret bootstrap depended on resources that were not reliably present before the job ran.

---

## 1. Kind still needs a node-local image, even when the registry push succeeds

### What happened

The PostgreSQL image was mirrored to the local registry, but the Kind node resolved `docker-registry.dev.jac.dot` to `127.0.0.1`. That meant the node still could not pull the image from inside the cluster, even though the registry push itself succeeded.

### Lesson

**A successful registry push is not enough for Kind. The image must also be loaded into the node with the exact manifest the node can run.**

For this repair, the working path was:

1. mirror `postgres:17-bookworm` to the local registry,
2. resolve the platform-specific upstream manifest digest,
3. tag that digest locally,
4. load the tagged image into the Kind control-plane node.

### Why it matters

Without the node-local load, the pod keeps retrying the host registry path and falls back into `ImagePullBackOff` even though the registry contains the image.

---

## 2. Embedded shell scripts in YAML must stay valid YAML first

### What happened

The shared secret-init ConfigMap embedded a heredoc-style script. A small indentation mistake in that block made the whole manifest invalid, so ArgoCD could not render the app and the secret-init hook never ran.

### Lesson

**Treat embedded scripts as YAML content first and shell content second. A heredoc that looks fine in a terminal can still break manifest rendering.**

When a ConfigMap stores a generated script, prefer shell constructions that are less fragile inside YAML block scalars.

### Why it matters

If the manifest does not render, ArgoCD never gets to the point where it can create the service account, ConfigMap, or job that the script depends on.

---

## 3. Secret generators must read from the namespace where the secret lives

### What happened

The password helper originally looked for an existing secret in a hardcoded namespace. That made the generated password unstable and caused the Kong database secret to drift unexpectedly.

### Lesson

**Namespace must be an input to secret lookup, not an assumption.**

The stable pattern is:

```bash
existing=$(kubectl get secret "$secret_name" -n "$namespace" -o jsonpath="{.data.$key}" 2>/dev/null | base64 -d 2>/dev/null || true)
```

### Why it matters

A hardcoded namespace can silently rotate credentials on every sync, which breaks any stateful service that depends on those values staying consistent.

---

## 4. ArgoCD hooks should not depend on resources that are created by the same hook phase

### What happened

The secret-init job initially ran as a PreSync hook while its service account, RBAC, and ConfigMap were also being created in the same sync flow. That produced races where the job started before its dependencies existed.

### Lesson

**If a hook depends on supporting resources, keep those support resources as regular synced objects and run the job later, not earlier.**

For this repo, the stable pattern was:

- sync the ConfigMap, ServiceAccount, ClusterRole, and ClusterRoleBinding normally,
- run the secret-init job as a PostSync step.

### Why it matters

This avoids `serviceaccount not found` and `configmap not found` failures during hook startup.

---

## 5. A healthy migration log does not prove the live app is healthy

### What happened

The Kong migration job reported `Database is up-to-date`, but the live proxy still crashed until the database schema and credentials were verified against the running pod.

### Lesson

**Always verify the live database schema and the live secret values, not just the job logs.**

Useful checks after a bootstrap or password rotation:

- `kubectl exec ... -- psql -U kong -d kong -c '\dt'`
- `kubectl get secret kong-db-credentials -n platform-kong -o yaml`
- `kubectl logs deploy/kong`

### Why it matters

Stateful startup failures often look like application crashes, but the real issue is usually an out-of-band state mismatch: missing tables, stale credentials, or a secret generated from the wrong namespace.

---

## 6. Separate control-plane fixes from application fixes

### What happened

This repair initially looked like a Kong-only issue, but it actually spanned repo registration, bootstrap source selection, Kind image availability, secret generation, and database initialization.

### Lesson

**When a GitOps workload fails, fix the control-plane dependencies first. Only then should you chase application startup logs.**

That sequencing saved time here because Kong itself was not the first failure; the surrounding bootstrap path was.

---

## Quick Reference

- Mirror and preload dev images through the repo-owned publisher script, not by hand.
- Keep dev on `file:///repos`, test and prod on GitHub URLs.
- Make secret generation namespace-aware.
- Prefer PostSync for jobs that require the same-app ConfigMap and RBAC to exist first.
