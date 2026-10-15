# Day 7: Helm

Packaged the hand-written `llm-v0` manifests into a reusable Helm chart so settings
live in one `values.yaml` instead of hardcoded YAML. This is how the project ships
from here (and sets up Day 9's "same chart, two engines").

## Concepts

- **Chart** = `templates/` (YAML with `{{ }}` placeholders) + `values.yaml` (defaults).
  Helm *renders* templates with values -> plain Kubernetes YAML -> applies it.
- **Release** = an installed chart instance, with a name (`helm install llm ...`)
  and a revision history.
- **Values override defaults** at install/upgrade time: `--set key=val` or `-f file`.
  No file edit needed. This is what lets one chart run many configs.

## Templating used

- `{{ .Values.x }}` — pull from values.yaml (nested: `.Values.image.repository`).
- `{{ .Release.Name }}` — built-in: the release name at install time. Used for all
  object names and the `app:` label/selector, so they always render to the same
  string and the label glue stays correct.
- `{{ ... | quote }}` — pipe a value through a function; `quote` wraps it in quotes
  (needed for `1Gi`, `500m`, `5Gi` so YAML treats them as strings).
- Rule: templatize only what varies (replicas, image, resources). Keep constants
  hardcoded (probe paths, HF_HOME, mountPath) so the chart stays readable.

## Workflow commands

```bash
helm create charts\llm-serve          # scaffold (then trim samples)
helm lint charts\llm-serve            # structural check
helm template llm charts\llm-serve    # render to YAML WITHOUT installing (#1 debug tool)
helm install llm charts\llm-serve     # render + apply -> a release
helm upgrade llm charts\llm-serve --set replicas=2   # new revision
helm history llm                      # per-release revision ledger
helm rollback llm 1                   # revert whole release to a revision
helm list                             # releases + current revision/status
```

`helm upgrade`/`rollback` are to a whole app what `kubectl rollout`/`undo` were to
one Deployment.

## Observed

- `helm template` rendered `.Release.Name` -> `llm`, PVC -> `llm-cache`, image ->
  `llm-v0:0.1`, replicas -> 1, resources/storage substituted and quoted. Verified
  everything before touching the cluster.
- `helm install llm` created Deployment `llm`, Service `llm`, PVC `llm-cache`;
  release showed REVISION 1, STATUS deployed.
- `helm upgrade --set replicas=2` -> REVISION 2, a 2nd Pod appeared (no file edit).
- `helm rollback llm 1` -> back to 1 Pod. History showed revisions 1 (superseded),
  2 (superseded), 3 (deployed, "Rollback to 1"). A rollback creates a NEW revision
  that copies the target's state; history only grows forward.

## Gotchas

- `helm` not on PowerShell PATH (stale PATH; winget install). Fix: append the
  winget package dir for the session, or fully restart VS Code.
- Helm installed is v4.3.0 (newer than the course's v3); the commands used are
  identical.
- Lint failed with "unpacking subchart llm-serve ... Chart.yaml missing" because a
  stray nested copy `charts/llm-serve/charts/llm-serve/` existed. Anything under a
  chart's `charts/` dir is treated as a subchart; removing the stray folder fixed it.

## Check yourself

- **What does `helm template` do that `install` doesn't?** Renders the final YAML
  locally and prints it WITHOUT applying to the cluster — safe inspection/debugging.
- **Why are values better than editing YAML?** One place to configure; the same
  templates serve many configs via overrides; changes are tracked as versioned,
  reversible release revisions.

## Cleanup note

The old raw `model-cache` PVC (from Day 6) is now orphaned (raw llm-v0 Deployment
deleted). Harmless; can remove with `kubectl delete pvc model-cache`.

Tagged `v0.1` — end of Week 1.
