import os
import random
import time
import requests
import yaml
import kopf
import logging
from kubernetes import client, config
import sys


logging.info("Scheduler is starting...")

# Load Kubernetes config
config.load_incluster_config()

# Constants
CARBON_API_URL = "https://wj38sqbq69.execute-api.us-east-1.amazonaws.com/Prod/row"
WORKLOAD_TEMPLATE = "workload.yaml"

# Get environment variables
NUM_WORKLOADS = int(os.getenv("NUM_WORKLOADS", 2))  # TODO set to 180 later
SCHEDULING_PERIOD = int(os.getenv("WORKLOAD_SCHEDULING_PERIOD", 10))
STRATEGY = str(os.getenv("SCHEDULING_STRATEGY", "both"))

# Get k8s nodes in Cluster
k8s_api = client.CoreV1Api()
logging.info("Getting k8s nodes...")
response = k8s_api.list_node()
names = [item.metadata.name for item in response.items]
logging.info("Got nodes: "+str(names))
if len(names) != 3:
    logging.error("Too many or too few nodes in cluster to apply the mapping. Expected 3 nodes but got"+str(len(names)))
NODE_REGION_MAPPING = {
    names[0]: "DE",
    names[1]: "ERCOT",
    names[2]: "NL",
}

# Create loggers for carbonaware and normal strategy
def create_logger(strategy):
    # Create a logger that writes results
    write_logger = logging.getLogger(strategy)
    write_logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(strategy+"_strategy.log")
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    write_logger.addHandler(file_handler)
    write_logger.addHandler(stream_handler)
    return write_logger
carbonaware_logger = create_logger("carbonaware")
normal_logger = create_logger("normal")

# Load workload template
def load_workload_template():
    with open(WORKLOAD_TEMPLATE, "r") as file:
        return yaml.safe_load(file)

# Fetch carbon intensity data
def fetch_carbon_intensity():  
    try:
        response = requests.get(CARBON_API_URL, timeout=10)
        response.raise_for_status()
        return response.json() # e.g., {"DE": 476.86, "ERCOT": 288.29, "NL": 266.5}
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

# select node randomly
def random_placement(carbon_data):
    node = random.choice(list(NODE_REGION_MAPPING.keys()))
    region = NODE_REGION_MAPPING[node]
    intensity = carbon_data.get(region, float("inf"))
    return node, intensity

# Schedule workload to Kubernetes
def schedule_workload(api, pod_spec, node, intensity, region, strategy):
    unique_name = f"workload-{int(time.time())}"
    pod_spec["metadata"]["name"] = unique_name
    pod_spec["metadata"]["labels"]["strategy"] = strategy  # Add label
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
    log_pod_placement(unique_name, node, intensity, region, "Planned", strategy)

def log_pod_placement(workload_name, node_name, intensity, region, type, strategy):
    if strategy == "carbonaware":
        carbonaware_logger.info(f"Pod: {workload_name}, Node: {node_name}, Intensity: {intensity}, Region: {region}, Type: {type}")
    elif strategy == "normal":
        normal_logger.info(f"Pod: {workload_name}, Node: {node_name}, Intensity: {intensity}, Region: {region}, Type: {type}")
    else:
        logging.error("Invalid scheduling strategy. Skipping logging.")

def run_experiment(api, strategy, pod_template):

    for i in range(NUM_WORKLOADS):
        logging.info(f"Scheduling workload {i + 1}/{NUM_WORKLOADS}")

        # Fetch carbon intensity data
        carbon_data = fetch_carbon_intensity()
        if not carbon_data:
            logging.error("Skipping scheduling due to missing carbon intensity data.")
            time.sleep(SCHEDULING_PERIOD)
            continue

        # Pick node according to strategy
        if strategy == "carbonaware":
            node_selection, intensity = select_best_node(carbon_data)
        elif strategy == "normal":
            node_selection, intensity = random_placement(carbon_data)
        else:
            logging.error("Invalid scheduling strategy. Skipping scheduling.")
            time.sleep(SCHEDULING_PERIOD)
        if not node_selection:
            logging.error("No suitable node found. Skipping scheduling.")
            time.sleep(SCHEDULING_PERIOD)
            continue
        
        # schedule workload
        region = NODE_REGION_MAPPING[node_selection]
        logging.info(f"Best node selected: {node_selection}")
        schedule_workload(api, pod_template, node_selection, intensity, region, strategy)
        time.sleep(SCHEDULING_PERIOD)

    # Wait for the last pod placement to occur
    logging.info("All workloads scheduled. Waiting to allow log retrieval...")
    time.sleep(70)


# Main loop
def main():
    time.sleep(10)
    api = client.CoreV1Api()
    pod_template = load_workload_template()

    # run experiment based on strategy selection
    if STRATEGY == "carbonaware":
        run_experiment(api, "carbonaware", pod_template)
    elif STRATEGY == "normal":
        run_experiment(api, "normal", pod_template)
    elif STRATEGY == "both":
        for strategy in ["carbonaware", "normal"]:
            run_experiment(api, strategy, pod_template)
    else:
        logging.error("Invalid scheduling strategy. Exiting.")
        sys.exit(1)
        
    
    logging.info("All workloads scheduled. Waiting to allow log retrieval...")
    time.sleep(3600)
    sys.exit(0)

# Kopf handler for observing actual pod placement
@kopf.on.create("", "v1", "pods")
def observe_placement(name, namespace, labels, logger, **kwargs): 
    workload_name = kwargs.get('body', {}).get('metadata', {}).get('name', None)
    node_name = kwargs.get('body', {}).get('spec', {}).get('nodeName', None)
    if workload_name and node_name:
        logging.info(f"Workload Name: {workload_name}, Node Name: {node_name}")
        region = NODE_REGION_MAPPING.get(node_name, "Unknown")
        intensity = fetch_carbon_intensity().get(region, float("inf"))

        # use logger with respective file handler according to strategy used
        strategy = labels.get("strategy")
        log_pod_placement(workload_name, node_name, intensity, region, "Actual", strategy) 

    else:
        logging.error("Could not extract workload name or node name")

# Kopf resume/create handler
@kopf.on.resume("", "v1", "pods")
@kopf.on.create("", "v1", "pods")
def on_scheduler_alive(name, namespace, labels, logger, **kwargs):
    # Check if scheduler pod has started, then run the experiments
    if labels.get("application") == "scheduler-operator":
        main()
