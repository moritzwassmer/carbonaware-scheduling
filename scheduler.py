import os
import random
import time
import requests
import yaml
import kopf
import logging
from kubernetes import client, config
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

print("Scheduler is running")
# For debugging purposes
current_time = datetime.now().strftime("%H:%M")
print(f"Current time: {current_time}")

# Load Kubernetes config
config.load_incluster_config()

# Constants
CARBON_API_URL = "https://wj38sqbq69.execute-api.us-east-1.amazonaws.com/Prod/row"
WORKLOAD_TEMPLATE = "workload.yaml"
NUM_WORKLOADS = 2 # TODO set to 180 later

# Configurable environment variable for scheduling period
SCHEDULING_PERIOD = int(os.getenv("WORKLOAD_SCHEDULING_PERIOD", 10))

# Node-region mapping
NODE_REGION_MAPPING = {
    "kind-worker": "DE",
    "kind-worker2": "ERCOT",
    "kind-worker3": "NL",
}

# Load workload template
def load_workload_template():
    with open(WORKLOAD_TEMPLATE, "r") as file:
        return yaml.safe_load(file)

# Fetch carbon intensity data
def fetch_carbon_intensity(): # e.g. {"DE": 476.86, "ERCOT": 288.29, "NL": 266.5}
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
    return best_node, lowest_intensity

# Schedule workload to Kubernetes
def schedule_workload(api, pod_spec, node, intensity, region):
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
    logging.info(f"%s, SUG, %.2f, %s", unique_name, intensity, region)

# Monitor pod placement
def monitor_pod_placement(event, **kwargs):
    pod = event.get("object")
    pod_name = pod.metadata.name
    node_name = pod.spec.node_name
    region = NODE_REGION_MAPPING.get(node_name, "Unknown")
    intensity = fetch_carbon_intensity().get(region, float("inf"))
    print(f"Pod {pod_name} placed on node {node_name}")
    logging.info(f"%s, ACT, %.2f, %s", pod_name, intensity, region)

# Main loop
def main():
    api = client.CoreV1Api()
    pod_template = load_workload_template()

    for i in range(NUM_WORKLOADS):
        print(f"Workload {i+1}/{NUM_WORKLOADS}")
        print("Fetching carbon intensity data...")
        carbon_data = fetch_carbon_intensity()
        if not carbon_data:
            print("Skipping scheduling due to missing data.")
            time.sleep(SCHEDULING_PERIOD)
            continue

        print("Selecting the best node...")
        best_node, lowest_intensity = select_best_node(carbon_data)
        if not best_node:
            print("No suitable node found. Skipping scheduling.")
            time.sleep(SCHEDULING_PERIOD)
            continue

        region = NODE_REGION_MAPPING[best_node]
        print(f"Best node selected: {best_node}")
        schedule_workload(api, pod_template, best_node, lowest_intensity, region)
        print("\n")
        time.sleep(SCHEDULING_PERIOD)


    # Wait for the last pod placement to occur, keep pod alive to be able to kubectl cp logs, 
    # copy like kubectl cp scheduler-job-jgqrv:/app/scheduler.log results/scheduler.log
    time.sleep(3600) # 1 hour
    sys.exit(0)

# Kopf handler for observing pod placement
@kopf.on.event("", "v1", "pods")
def observe_placement(event, **kwargs):
    if event["type"] == "ADDED":
        monitor_pod_placement(event, **kwargs)

if __name__ == "__main__":
    main()
