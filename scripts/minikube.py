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
        "event_list": [],
        "replicas": replicas,
    }

    deployment_thread = threading.Thread(target=retrieve_deployment_events, args=[result["namespace"], result["deployment_name"], result["event_list"]])
    deployment_thread.start()

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

    return result

def minikube_pod_type_experiment(pod_count) -> dict:
    config.load_kube_config()
    result = {
        "namespace": "default",
        "first_sleep_seconds": 1,
        "second_sleep_seconds": 1,
        "pod_count": pod_count,
    }

    result["time_before_create"] = str(datetime.now())
    util_create_pods(result["namespace"], result["pod_count"])

    result["time_before_wait"] = str(datetime.now())
    util_wait_until_pods_ready(result["namespace"], result["pod_count"])

    result["time_before_sleep1"] = str(datetime.now())
    time.sleep(result["first_sleep_seconds"])

    result["time_before_delete"] = str(datetime.now())
    util_delete_pods(result["namespace"], result["pod_count"])
    
    result["time_before_sleep2"] = str(datetime.now())
    time.sleep(result["second_sleep_seconds"])

    return result

r = minikube_pod_type_experiment(1)

print(json.dumps(r, indent=2))