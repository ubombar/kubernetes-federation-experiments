from kubernetes import client, config, watch
from datetime import datetime
import time 
import pandas as pd
import threading 
from dataclasses import dataclass
from datetime import datetime
import pandas as pd 
from dataclasses import dataclass
import os
import numpy as np 
import collections 
from  minikube_util import *
import threading
import json

def minikube_deployment_type_experiment(replicas) -> dict:
    config.load_kube_config()
    result = {
        "deployment_name": "test-deployment",
        "namespace": "default",
        "first_sleep_seconds": 1,
        "second_sleep_seconds": 1,
        "deployment_event_list": list(),
        "pods_event_dict": collections.defaultdict(list),
        "replicas": replicas,
    }

    deployment_thread = threading.Thread(target=retrieve_deployment_events, args=[result["namespace"], result["deployment_name"], result["deployment_event_list"]])
    deployment_thread.start()

    pods_thread = threading.Thread(target=retrieve_pods_events, args=[result["namespace"], result["pods_event_dict"]])
    pods_thread.start()

    result["time_before_create"] = str(datetime.now())
    util_create_deployment(result["namespace"], result["deployment_name"], result["replicas"])

    result["time_before_wait"] = str(datetime.now())
    util_wait_until_deployment_ready(result["namespace"], result["deployment_name"])

    result["time_before_sleep1"] = str(datetime.now())
    time.sleep(result["first_sleep_seconds"])

    result["time_before_delete"] = str(datetime.now())
    util_delete_deployment(result["namespace"], result["deployment_name"])
    
    result["time_before_sleep2"] = str(datetime.now())
    time.sleep(result["second_sleep_seconds"])

    deployment_thread.join()
    pods_thread.join()

    return result

def minikube_deployments_type_experiment(deployment_count) -> dict:
    config.load_kube_config()
    result = {
        "namespace": "default",
        "first_sleep_seconds": 1,
        "second_sleep_seconds": 1,
        "deployments_event_dict": collections.defaultdict(list),
        "pods_event_dict": collections.defaultdict(list),
        "deployment_count": deployment_count,
    }

    deployments_thread = threading.Thread(target=retrieve_deployments_events, args=[result["namespace"], result["deployments_event_dict"]])
    deployments_thread.start()
    
    pods_thread = threading.Thread(target=retrieve_pods_events, args=[result["namespace"], result["pods_event_dict"]])
    pods_thread.start()

    result["time_before_create"] = str(datetime.now())
    util_create_deployments(result["namespace"], result["deployment_count"])

    result["time_before_wait"] = str(datetime.now())
    util_wait_until_deployments_ready(result["namespace"], result["deployment_count"])

    result["time_before_sleep1"] = str(datetime.now())
    time.sleep(result["first_sleep_seconds"])

    result["time_before_delete"] = str(datetime.now())
    util_delete_deployments(result["namespace"], result["deployment_count"])
    
    result["time_before_sleep2"] = str(datetime.now())
    time.sleep(result["second_sleep_seconds"])

    deployments_thread.join()
    pods_thread.join()

    return result

r = minikube_deployments_type_experiment(2)

print(json.dumps(r, indent=2))