# Day 2: Pods, ReplicaSets, Deployments

## Topics

- **Pod** — the smallest unit Kubernetes schedules; a wrapper around one or more
  containers that share a network (IP) and storage. Pods are **disposable**:
  when something is wrong they are deleted and replaced, never repaired. Their
  name and IP are temporary and change on every replacement.

- **Labels & selectors** — key/value tags (e.g. `app: hello`) that let objects
  find each other loosely. A **label** is a tag you put *on* an object; a
  **selector** is a query that finds objects *by* their labels. This is the
  "glue": controllers and Services track a changing set of Pods by label, not by
  name/IP. Two sides of one wire — the producer side stamps the tag on, the
  consumer side searches for it, and they must use the same string.

- **ReplicaSet** — runs the control loop "keep exactly N Pods matching my
  selector alive." Delete a Pod and it notices actual < desired and creates a
  replacement. You rarely create one directly; a Deployment creates it for you.

- **Deployment** — sits on top of ReplicaSets. It keeps N Pods alive (via the
  ReplicaSet) *and* adds safe updates and rollbacks. Ownership chain:
  **Deployment → ReplicaSet → Pods**. On an update it creates a *new* ReplicaSet
  and gradually shifts Pods from the old one to the new one.

- **Rolling update knobs**
  - `maxSurge` — how many extra Pods above the desired count are allowed during
    an update (`1` = may briefly run N+1).
  - `maxUnavailable` — how many Pods may be missing during an update (`0` = never
    drop below N ready; a new Pod must become Ready before an old one is removed).
  - Together, `maxSurge: 1` + `maxUnavailable: 0` = add one new, wait until it is
    Ready, then remove one old. Zero-downtime.

- **LLM angle** — a vLLM Pod can take minutes to load weights before it is Ready.
  With `maxUnavailable: 0` the slow new Pod must finish loading before any old Pod
  is killed, so capacity never drops. Revisited on Day 18.

## What I observed

1. **ReplicaSets during the update** — the Deployment created a second
   ReplicaSet (new `pod-template-hash`) for the new image, scaled it up to 3 one
   Pod at a time while scaling the old ReplicaSet down to 0. The old ReplicaSet
   was **kept at 0, not deleted** — that is what makes `rollout undo` instant.

2. **`maxSurge: 1` / `maxUnavailable: 0`** — each new Pod reached `1/1 Running`
   *before* any old Pod started `Terminating`. Never fewer than 3 ready Pods, at
   most one extra at a time. Zero dropped traffic.

3. **Replaced, not repaired** — deleting a Pod produced a brand-new Pod with a
   different name/IP within ~1s, created by the ReplicaSet loop. The old Pod was
   discarded; Kubernetes never "fixes" a Pod in place.

4. **Traffic stayed safe during the bad rollout** — setting a non-existent image
   (`nginx:does-not-exist`) left the new Pod stuck in `ErrImagePull` /
   `ImagePullBackOff`. Because it never became Ready and `maxUnavailable: 0`, all
   3 old Pods kept running and serving. `rollout undo` restored the previous good
   ReplicaSet instantly.

5. **Selector must match template labels** — changing only the template label to
   `app: broken` while the selector stayed `app: hello` was rejected by the API
   server before anything changed:
   `` `selector` does not match template `labels` ``.

## The manifest

`manifests/hello-deploy.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hello
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: hello
    spec:
      containers:
        - name: web
          image: nginx:1.25
          ports:
            - containerPort: 80
```

## Key commands

```bash
kubectl apply -f manifests\hello-deploy.yaml      # declare desired state
kubectl get deploy,rs,pods -o wide                # see the ownership chain
kubectl delete pod <name>                         # prove self-healing
kubectl scale deployment hello --replicas=5       # change desired count
kubectl set image deployment/hello web=nginx:1.26 # rolling update
kubectl rollout status deployment/hello           # wait for / check a rollout
kubectl rollout history deployment/hello          # list revisions
kubectl rollout undo deployment/hello             # roll back one revision
```
