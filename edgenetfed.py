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
from  util import *
import threading
import json
from tqdm import tqdm
import itertools

def edgenetfed_selectivedeployment_type_experiment(pod_count, namespace, first_sleep_seconds, second_sleep_seconds, kubeconfig_file_worker1, kubeconfig_file_worker2, kubeconfig_file_fedmanager) -> dict:
    config.load_kube_config()
    result = {
        "deployment_events": list(),
        "pod_events": collections.defaultdict(list),
    }

    deployment_thread = threading.Thread(target=retrieve_deployment_events, args=[namespace, "deployment", result["deployment_events"]])
    deployment_thread.start()

    pods_thread = threading.Thread(target=retrieve_pods_events, args=[namespace, result["pod_events"]])
    pods_thread.start()

    result["time_before_create"] = str(datetime.now())
    util_create_selectivedeployment(namespace, "deployment", pod_count)

    result["time_before_wait"] = str(datetime.now())
    util_wait_until_deployment_ready(namespace, "deployment")

    result["time_before_sleep1"] = str(datetime.now())
    time.sleep(first_sleep_seconds)

    result["time_before_delete"] = str(datetime.now())
    util_delete_deployment(namespace, "deployment")
    
    result["time_before_sleep2"] = str(datetime.now())
    time.sleep(second_sleep_seconds)

    result["time_before_join"] = str(datetime.now())
    deployment_thread.join()
    pods_thread.join()

    result["time_before_end"] = str(datetime.now())
    return result

def edgenetfed_selectivedeployments_type_experiment(pod_count, namespace, first_sleep_seconds, second_sleep_seconds) -> dict:
    config.load_kube_config()
    result = {
        "deployment_events": collections.defaultdict(list),
        "pod_events": collections.defaultdict(list),
    }

    deployments_thread = threading.Thread(target=retrieve_deployments_events, args=[namespace, result["deployment_events"]])
    deployments_thread.start()
    
    pods_thread = threading.Thread(target=retrieve_pods_events, args=[namespace, result["pod_events"]])
    pods_thread.start()

    result["time_before_create"] = str(datetime.now())
    util_create_deployments(namespace, pod_count)

    result["time_before_wait"] = str(datetime.now())
    util_wait_until_deployments_ready(namespace, pod_count)

    result["time_before_sleep1"] = str(datetime.now())
    time.sleep(first_sleep_seconds)

    result["time_before_delete"] = str(datetime.now())
    util_delete_deployments(namespace, pod_count)
    
    result["time_before_sleep2"] = str(datetime.now())
    time.sleep(second_sleep_seconds)

    result["time_before_join"] = str(datetime.now())
    deployments_thread.join()
    pods_thread.join()

    result["time_before_end"] = str(datetime.now())
    return result

def experiment_selectivedeployments(pod_counts: list[int], single_deployment: bool, num_iterations: int, namespace: str="default", first_sleep: int=5, second_sleep: int=5) -> dict:
    experiments = []
    filepath = os.path.join("jsons", generate_name())

    # Info
    kubeconfig_file_worker1 = "~/.kube/config" # we are here
    kubeconfig_file_worker2 = "~/.kube/config-worker-2"
    kubeconfig_file_fedmanager = "~/.kube/config-fed-manager"
    selectivedeployment_namespace = '71959dc7-5064-4ad1-b72a-a0cbe6a7df5c-test-34390dac'

    for pod_count, iteration in tqdm(itertools.product(pod_counts, range(num_iterations)), total=len(pod_counts)*num_iterations):
        data = None
        if single_deployment:
            data = edgenetfed_selectivedeployment_type_experiment(pod_count, namespace, first_sleep, second_sleep, kubeconfig_file_worker1, kubeconfig_file_worker2, kubeconfig_file_fedmanager)
        else:
            data = edgenetfed_selectivedeployments_type_experiment(pod_count, namespace, first_sleep, second_sleep)

        experiment = {
            "data": data,
            "framework": "native",
            "iteration": iteration,
            "num_iterations": num_iterations,
            "pod_count": pod_count,
            "namespace": namespace,
            "single_deployment": single_deployment,
        }
        experiments.append(experiment)

        save_json(filepath, experiments)

if __name__ == "__main__":
    print("Experiment: single_deployment")
    experiment_selectivedeployments([1, 5, 20], False, 50)

    print("Experiment: multi_deployment")
    experiment_selectivedeployments([1, 5, 20], True, 50)