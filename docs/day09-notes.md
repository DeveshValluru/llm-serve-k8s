# Day 9: OpenAI-compatible serving (engine-swappable chart)

Goal: make the Helm chart engine-agnostic so ONE chart serves many engines — a CPU
FastAPI server on kind now, and vLLM on GPU later (Day 16) — differing only in a
values file.

## The idea

```
values.yaml  (engine: image/args/port/probe-paths + gpu toggle + env)
      │
      ├─ helm template/install -f values-local.yaml → FastAPI llm-v0:0.1 (CPU, kind)
      └─ helm template/install -f values-gpu.yaml   → vllm/vllm-openai (GPU, minikube, Day 16)
      (same templates — only the values differ)
```

## Chart changes

- `values.yaml`: added `engine` (image, pullPolicy, args, port, startupPath,
  livenessPath, readinessPath), `gpu` (enabled, count), and `env` (extra vars).
- `deployment.yaml`: reads all of the above. Conditionals:
  - `{{- with .Values.engine.args }}` — render `args:` only if non-empty.
  - `{{- if .Values.gpu.enabled }}` — add `nvidia.com/gpu: N` to limits only on GPU.
  - `{{- with .Values.env }}` — append extra env (e.g. HF_TOKEN) after HF_HOME.
- `service.yaml`: `targetPort` now `{{ .Values.engine.port }}`.
- `values-local.yaml` / `values-gpu.yaml`: the two engine profiles.

Key insight: different engines have different health endpoints (FastAPI: /ready +
/healthz; vLLM: /health), so the probe PATHS must be values too — not just the image.

## OpenAI-compatible API (why engines standardize on it)

Production engines (vLLM, TGI, llama.cpp, SGLang) expose `/v1/models`,
`/v1/chat/completions` (supports `stream: true`), `/v1/completions`. Any OpenAI
client works by pointing base_url at the server — no custom client needed.

## vLLM flags (in values-gpu.yaml)

- `--model` — which model (HF repo/path).
- `--max-model-len` — max context (prompt+output). Bigger => larger per-request KV
  cache => fewer concurrent requests fit.
- `--gpu-memory-utilization` (0.90) — fraction of VRAM vLLM may use; higher = more
  KV-cache room/concurrency, but leave headroom or risk OOM.
- `--max-num-seqs` — max concurrently batched sequences (continuous-batching width).
- `--tensor-parallel-size` — split one model across N GPUs (1 for single GPU).

## Validation

`helm template -f values-local.yaml` vs `-f values-gpu.yaml` rendered two very
different Deployments from one chart:
- local: image llm-v0:0.1, no args, readiness /ready, limits memory only, env HF_HOME.
- gpu: image vllm/vllm-openai, vLLM args, readiness /health, limits + nvidia.com/gpu:1,
  env HF_HOME + HF_TOKEN (from secret), 4Gi/2CPU requests.

## GPU plan note

kind can't give its node a GPU on Windows/WSL2 (no `--gpus` for the node, runtime
doesn't auto-inject). Days 9-14 stay on kind/CPU; GPU days (15-17) will use minikube
`--gpus all` with the local RTX 4060. All charts/manifests transfer unchanged.
values-gpu.yaml still needs (Day 16): an hf-token Secret and a memory-backed
/dev/shm volume.

## Check yourself

- **Why does `--gpu-memory-utilization` matter?** It sets how much VRAM vLLM uses
  for weights + KV cache; higher packs more concurrent requests but risks OOM.
- **What happens if `--max-model-len` is huge?** Each request reserves a bigger KV
  cache, so far fewer requests fit concurrently (lower throughput/concurrency).
