# 🧭 Foliohive — CKAD & AKS Discovery Lab

This repository is a living laboratory. We do not just deploy tools; we deconstruct them to understand the Kubernetes API, master the CKAD domains, and prepare for production-grade AKS architecture.

**The Trio Engine:**
* **Joshua (The Architect):** Drives the experiments, questions the architecture, and normalizes the cluster state.
* **Gemini (The Guide):** Maps local experiments to CKAD exam objectives and enterprise AKS realities.
* **Reasonix (The Agent):** Drafts the boilerplate, refactors YAML, and maintains declarative strictness.

---


---

## 🔬 1. Active Sandbox

| Property                | Value |
|-------------------------|-------|
| Compute                 | Azure VM (bare-metal emulation) |
| Control plane           | Minikube `ckad-docker` — **Docker driver**, 2 nodes |
| Kubernetes version      | `v1.35.1` |
| Node topology           | `ckad-docker` (control-plane), `ckad-docker-m02` (worker) |
| Ingress                 | NGINX Ingress Controller (Minikube addon), `api.foliohive.local` |
| Monitoring              | Prometheus + Grafana via `kube-prometheus-stack` Helm chart, Loki (log aggregation) + Promtail (log collector) |
| Metrics                 | Minikube metrics-server addon with `--kubelet-insecure-tls` |
| Stateful storage        | PostgreSQL 18.4 on StatefulSet with hostPath PV pinned to worker node |
| Orchestration           | `up.sh` — idempotent convergence loop (no imperative mutations) |

### Manifests (project root)

| File | Resources |
|------|-----------|
| `ns.yaml` | Namespaces `lab-pack`, `monitoring` |
| `db.yaml` | StatefulSet `postgres`, Service `postgres-service` (headless), PV, PVC, SA + Role + RoleBinding |
| `api.yaml` | Deployment `backend-fastapi`, Service `api-service` (ClusterIP :80 → :8000), HPA |
| `secret/secret.yaml` | Opaque Secret `postgres-secret` (user, password, db) |
| `platform-network/ingress.yaml` | Ingress `foliohive-ingress` routing `api.foliohive.local` → `api-service:80` |
| `platform-network/network-policy.yaml` | NetworkPolicy locking postgres ingress to only backend pods on port 5432 |
| `platform-monitoring/api-service-monitor.yaml` | ServiceMonitor for backend-fastapi (Prometheus auto-discovery) |
| `platform-monitoring/ingress-monitor.yaml` | Ingress for Grafana (`/grafana`) and Prometheus (`/prometheus`) sub-paths |
| `cluster-config/coredns-patch.yaml` | Kustomize patch changing CoreDNS liveness probe from `/health` to `/ready` |

### Helm

| Chart | Namespace | Purpose |
|-------|-----------|---------|
| `platform-monitoring/` (v2, `kube-prometheus-stack` + `loki` + `promtail` deps) | `monitoring` | Prometheus + Grafana + node-exporter (alertmanager disabled), Loki (single-binary filesystem), Promtail (DaemonSet log collector) |

### Current cluster state (kube-system)

| Pod | Status | Role |
|-----|--------|------|
| coredns | Running | Cluster DNS (patched) |
| kindnet | Running × 2 | CNI (DaemonSet) |
| kube-apiserver / etcd / kube-scheduler / kube-controller-manager | Running | Control plane |
| kube-proxy | Running × 2 | Service networking (iptables) |
| metrics-server | Running | Resource metrics for HPA |
| storage-provisioner | Running | Dynamic storage |

---

## 🏆 2. CKAD Competencies Proven

### Stateful Application Design
- `StatefulSet` with headless service (`postgres-service`, `clusterIP: None`) for stable network identity (`postgres-0`)
- PVC via `volumeClaimTemplates` bound to a hostPath PV pinned to the worker node via `nodeAffinity`
- Explicit `securityContext`: `runAsUser: 999` (matches native postgres Linux UID), `fsGroup: 999`

### Multi-Container Pod Design (Init Container)
- **InitContainer `run-migrations`** runs `alembic upgrade head` before the main container starts
- Uses the same runtime image (`fastapi:v11`) and inherits the same env config
- Blocking pattern: migrations must succeed before the FastAPI app launches
- `securityContext` hardening: `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, ephemeral `/tmp` volume

### Pod Hardening & Least Privilege
- `automountServiceAccountToken: false`
- `readOnlyRootFilesystem: true` on both init and main containers
- `runAsNonRoot: true`, `runAsUser: 1000`
- Non-root user `appuser` in Docker image

### Application Environment & Configuration
- All secrets injected via `secretKeyRef` env vars (never baked into images or Git)
- DSN built at runtime from component env vars via Pydantic `BaseSettings`
- `.env` file for local dev only; `.env` is gitignored

### Pod Self-Healing (Probes)
- **Liveness:** `GET /healthz` (lightweight — no DB dependency)
- **Readiness:** `GET /db-check` (runs `SELECT 1` — removes pod from Service when DB is down)
- Both: initialDelay 5s, period 10s, timeout 2s, failureThreshold 3

### Horizontal Pod Autoscaling
- CPU threshold: 70% average utilization
- Memory threshold: 80% average utilization
- Scale-down stabilization: 60s (vs. default 5 min)
- Instant scale-up: 0s stabilization window
- Min 2 / Max 5 replicas

### Ingress & Cross-Namespace Routing
- Single `api.foliohive.local` host routes to lab-pack API (`/`)
- Same host routes Grafana (`/grafana`) and Prometheus (`/prometheus`) in the `monitoring` namespace via regex sub-paths and rewrite-target

### Network Policy
- Postgres accepts **only** traffic from pods with label `app.kubernetes.io/name: backend-fastapi` on port 5432
- All other ingress to postgres is dropped

### Observability
- JSON-structured logging to stdout via `pythonjsonlogger`
- Prometheus metrics auto-exposed at `/metrics` via `prometheus_fastapi_instrumentator`
- ServiceMonitor for Prometheus auto-discovery
- Grafana with admin credentials (`admin` / `admin`)
- **Loki** (single-binary filesystem mode) for log aggregation — lean footprint, no object store dependency
- **Promtail** DaemonSet collecting all pod logs and shipping to Loki
- Loki registered as a Grafana datasource for log exploration alongside metrics

---

## 🚀 3. Current Frontier (Active Discoveries)

### Module A ✅ Completed: Configuration & Secrets Lifecycle
*CKAD Domain: Configuration & Security (15%)*
- Pydantic `BaseSettings` loads from env vars (Kubernetes `secretKeyRef`)
- `.env` used only for local development; never deployed to cluster
- Secret `postgres-secret` is an Opaque secret, injected as individual env vars (not mounted as volumes)
- Known limitation: No config reload on secret rotation (requires pod restart)

### Module B ✅ Completed: Init Container Pattern (Alembic)
*CKAD Domain: Pod Design (20%)*
- InitContainer `run-migrations` runs `alembic upgrade head` before the main app starts
- DNS workaround: `hostAliases` added because CoreDNS kubernetes plugin failed to watch the API server, breaking cluster DNS for `*.svc.cluster.local` names
- Fallback: App's `on_event("startup")` also calls `Base.metadata.create_all()` to catch local dev scenarios

### Module C 🔄 In Progress: Pod Self-Healing
*CKAD Domain: Observability & Maintenance (15%)*
- Probes are deployed and verified
- Next: Inject latency / memory pressure and observe probe behavior; tune failure thresholds

### Module D 🔮 Next: GitOps Convergence
*CKAD Domain: App Deployment (20%)*
- Currently `up.sh` is a bash convergence loop (apply-and-wait)
- Target: Replace with ArgoCD watching this Git repo and pulling changes automatically
- Pre-requisite: Repo must be properly structured with Kustomize overlays for env differences

### Module E ✅ Completed: Log Aggregation (Loki + Promtail)
*CKAD Domain: Observability & Maintenance (15%)*
- Loki deployed in single-binary filesystem mode — no object store dependency, minimal resource footprint (100m CPU / 128Mi memory)
- Promtail DaemonSet scrapes all pod logs across cluster nodes (50m CPU / 64Mi memory per node)
- Loki registered as an additional Grafana datasource for Explore → Logs
- Log shipping path: container stdout → Promtail → Loki → Grafana
- Known limitation: Filesystem storage is ephemeral (emptyDir) — logs lost on pod restart; acceptable for lab

---

## 🧱 Project Architecture

```
root/
├── api.yaml                  # Backend Deployment + Service + HPA
├── db.yaml                   # PostgreSQL StatefulSet + headless Service + PV + RBAC
├── ns.yaml                   # Namespaces
├── secret/secret.yaml        # Opaque database credentials
├── up.sh                     # Convergence orchestrator
├── platform-network/         # Ingress rules, NetworkPolicy
├── platform-monitoring/      # Helm chart + ServiceMonitor + monitoring Ingress
├── cluster-config/           # Kustomize patches (CoreDNS)
└── src/
    ├── Dockerfile            # Multi-stage build (python:3.11-slim)
    ├── requirements.txt      # FastAPI, SQLAlchemy, psycopg, Alembic, etc.
    ├── alembic.ini
    ├── alembic/              # Migration scripts
    └── app/
        ├── app.py            # FastAPI routes + startup
        ├── config.py         # Pydantic Settings
        ├── db.py             # SQLAlchemy engine + Base + session
        ├── models.py         # User ORM model
        ├── schemas.py        # Pydantic request/response DTOs
        └── logging_config.py # JSON logging config
```

### Stack versions

| Component | Version |
|-----------|---------|
| Python | 3.11 |
| FastAPI | 0.136.0 |
| SQLAlchemy | 2.0.36 |
| psycopg (binary) | 3.2.1 |
| Alembic | 1.14.0 |
| Pydantic Settings | 2.6.1 |
| Postgres image | 18.4-bookworm |

### Commands (run from `src/`)

| Action | Command |
|--------|---------|
| Dev server | `uvicorn app.app:app --host 127.0.0.1 --port 8000 --reload` |
| Alembic migration | `alembic upgrade head` |
| Docker build | `docker build -t fastapi:v11 .` (from `src/`) |
| Minikube image load | `minikube -p ckad-docker image load fastapi:v11` |
| Full cluster deploy | `./up.sh` |

---

## 🔮 4. Next Steps

1. **Test suite** — no tests exist yet; `pytest` + `httpx.AsyncClient` for FastAPI
2. **CI pipeline** — GitHub Actions to lint, test, build, and push image
3. **Prometheus alerting** — configure Alertmanager rules for pod health, HPA thresholds
4. **Kustomize overlays** — dev/staging/prod with env-specific values
5. **GitOps** — replace `up.sh` imperative loop with ArgoCD declarative sync
6. **DB session DI** — migrate from manual `SessionLocal()` to FastAPI `Depends()` for proper request lifecycle management

---

### Sample Convergence engine for `./up.sh`
```bash
#!/bin/bash
echo "🔄 Step 1: Checking code state synchronization..."
# If we are tracking via Git, ensure we pull the latest committed changes
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "📦 Code repo detected. Synchronizing localized source files..."
    # In a real pipeline this would be 'git pull', locally we just read the workspace
fi
```

