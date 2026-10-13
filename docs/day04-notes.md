# Day 4: Config, Secrets, and Resources

The most important day for inference stability: getting `requests`/`limits`
wrong is the #1 cause of broken LLM deployments.

## ConfigMap vs Secret

- **ConfigMap** — non-secret settings as key/value (e.g. `MODEL_NAME`,
  `MAX_TOKENS`). Stored in plain text. Separates config from the image so one
  generic image can be reconfigured without a rebuild.
- **Secret** — same structure, for sensitive values (e.g. `HF_TOKEN`). Stored
  only **base64-encoded, NOT encrypted**. Confirmed by decoding
  `ZHVtbXktdmFsdWUtZm9yLW5vdw==` back to `dummy-value-for-now` in one command.
- Real protection for Secrets:
  - **RBAC** — only authorized identities (e.g. the inference Pod's
    ServiceAccount) can read the Secret via the API.
  - **Encryption at rest** — encrypt Secret data in etcd so raw disk/backups are
    useless.
  - **External secret stores** (Vault, cloud secret managers) — keep the real
    value out of the cluster entirely.
  - **Never** bake secrets into the image at build time — inject at runtime.

### Two injection styles (both used in config-test.yaml)

- `envFrom: configMapRef` — bulk import **every** key of a ConfigMap as env vars.
- `env: ... valueFrom: secretKeyRef` — pull **one** named key from a Secret.
  Kubernetes auto-decodes the base64 so the app sees plaintext (`os.getenv`).

## requests vs limits (the core of the day)

- **`requests`** = what the **scheduler reserves**. "I need at least this much."
  Used for **placement** (compared against a node's Allocatable).
- **`limits`** = the **hard ceiling** enforced by the **Linux kernel** at runtime.

Two different components, two different numbers: **scheduler -> requests,
kernel -> limits.**

Consequences of exceeding a limit differ by resource:
- **Memory over limit -> `OOMKilled`** (memory can't be compressed, so the
  container is killed). Exit code **137** (= 128 + 9/SIGKILL). Repeated crashes
  -> `CrashLoopBackOff`.
- **CPU over limit -> throttled** (sliced, not killed). Shows up as latency.

Scheduling failure (separate from limits):
- **`requests` bigger than any node's Allocatable -> Pod stuck `Pending`** with
  `FailedScheduling: Insufficient <resource>`. Same shape as requesting a GPU no
  node has.

## QoS classes (eviction order under memory pressure)

Derived automatically from requests/limits:
- **Guaranteed** — every container sets requests AND limits for BOTH cpu & memory,
  with request == limit. Killed last.
- **Burstable** — not Guaranteed, but at least one request/limit is set (e.g.
  request set with a higher limit, or request but no limit). Middle priority.
- **BestEffort** — nothing set anywhere. Killed first.

## Two failure signatures (interview gold)

| | OOMKilled (oom-test) | Pending (too-big) |
|---|---|---|
| `Node:` | assigned | `<none>` |
| `PodScheduled` | True | **False** |
| Status | Terminated, restarts climbing | **Pending** forever, 0 restarts |
| Who complains | kubelet / kernel | **scheduler** |
| Event | `BackOff` / `OOMKilled`, exit 137 | `FailedScheduling: Insufficient memory` |
| Root cause | **limit** too low for actual usage | **request** bigger than any node |
| Fix | raise `limits.memory` / use less | lower `requests` / add capacity |

## Observed

- `oom-test` (requests 50Mi, limits 100Mi, stress grabs 300M): `Reason: OOMKilled`,
  `Exit Code: 137`, `Restart Count` climbing, `BackOff` events. `PodScheduled: True`
  (placed fine; died at runtime). QoS: Burstable.
- `too-big` (requests 500Gi): `Status: Pending`, `Node: <none>`, no IP,
  `PodScheduled: False`, Event `FailedScheduling: 0/1 nodes are available:
  1 Insufficient memory`. Scheduler never placed it.

## LLM relevance

- A model needing more RAM than `limits.memory` dies exactly like oom-test
  (exit 137, CrashLoopBackOff). Set limits above the real footprint, with headroom
  for the KV cache (grows with concurrency).
- A GPU Pod on a cluster with no GPU node sits Pending like too-big — same debug
  path: describe pod (Events), describe node (Allocatable), check taints/selectors.

## Check yourself

- **Pod is Pending, how to find why?** `kubectl describe pod` -> Events
  (`FailedScheduling`), then `kubectl describe node` -> Allocatable.
- **Pod is OOMKilled, what to change?** Raise `limits.memory` (or reduce the
  workload's memory use); confirm with the container's `Last State` / exit 137.
