import os
import random
import time
import requests
import yaml
import kopf
from kubernetes import client, config

# Load Kubernetes config
#config.load_kube_config()
#config.load_incluster_config()

# Load the admin kubeconfig file
KUBECONFIG_PATH = os.getenv("KUBECONFIG", "~/.kube/config")  # Default path to kubeconfig
config.load_kube_config(config_file=os.path.expanduser(KUBECONFIG_PATH))
print(f"Using kubeconfig from: {KUBECONFIG_PATH}")

# Constants
CARBON_API_URL = "https://wj38sqbq69.execute-api.us-east-1.amazonaws.com/Prod/row"
WORKLOAD_TEMPLATE = "workload.yaml"

# Configurable environment variable for scheduling period
SCHEDULING_PERIOD = int(os.getenv("WORKLOAD_SCHEDULING_PERIOD", 60))

# Node-region mapping
NODE_REGION_MAPPING = {
    "node-1": "DE", # region-a
    "node-2": "ERCOT",
    "node-3": "NL",
}

# Load workload template
def load_workload_template():
    with open(WORKLOAD_TEMPLATE, "r") as file:
        return yaml.safe_load(file)

# Fetch carbon intensity data
def fetch_carbon_intensity():
    try:
        response = requests.get(CARBON_API_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching carbon intensity: {e}")
        return None

# Select the best node based on carbon intensity
def select_best_node(carbon_data):
    best_node = None
    lowest_intensity = float("inf")
    for node, region in NODE_REGION_MAPPING.items():
        intensity = carbon_data.get(region, float("inf"))
        if intensity < lowest_intensity:
            lowest_intensity = intensity
            best_node = node
    return best_node

# Schedule workload to Kubernetes
def schedule_workload(api, pod_spec, node):
    unique_name = f"workload-{int(time.time())}"
    pod_spec["metadata"]["name"] = unique_name
    pod_spec["spec"]["affinity"] = {
        "nodeAffinity": {
            "requiredDuringSchedulingIgnoredDuringExecution": {
                "nodeSelectorTerms": [
                    {
                        "matchExpressions": [
                            {
                                "key": "kubernetes.io/hostname",
                                "operator": "In",
                                "values": [node],
                            }
                        ]
                    }
                ]
            }
        }
    }
    api.create_namespaced_pod(namespace="default", body=pod_spec)
    print(f"Scheduled workload: {unique_name} to node: {node}")

# Monitor pod placement
def monitor_pod_placement(event, **kwargs):
    pod = event.get("object")
    pod_name = pod.metadata.name
    node_name = pod.spec.node_name
    print(f"Pod {pod_name} placed on node {node_name}")

# Main loop
def main():
    api = client.CoreV1Api()
    pod_template = load_workload_template()
    
    while True:
        print("Fetching carbon intensity data...")
        carbon_data = fetch_carbon_intensity()
        if not carbon_data:
            print("Skipping scheduling due to missing data.")
            time.sleep(SCHEDULING_PERIOD)
            continue

        print("Selecting the best node...")
        best_node = select_best_node(carbon_data)
        if not best_node:
            print("No suitable node found. Skipping scheduling.")
            time.sleep(SCHEDULING_PERIOD)
            continue

        print(f"Best node selected: {best_node}")
        schedule_workload(api, pod_template, best_node)
        time.sleep(SCHEDULING_PERIOD)

# Kopf handler for observing pod placement
@kopf.on.event("", "v1", "pods")
def observe_placement(event, **kwargs):
    if event["type"] == "ADDED":
        monitor_pod_placement(event, **kwargs)

if __name__ == "__main__":
    main()
