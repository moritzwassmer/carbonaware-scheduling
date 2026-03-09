# Carbon-Aware Scheduling on Kubernetes (kind)

This project runs a Kubernetes-based scheduling experiment that compares two pod placement strategies:

- `carbonaware`: place workload pods on the node mapped to the region with the lowest live carbon intensity.
- `normal`: place workload pods randomly across the mapped nodes.

The scheduler is implemented as a Python + Kopf operator (`scheduler.py`) and runs in-cluster as a pod.

## How It Works

For each scheduled workload:

1. The scheduler fetches carbon intensity values from:
   - `https://wj38sqbq69.execute-api.us-east-1.amazonaws.com/Prod/row`
2. It maps cluster nodes to fixed regions (`DE`, `ERCOT`, `NL`).
3. It selects a target node according to the configured strategy.
4. It creates a pod from `workload.yaml` with required node affinity.
5. It logs both:
   - `Planned` placement (decision time)
   - `Actual` placement (observed by Kopf pod event handlers)

Logs are written inside the scheduler container to:

- `/app/carbonaware_strategy.log`
- `/app/normal_strategy.log`

## Repository Structure

- `scheduler.py`: scheduling logic and Kopf handlers
- `workload.yaml`: template for generated workload pods (sysbench CPU load)
- `rbac.yaml`: service account and cluster-level permissions for the scheduler
- `deployment.yml`: single-cluster run with both strategies (`SCHEDULING_STRATEGY=both`)
- `deployment_carbonaware.yml`: single-strategy run (`carbonaware`)
- `deployment_normal.yml`: single-strategy run (`normal`)
- `kind_conf_3node_1.yml`, `kind_conf_3node_2.yml`: kind cluster configs (3 nodes each)
- `kind_sequential.bat`: helper script for one cluster, sequential strategy execution
- `kind_parallel.bat`: helper script for two clusters, parallel strategy execution
- `dockerfile.Dockerfile`: container image definition for scheduler
- `results/`: example output logs

## Prerequisites

- Docker
- kind
- kubectl
- Windows PowerShell or Command Prompt (batch scripts are provided)

Optional if you want to build and push your own image:

- Docker Hub (or another container registry) access

## Quick Start

### Option A: Single Cluster, Run Both Strategies

1. Create a 3-node kind cluster:

```powershell
kind delete clusters --all
kind create cluster --config .\kind_conf_3node_1.yml --name cluster
```

2. Switch context and deploy RBAC + scheduler:

```powershell
kubectl config use-context kind-cluster
kubectl apply -f .\rbac.yaml
kubectl apply -f .\deployment.yml
```

3. Watch scheduler logs:

```powershell
kubectl logs -f pod/scheduler
```

4. Copy result logs from the pod:

```powershell
kubectl cp scheduler:/app/normal_strategy.log .\results\normal_strategy.log
kubectl cp scheduler:/app/carbonaware_strategy.log .\results\carbonaware_strategy.log
```

### Option B: Two Clusters, Run Strategies in Parallel

1. Create both clusters:

```powershell
kind delete clusters --all
kind create cluster --config .\kind_conf_3node_1.yml --name carbonaware
kind create cluster --config .\kind_conf_3node_2.yml --name normal
```

2. Deploy carbon-aware scheduler:

```powershell
kubectl config use-context kind-carbonaware
kubectl apply -f .\rbac.yaml
kubectl apply -f .\deployment_carbonaware.yml
```

3. Deploy normal scheduler:

```powershell
kubectl config use-context kind-normal
kubectl apply -f .\rbac.yaml
kubectl apply -f .\deployment_normal.yml
```

4. Collect logs from each cluster context.

## Configuration

Scheduler behavior is controlled by environment variables in deployment manifests:

- `NUM_WORKLOADS`: number of workload pods to schedule
- `WORKLOAD_SCHEDULING_PERIOD`: seconds between scheduling attempts
- `SCHEDULING_STRATEGY`: `carbonaware`, `normal`, or `both`

Example from `deployment.yml`:

```yaml
env:
- name: NUM_WORKLOADS
  value: "2"
- name: WORKLOAD_SCHEDULING_PERIOD
  value: "10"
- name: SCHEDULING_STRATEGY
  value: "both"
```

## Building the Scheduler Image

The deployment files currently reference:

- `mowassmer/task4:1.0.2`

To build your own image:

```powershell
docker build -f .\dockerfile.Dockerfile -t <your-registry>/<your-image>:<tag> .
docker push <your-registry>/<your-image>:<tag>
```

Then update `image:` in deployment manifests.

## Validating Experiment Results

Check placement distribution directly in logs:

- Carbon-aware should bias toward the lowest-intensity mapped region.
- Normal should look more evenly random across mapped nodes over time.

Inspect pods by node:

```powershell
kubectl get pods -A -o wide --field-selector spec.nodeName=<node-name>
```

## Important Assumptions and Limitations

- The scheduler expects exactly 3 nodes in the cluster.
- Node-to-region mapping is positional (`list_node()` order), not label-based.
- Control-plane or system pods may appear in logs with `Region: Unknown` and `Intensity: inf`.
- The provided `.bat` scripts contain machine-specific absolute paths; adjust them for your environment.
- This experiment is a prototype for comparison and does not replace the default Kubernetes scheduler globally.

## Troubleshooting

- Scheduler pod not starting:
  - Run `kubectl describe pod scheduler` and check image pull/auth errors.
- No workload pods created:
  - Check `kubectl logs pod/scheduler` for API/network errors.
- Missing permissions:
  - Re-apply `rbac.yaml` and verify service account usage in deployment.
- `kubectl cp` fails:
  - Ensure the pod name matches the manifest (`scheduler` or `scheduler-operator`) for the chosen deployment.

## License

No license file is currently included in this repository.
