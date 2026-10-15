# Day 6: Storage and model caching

Problem: the container filesystem is ephemeral, so the model re-downloaded on
every Pod restart (the Day 5 cold start). Fix: a PersistentVolumeClaim that
outlives the Pod, so weights download once and persist.

## Storage concepts

- **Ephemeral vs persistent** — a container's filesystem dies with the container;
  `emptyDir` dies with the Pod. A **PVC** outlives the Pod.
- **PV / PVC / StorageClass** (rent-an-apartment analogy):
  - **PV** = the actual storage (real disk/dir).
  - **PVC** = your request for storage; the Pod references this, not the PV.
  - **StorageClass** = the provisioner that auto-creates a PV to satisfy the PVC.
  - Flow: create PVC -> StorageClass provisions a PV -> PVC binds to PV -> Pod
    mounts the PVC.
- kind default class: `standard`, provisioner `rancher.io/local-path`
  (node-local directories), `WaitForFirstConsumer` binding mode -> the PVC stays
  `Pending` (by design, not an error) until a Pod mounts it, so the PV is created
  on the same node the Pod lands on.
- **Init containers** run to completion before the main container — a common
  pattern for pre-fetching weights (not used today; the app downloads into the
  cache itself).

## How the fix wires together

```
HF_HOME=/cache                       # tell HF/transformers to cache here
  -> container writes to /cache
  -> /cache is the mounted volume "cache"   (container volumeMounts)
  -> "cache" is backed by PVC model-cache    (pod-level volumes)
  -> PVC is a persistent disk -> survives Pod deletion
```

Indentation trap: `env` and `volumeMounts` are container-level (aligned with
`ports:`); `volumes` is Pod-level (aligned with `containers:`). The `name: cache`
must match between `volumeMounts` and `volumes`.

## Results (SmolLM2-135M, ~270 MB, CPU)

| Start | Model source | Time to Ready |
|-------|--------------|--------------:|
| Cold (no cache) | downloaded from HuggingFace | **22.0 s** |
| Warm (PVC cache) | read from /cache (PVC) | **8.6 s** |

**~61% reduction.** The ~8.6s that remains = fixed cost (schedule + uvicorn boot
+ torch/transformers import + load weights from disk). The ~13s saved = the
network download, now skipped.

Scaling insight: on a 7B model (~15 GB) the download would be minutes, so caching
turns a multi-minute cold start into load-from-disk seconds — important for
autoscaling (a slow-starting Pod can't react to spikes) and rolling updates.

## Check yourself

- **Why is `ReadWriteOnce` a problem when scaling to many replicas?** RWO mounts
  read-write on **one node** at a time, so replicas spread across nodes can't all
  share one RWO volume. PVC caching only helps restarts on the same node, and
  never the very first download.
- **Other ways to get weights onto a node fast:**
  - Pre-bake weights into the container image (no runtime download).
  - Shared **read-only** volume (ROX / RWX, e.g. NFS) so many replicas read one copy.
  - Node-local caches / pre-pulled images / a model-cache DaemonSet.
  - An init container that fetches weights before the server starts.

## Manifest

`manifests/model-cache.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 5Gi
```

Added to `manifests/llm-v0.yaml`: container `env` (HF_HOME=/cache) +
`volumeMounts` (cache -> /cache), and Pod-level `volumes` (cache -> PVC
model-cache).
