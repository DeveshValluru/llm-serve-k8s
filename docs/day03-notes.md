# Day 3: Services, networking, DNS

## The problem

Every Pod has its own IP, and that IP changes every time the Pod is replaced
(confirmed today: the Pods that were `.6/.7/.8` on Day 2 came back as
`.16/.17/.18`). So no client can target Pods by IP. A **Service** gives one
stable name + virtual IP that load-balances across whatever Pods are alive.

## The request chain

```
client → Service (stable name/IP) → Endpoints (live list of Ready Pod IPs) → a Pod
```

- **Service** — stable front door. Finds its Pods by label `selector` (`app: hello`,
  the same label the ReplicaSet uses). Has a virtual `CLUSTER-IP` (e.g.
  `10.96.134.164`) in a different range from Pod IPs (`10.244.x.x`); the virtual
  IP never changes for the life of the Service.
- **Endpoints** — the auto-maintained address book of current Pod IPs behind the
  Service. A controller watches for Ready Pods matching the selector and keeps
  this list in sync. (Being deprecated in favor of `EndpointSlice` /
  `discovery.k8s.io/v1` for scalability — same idea, chunked for large Services.)
- **CoreDNS** — gives each Service a DNS name so apps use names, not IPs.
- **kube-proxy** — on each node, implements the routing: intercepts the virtual
  IP and forwards to one of the endpoint Pod IPs.

## Service types

- **ClusterIP** (default) — internal only. Used today; what internal backends
  (like the LLM service) use.
- **NodePort** — opens a port on every node's IP for external access. Crude.
- **LoadBalancer** — cloud provisions an external LB + public IP. Doesn't fully
  work on kind (no cloud); Day 10's Ingress is the local answer for external access.

## DNS name format

```
hello.default.svc.cluster.local
└┬──┘ └┬────┘ └┬┘ └┬──────────┘
 svc   ns   "service"  cluster suffix
```

From a Pod in the **same namespace**, the short name `hello` resolves via CoreDNS.
This is how services call each other, e.g. a client doing
`http://llm-v0/v1/chat/completions`.

## What I observed

1. **Endpoints == Pod IPs** — the Service's endpoints (`.16/.17/.18:80`) matched
   the three Pod IPs exactly. `:80` is the `targetPort`.
2. **From the laptop (Step 3)** — a ClusterIP Service is not directly reachable, so
   `kubectl port-forward svc/hello 8080:80` tunnels in; `curl localhost:8080`
   returned the nginx page. The whole chain worked without ever touching a Pod IP.
3. **From inside the cluster (Step 4)** — a throwaway Pod ran `curl http://hello`
   (name only). CoreDNS resolved it; no tunnel, no IP needed. This is how real
   apps call the service.
4. **Self-healing routing (Step 5)** — deleting a Pod removed its IP (`.16`) from
   the Endpoints list and the replacement's new IP (`.20`) appeared automatically.
   Still 3 endpoints; the Service name/IP never changed. A client would not notice.

## Two layers of self-healing (so far)

- Day 2: ReplicaSet heals the **Pods** (keeps N alive).
- Day 3: Endpoints controller heals the **routing** (keeps the address book
  pointing only at live, Ready Pods).

## The manifest

`manifests/hello-svc.yaml`:

```yaml
apiVersion: v1          # Service is a core object -> v1 (NOT apps/v1)
kind: Service
metadata:
  name: hello
spec:
  selector:
    app: hello          # route to Pods with this label
  ports:
    - port: 80          # port the Service listens on
      targetPort: 80    # port on the Pod to forward to
  # no `type:` -> defaults to ClusterIP (internal only)
```

## Key commands

```bash
kubectl apply -f manifests\hello-svc.yaml
kubectl get svc hello                 # TYPE, CLUSTER-IP, PORT(S)
kubectl get endpoints hello           # live list of backing Pod IPs
kubectl port-forward svc/hello 8080:80           # tunnel from laptop (test)
kubectl run curl-test --image=curlimages/curl --restart=Never -it --rm -- curl -s http://hello
```

## Check yourself

- **Why can't clients use Pod IPs directly?** They change on every Pod
  replacement (and there are many Pods); you'd be pointing at a dead/wrong target.
- **What fills the Endpoints list?** A controller that watches for Ready Pods
  matching the Service's selector and writes their current IPs in.
