# Day 5: Health probes and first LLM server

First real inference server in the cluster: a FastAPI app loading SmolLM2-135M,
packaged with Docker, run by Kubernetes with three probes.

## The three layers (and how they connect)

- **FastAPI (`app/app.py`)** — the app. Loads the model once at startup, exposes
  `/healthz` (process alive), `/ready` (model loaded? 503 while loading, 200 after),
  and `/generate` (inference). The health endpoints exist specifically so
  Kubernetes probes have something meaningful to poll.
- **Docker (`app/Dockerfile`)** — the package. Bundles Python + fastapi/uvicorn/
  transformers/torch (CPU build via `--extra-index-url .../whl/cpu`) + `app.py`,
  and starts `uvicorn app:app --host 0.0.0.0 --port 8000`. Runs identically anywhere.
- **Kubernetes (`manifests/llm-v0.yaml`)** — the operator. Runs the image as a
  Deployment, probes the endpoints to track health, exposes it via a Service.

## The three probes

- **Startup** (`/healthz`, period 5s, failureThreshold 60 = 5 min grace) — runs
  first; liveness/readiness are suspended until it passes once. Absorbs the early
  "connection refused" while uvicorn + torch are still importing.
- **Readiness** (`/ready`, period 5s) — gates traffic. While `/ready` returns 503,
  the Pod is kept OUT of the Service Endpoints (stays `0/1`). When it returns 200,
  the Pod joins Endpoints (`1/1`). Does NOT restart the Pod.
- **Liveness** (`/healthz`, period 10s) — restarts the Pod only if it wedges after
  startup.

Why startup probe instead of a long liveness `initialDelaySeconds`: a fixed delay
is a bad guess either way (too short kills slow starts; too long leaves a dead
container unrestarted). Startup probe is adaptive: lots of patience during startup,
then fast liveness checks for the rest of the Pod's life.

## Control plane vs data plane (how requests actually work)

- Kubernetes **keeps things alive and routes** (control plane): starts/restarts
  Pods, probes health, maintains Endpoints, sets up kube-proxy routing rules.
- The **request itself** (data plane) goes: client -> Service virtual IP ->
  kube-proxy rule picks a Ready Pod -> Pod:8000 -> uvicorn -> FastAPI `/generate`
  -> `model.generate()`. The actual inference work happens **inside the app**;
  the API server/scheduler/controllers are NOT in the request path.
- Implication: Kubernetes doesn't know about tokens/TTFT/queue-depth — those live
  in the app. That's why inference metrics come from the app (Day 11) and why CPU
  is a poor autoscaling signal (Day 14).

## Build + load workflow (kind)

```bash
docker build -t llm-v0:0.1 app            # build image (slow: pulls torch)
kind load docker-image llm-v0:0.1 --name llm   # copy image into the kind node
```

- kind can't see laptop Docker images; must load them in. `imagePullPolicy:
  IfNotPresent` then makes Kubernetes use the loaded image instead of pulling from
  a registry (confirmed by event "already present on machine").
- Use a specific tag (`:0.1`), never `latest`.

## Observed

- Pod reached `1/1 Running`; cold start ~25-30s (process boot + model download +
  load). `describe` showed `Startup probe failed: connection refused (x5)` during
  boot — the startup probe absorbing the window before uvicorn was listening.
- QoS: Burstable (memory request 1Gi != limit 2Gi; CPU request only).
- `/generate` with prompt "Kubernetes is", max_new_tokens 30 returned coherent
  text in ~1.49s (CPU inference on a 135M model).

## Gotchas hit

- kind not on PowerShell PATH (stale PATH from a session opened before winget
  installed it). Fix: reopen the shell / fully restart VS Code, or append the
  winget package dir to `$env:PATH` for the session.
- PowerShell mangles escaped double quotes for `curl.exe`. Fix: wrap the JSON body
  in single quotes: `-d '{"prompt":"...","max_new_tokens":30}'`.

## Check yourself

- **Why a startup probe not just a long liveness delay?** Adaptive vs fixed guess;
  gives startup as much time as needed, then fast liveness for the rest of life.
- **What happens if readiness fails after startup?** Pod is removed from Service
  Endpoints (no traffic) but NOT restarted; it rejoins when readiness passes again.
