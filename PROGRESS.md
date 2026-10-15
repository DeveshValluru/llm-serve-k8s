# Progress Tracker — llm-serve-k8s

21-day Kubernetes for LLM Inference course. Repo: https://github.com/DeveshValluru/llm-serve-k8s

Legend: ✅ done · 🔄 in progress · ⬜ not started

---

## Week 1 — Kubernetes fundamentals → first model server

| Day | Topic | Status | Deliverable | Committed |
|----|-------|:------:|-------------|:---------:|
| 0 | Setup (Docker, kubectl, kind `llm`, helm, k9s, folders, git) | ✅ | cluster + folders | — |
| 1 | Architecture & first look (control plane, apply flow, Events) | ✅ | (notes skipped) | — |
| 2 | Pods, ReplicaSets, Deployments (rolling update, rollback) | ✅ | `manifests/hello-deploy.yaml`, `docs/day02-notes.md` | ✅ |
| 3 | Services, networking, DNS (ClusterIP, Endpoints, CoreDNS) | ✅ | `manifests/hello-svc.yaml`, `docs/day03-notes.md` | ✅ |
| 4 | Config, Secrets, Resources (requests/limits, OOMKilled, Pending, QoS) | ✅ | `manifests/config-test.yaml`, `oom-test.yaml`, `too-big.yaml`, `docs/day04-notes.md` | ✅ |
| 5 | Health probes & first LLM server (FastAPI, Docker, kind load, probes) | ✅ | `app/app.py`, `app/Dockerfile`, `manifests/llm-v0.yaml`, `docs/day05-notes.md` | ✅ |
| 6 | Storage & model caching (PVC, cold vs warm start) | ⬜ | `manifests/model-cache.yaml`, `docs/day06-notes.md` | ⬜ |
| 7 | Helm (chart, values, upgrade/rollback) | ⬜ | `charts/llm-serve`, tag `v0.1` | ⬜ |

## Week 2 — Real inference serving, scaling, observability

| Day | Topic | Status | Deliverable | Committed |
|----|-------|:------:|-------------|:---------:|
| 8 | LLM inference fundamentals (reading) | ⬜ | `docs/inference-primer.md` | ⬜ |
| 9 | OpenAI-compatible serving (vLLM-ready chart) | ⬜ | chart w/ engine values, `values-gpu.yaml` | ⬜ |
| 10 | Ingress / Gateway & streaming (SSE) | ⬜ | `charts/.../ingress.yaml`, `docs/day10-notes.md` | ⬜ |
| 11 | Observability 1 — Prometheus (ServiceMonitor, PromQL) | ⬜ | `dashboards/queries.md` | ⬜ |
| 12 | Observability 2 — Grafana & alerts | ⬜ | `dashboards/llm-inference.json` + screenshot | ⬜ |
| 13 | Load testing (concurrency sweep, TTFT, tokens/sec) | ⬜ | `bench/loadtest.py`, `bench/results-cpu.csv`, chart | ⬜ |
| 14 | Autoscaling (KEDA on queue depth) | ⬜ | `ScaledObject`, `docs/scaling-lessons.md`, tag `v0.2` | ⬜ |

## Week 3 — GPUs, production patterns, job-readiness

*(needs a rented GPU Linux VM — RunPod/Lambda/GCP/AWS. Budget $15–40, shut down after each session.)*

| Day | Topic | Status | Deliverable | Committed |
|----|-------|:------:|-------------|:---------:|
| 15 | GPU on Kubernetes (device plugin / GPU Operator) | ⬜ | node allocatable + nvidia-smi pod screenshots | ⬜ |
| 16 | vLLM on a GPU | ⬜ | GPU deployment + Grafana GPU panels | ⬜ |
| 17 | GPU benchmarking (cost per 1M tokens) | ⬜ | `bench/results-gpu.csv`, `docs/benchmark-report.md` | ⬜ |
| 18 | Rollouts, canaries, reliability (PDB, graceful drain) | ⬜ | `docs/runbook.md` | ⬜ |
| 19 | Routing & multi-model (KServe, LoRA, prefix caching) | ⬜ | `docs/architecture.md` | ⬜ |
| 20 | Security, cost, polish (RBAC, NetworkPolicy, CI) | ⬜ | hardened chart, tag `v1.0` | ⬜ |
| 21 | Package for job hunt (README, demo, resume bullets) | ⬜ | final `README.md`, demo video, resume bullets | ⬜ |

---

## Daily checklist (per day)
- [ ] Read the day's whole picture first
- [ ] Ran each step one at a time, understood what/why/where
- [ ] Deliverable written in my own words and committed
- [ ] `docs/journal.md`: 3–5 lines on what broke and what I learned

## Notes
- Branch: `main`. Commits are mine only (no co-author line).
- Cluster: kind `llm`, context `kind-llm`. Restart after reboot:
  Docker Desktop → `docker start llm-control-plane` → `kubectl get nodes`.
