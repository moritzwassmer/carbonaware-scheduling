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

# Create a dedicated write_logger
write_logger = logging.getLogger("scheduler")
write_logger.setLevel(logging.INFO)

# Create file and stream handlers
file_handler = logging.FileHandler("scheduler.log")
stream_handler = logging.StreamHandler(sys.stdout)

# Set formatter and add handlers to the write_logger
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

write_logger.addHandler(file_handler)
write_logger.addHandler(stream_handler)

logging.info("Scheduler is starting...")
# For debugging purposes
current_time = datetime.now().strftime("%H:%M")
logging.info(f"Current time: {current_time}")

# Load Kubernetes config
config.load_incluster_config()

# Constants
CARBON_API_URL = "https://wj38sqbq69.execute-api.us-east-1.amazonaws.com/Prod/row"
WORKLOAD_TEMPLATE = "workload.yaml"
NUM_WORKLOADS = 2  # TODO set to 180 later

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
def fetch_carbon_intensity():  # e.g., {"DE": 476.86, "ERCOT": 288.29, "NL": 266.5}
    try:
        response = requests.get(CARBON_API_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching carbon intensity: {e}")
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
    write_logger.info(f"Pod: {unique_name} to node: {node}, Intensity: {intensity}, Region: {region}, Type: Planned")

# Monitor pod placement
def monitor_pod_placement(workload_name, node_name):
    #logging.info("124421415241213")
    region = NODE_REGION_MAPPING.get(node_name, "Unknown")
    intensity = fetch_carbon_intensity().get(region, float("inf"))
    write_logger.info(f"Pod: {workload_name}, Node: {node_name}, Intensity: {intensity}, Region: {region}, Type: Actual")

# Main loop
def main():
    time.sleep(10)
    api = client.CoreV1Api()
    pod_template = load_workload_template()

    for i in range(NUM_WORKLOADS):
        logging.info(f"Scheduling workload {i + 1}/{NUM_WORKLOADS}")
        carbon_data = fetch_carbon_intensity()
        if not carbon_data:
            logging.info("Skipping scheduling due to missing carbon intensity data.")
            time.sleep(SCHEDULING_PERIOD)
            continue

        best_node, lowest_intensity = select_best_node(carbon_data)
        if not best_node:
            logging.info("No suitable node found. Skipping scheduling.")
            time.sleep(SCHEDULING_PERIOD)
            continue

        region = NODE_REGION_MAPPING[best_node]
        logging.info(f"Best node selected: {best_node}")
        schedule_workload(api, pod_template, best_node, lowest_intensity, region)
        time.sleep(SCHEDULING_PERIOD)

    # Wait for the last pod placement to occur, keep pod alive to allow log access
    logging.info("All workloads scheduled. Waiting to allow log retrieval...")
    time.sleep(3600)  # 1 hour
    sys.exit(0)

# Kopf handler for observing pod placement
@kopf.on.event("", "v1", "pods")
def observe_placement(event, **kwargs): # TODO Issue here
    #logging.info("124421415241213, \n"+str(event)+"\n"+str(kwargs))

    # get pod name and node name
    # Ensure the event has the expected structure
    if not isinstance(event, dict) or 'object' not in event or 'kind' not in event['object']:
        logging.error("Invalid event format")
        return

    obj = event['object']
    
    # Check if the object is a Pod
    if obj['kind'] == 'Pod':
        # Extract the workload name and nodeName if available
        workload_name = obj.get('metadata', {}).get('name', None)
        node_name = obj.get('spec', {}).get('nodeName', None)
        
        if workload_name and node_name:
            logging.info(f"Workload Name: {workload_name}, Node Name: {node_name}")
        else:
            logging.error("Could not extract workload name or node name")
            return
    else:
        logging.info(f"Unhandled kind: {obj['kind']}")

    monitor_pod_placement(workload_name, node_name)
    """if event["type"] == "ADDED":
        monitor_pod_placement(event, **kwargs)"""

# Kopf resume/create handler
@kopf.on.resume("", "v1", "pods")
@kopf.on.create("", "v1", "pods")
def on_pod_resume(name, namespace, labels, logger, **kwargs):
    # Check if this is the scheduler pod
    if labels.get("application") == "kopfexample-operator":
        main()
