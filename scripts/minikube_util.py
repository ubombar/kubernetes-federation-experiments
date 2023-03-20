from kubernetes import client, config, watch
from datetime import datetime
import time 
import pandas as pd
import threading 
from dataclasses import dataclass
from datetime import datetime
import pandas as pd 
import os
import numpy as np 
import collections 
import json

# @dataclass
# class MinikubeExperimentRow():
#     time_before_create: datetime
#     time_before_wait: datetime
#     time_before_sleep1: datetime
#     time_before_delete: datetime
#     time_before_sleep2: datetime
#     replicas: int
#     framework: str 
#     namespace: str
#     first_sleep_seconds: float
#     second_sleep_seconds: float

def generate_name():
    current_date = datetime.now()
    return f"{str(current_date).split('.')[0].replace(' ', '_').replace('-', '').replace(':', '')}.json"

def save_json(filepath, experiment_object):
    with open(filepath, 'w') as f:
        json.dump(experiment_object, f)

def util_wait_until_deployment_ready(namespace, deployment_name, timeout=None):
    w = watch.Watch()
    appsv1 = client.AppsV1Api()

    try:
        for event in w.stream(appsv1.list_namespaced_deployment, namespace=namespace, _request_timeout=timeout):
            deployment = event['object'].to_dict()

            if deployment['metadata']['name'] != deployment_name: continue
            
            ready_replicas = deployment['status']['ready_replicas']
            replicas = deployment['status']['replicas']

            # If null continue
            if not ready_replicas: continue

            if ready_replicas == replicas:
                w.stop()
    except client.ApiException as e:
        return e
    except KeyboardInterrupt:
        return

def util_create_deployment(namespace, deployment_name, replicas):
    appsv1 = client.AppsV1Api()

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name=deployment_name,
            labels={
                'app': 'test'
            },
        ),
        spec=client.V1DeploymentSpec(
            replicas=replicas,
            selector=client.V1LabelSelector(
                match_labels={
                    'app': 'test',
                },
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={
                        'app': 'test',
                    },
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="test-container",
                            image="busybox",
                            command=["/bin/sh", "-c", "sleep 9999"]
                        ),
                    ]
                )
            )
        ))

    try:
        appsv1.create_namespaced_deployment(namespace=namespace, body=deployment)
    except client.ApiException as e:
        return e

def util_delete_deployment(namespace, deployment_name):
    appsv1 = client.AppsV1Api()

    try:
        appsv1.delete_namespaced_deployment(name=deployment_name, namespace=namespace)
    except client.ApiException as e:
        return e

def retrieve_deployment_events(namespace, deployment_name, event_list) -> list[dict]:
    w = watch.Watch()
    appsv1 = client.AppsV1Api()

    for event in w.stream(appsv1.list_namespaced_deployment, namespace=namespace):
        event_type = event['type']
        event_object = event['object'].to_dict()

        if not event_object['metadata']['name'] == deployment_name: continue

        if event_type == "ADDED":
            event_list.append({
                "name": deployment_name,
                "type": "created",
                "ready_replicas": None,
                "time": str(datetime.now()),
            })
        elif event_type == "DELETED":
            event_list.append({
                "name": deployment_name,
                "type": "deleted",
                "ready_replicas": None,
                "time": str(datetime.now()),
            })
            w.stop() # STOP IF IT DEPLOYMENT IS DELETED
        else:
            event_list.append({
                "name": deployment_name,
                "type": "modified",
                "ready_replicas": event_object['status']['ready_replicas'],
                "time": str(datetime.now()),
            })

def util_wait_until_deployments_ready(namespace, deployment_count, timeout=None):
    w = watch.Watch()
    appsv1 = client.AppsV1Api()
    number_of_ready = 0

    try:
        for event in w.stream(appsv1.list_namespaced_deployment, namespace=namespace, _request_timeout=timeout):
            deployment = event['object'].to_dict()

            ready_replicas = deployment['status']['ready_replicas']
            replicas = deployment['status']['replicas']

            # If null continue
            if not ready_replicas: continue

            if ready_replicas == replicas: # replicas == 1 == ready_replicas
                number_of_ready += 1

            if deployment_count == number_of_ready:
                w.stop()
    except client.ApiException as e:
        return e
    except KeyboardInterrupt:
        return

def util_create_deployments(namespace, deployment_count):
    appv1 = client.AppsV1Api()
    deployments = []

    for i in range(deployment_count):
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=f"deployment-{i}",
                labels={
                    'app': 'test'
                },
            ),
            spec=client.V1DeploymentSpec(
                replicas=1, # Each deployment gets 1 replica
                selector=client.V1LabelSelector(
                    match_labels={
                        'app': 'test',
                    },
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={
                            'app': 'test',
                        },
                    ),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="test-container",
                                image="busybox",
                                command=["/bin/sh", "-c", "sleep 9999"]
                            ),
                        ]
                    )
                )
            ))
        deployments.append(deployment)

    try:
        for deployment in deployments:
            appv1.create_namespaced_deployment(namespace=namespace, body=deployment)
    except client.ApiException as e:
        return e

def util_delete_deployments(namespace, deployment_count):
    appsv1 = client.AppsV1Api()
    try:
        for i in range(deployment_count):
            appsv1.delete_namespaced_deployment(name=f"deployment-{i}", namespace=namespace)
    except client.ApiException as e:
        return e

def retrieve_deployments_events(namespace, event_dict: dict[list]) -> list[dict]:
    w = watch.Watch()
    appsv1 = client.AppsV1Api()

    for event in w.stream(appsv1.list_namespaced_deployment, namespace=namespace):
        event_type = event['type']
        event_object = event['object'].to_dict()

        deployment_name = event_object['metadata']['name']

        if event_type == "ADDED":
            event_dict[deployment_name].append({
                "name": deployment_name,
                "type": "created",
                "ready_replicas": None,
                "time": str(datetime.now()),
            })
        elif event_type == "DELETED":
            event_dict[deployment_name].append({
                "name": deployment_name,
                "type": "deleted",
                "ready_replicas": None,
                "time": str(datetime.now()),
            })
            w.stop() # STOP IF IT DEPLOYMENT IS DELETED
        else:
            event_dict[deployment_name].append({
                "name": deployment_name,
                "type": "modified",
                "ready_replicas": event_object['status']['ready_replicas'],
                "time": str(datetime.now()),
            })

def retrieve_pods_events(namespace, event_dict: dict[list]):
    w = watch.Watch()
    corev1 = client.CoreV1Api()

    for event in w.stream(corev1.list_namespaced_pod, namespace=namespace):
        event_type = event['type']
        event_object = event['object'].to_dict()

        pod_name = event_object['metadata']['name']
        pod_phase = event_object['status']['phase']

        if event_type == "ADDED":
            event_dict[pod_name].append({
                "name": pod_name,
                "type": "created",
                "phase": pod_phase,
                "time": str(datetime.now()),
            })
        elif event_type == "DELETED":
            event_dict[pod_name].append({
                "name": pod_name,
                "type": "deleted",
                "phase": pod_phase,
                "time": str(datetime.now()),
            })
            w.stop() # STOP IF IT DEPLOYMENT IS DELETED
        else:
            event_dict[pod_name].append({
                "name": pod_name,
                "type": "modified",
                "phase": pod_phase,
                "time": str(datetime.now()),
            })