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

def util_wait_until_pods_ready(namespace, pod_count, timeout=None):
    w = watch.Watch()
    corev1 = client.CoreV1Api()
    number_of_creations = 0

    try:
        for event in w.stream(corev1.list_namespaced_pod, namespace=namespace, _request_timeout=timeout):
            event_type = event['type']
            event_object = event['object'].to_dict()

            # We want containers to be running before shutting down
            if event_type == "MODIFIED":
                if event_object["status"]["phase"] == "Running":
                    number_of_creations += 1

            if number_of_creations == pod_count:
                w.stop()
    except client.ApiException as e:
        return e
    except KeyboardInterrupt:
        return

def util_create_pods(namespace, pod_count):
    corev1 = client.CoreV1Api()
    pods = []

    for i in range(pod_count):
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=f"pod-{i}",
                labels={
                    "app": "test",
                }
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
        pods.append(pod)

    try:
        for pod in pods:
            corev1.create_namespaced_pod(namespace=namespace, body=pod)
    except client.ApiException as e:
        return e

def util_delete_pods(namespace, pod_count):
    corev1 = client.CoreV1Api()
    try:
        for i in range(pod_count):
            corev1.delete_namespaced_pod(name=f"pod-{i}", namespace=namespace)
    except client.ApiException as e:
        return e

# def retrieve_deployment_events(namespace, deployment_name, event_list) -> list[dict]:
#     w = watch.Watch()
#     appsv1 = client.AppsV1Api()

#     for event in w.stream(appsv1.list_namespaced_deployment, namespace=namespace):
#         event_type = event['type']
#         event_object = event['object'].to_dict()

#         if not event_object['metadata']['name'] == deployment_name: continue

#         if event_type == "ADDED":
#             event_list.append({
#                 "name": deployment_name,
#                 "type": "created",
#                 "ready_replicas": None,
#                 "time": str(datetime.now()),
#             })
#         elif event_type == "DELETED":
#             event_list.append({
#                 "name": deployment_name,
#                 "type": "deleted",
#                 "ready_replicas": None,
#                 "time": str(datetime.now()),
#             })
#             w.stop() # STOP IF IT DEPLOYMENT IS DELETED
#         else:
#             event_list.append({
#                 "name": deployment_name,
#                 "type": "modified",
#                 "ready_replicas": event_object['status']['ready_replicas'],
#                 "time": str(datetime.now()),
#             })
