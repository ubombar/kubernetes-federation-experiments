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

def util_wait_until_deployment_ready(kubeconfig_file, namespace, deployment_name, timeout=None):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        w = watch.Watch()
        appsv1 = client.AppsV1Api(api_client)

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

def util_create_deployment(kubeconfig_file, namespace, deployment_name, replicas):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        w = watch.Watch()
        appsv1 = client.AppsV1Api(api_client)

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

def util_delete_deployment(kubeconfig_file, namespace, deployment_name):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        w = watch.Watch()
        appsv1 = client.AppsV1Api(api_client)

        try:
            appsv1.delete_namespaced_deployment(name=deployment_name, namespace=namespace)
        except client.ApiException as e:
            return e

def retrieve_deployment_events(kubeconfig_file, namespace, deployment_name, event_list) -> list[dict]:
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        w = watch.Watch()
        appsv1 = client.AppsV1Api(api_client)

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

def util_wait_until_deployments_ready(kubeconfig_file, namespace, deployment_count, timeout=None):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        w = watch.Watch()
        appsv1 = client.AppsV1Api(api_client)
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

def util_create_deployments(kubeconfig_file, namespace, deployment_count):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        w = watch.Watch()
        appsv1 = client.AppsV1Api(api_client)
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
                appsv1.create_namespaced_deployment(namespace=namespace, body=deployment)
        except client.ApiException as e:
            return e

def util_delete_deployments(kubeconfig_file, namespace, deployment_count):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        w = watch.Watch()
        appsv1 = client.AppsV1Api(api_client)

        try:
            for i in range(deployment_count):
                appsv1.delete_namespaced_deployment(name=f"deployment-{i}", namespace=namespace)
        except client.ApiException as e:
            return e

def retrieve_deployments_events(kubeconfig_file, namespace, event_dict: dict[list]) -> list[dict]:
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        w = watch.Watch()
        appsv1 = client.AppsV1Api(api_client)

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

def retrieve_pods_events(kubeconfig_file, namespace, event_dict: dict[list]):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        w = watch.Watch()
        corev1 = client.CoreV1Api(api_client)

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

def retrieve_selectivedeployment_events(kubeconfig_file, namespace, selectivedeployment_name, event_list) -> list[dict]:
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        coa = client.CustomObjectsApi(api_client)
        w = watch.Watch()

        for event in w.stream(coa.list_namespaced_custom_object, namespace=namespace, group="apps.edgenet.io", version="v1alpha2", plural="selectivedeployments"):
            event_type = event['type']
            event_object = event['object']

            if not event_object['metadata']['name'] == selectivedeployment_name: continue

            if event_type == "ADDED":
                event_list.append({
                    "name": selectivedeployment_name,
                    "type": "created",
                    "time": str(datetime.now()),
                })
            elif event_type == "DELETED":
                event_list.append({
                    "name": selectivedeployment_name,
                    "type": "deleted",
                    "time": str(datetime.now()),
                })
                w.stop() # STOP IF IT DEPLOYMENT IS DELETED
            else:
                event_list.append({
                    "name": selectivedeployment_name,
                    "type": "modified",
                    "time": str(datetime.now()),
                })

def retrieve_selectivedeployments_events(kubeconfig_file, namespace, event_dict: dict[list]) -> list[dict]:
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        coa = client.CustomObjectsApi(api_client)
        w = watch.Watch()

        for event in w.stream(coa.list_namespaced_custom_object, namespace=namespace, group="apps.edgenet.io", version="v1alpha2", plural="selectivedeployments"):
            event_type = event['type']
            event_object = event['object']

            selectivedeployment_name = event_object['metadata']['name']

            if event_type == "ADDED":
                event_dict[selectivedeployment_name].append({
                    "name": selectivedeployment_name,
                    "type": "created",
                    "time": str(datetime.now()),
                })
            elif event_type == "DELETED":
                event_dict[selectivedeployment_name].append({
                    "name": selectivedeployment_name,
                    "type": "deleted",
                    "time": str(datetime.now()),
                })
                w.stop() # STOP IF THE OBJECT IS DELETED
            else:
                event_dict[selectivedeployment_name].append({
                    "name": selectivedeployment_name,
                    "type": "modified",
                    "time": str(datetime.now()),
                })

def retrieve_selectivedeploymentanchors_events(kubeconfig_file, namespace, event_dict: dict[list]) -> list[dict]:
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        coa = client.CustomObjectsApi(api_client)
        w = watch.Watch()

        for event in w.stream(coa.list_namespaced_custom_object, 
                              namespace=namespace, 
                              group="federation.edgenet.io", 
                              version="v1alpha1", 
                              plural="selectivedeploymentanchors"):
            event_type = event['type']
            event_object = event['object']

            selectivedeploymentanchor_name = event_object['metadata']['name']

            if event_type == "ADDED":
                event_dict[selectivedeploymentanchor_name].append({
                    "name": selectivedeploymentanchor_name,
                    "type": "created",
                    "time": str(datetime.now()),
                })
            elif event_type == "DELETED":
                event_dict[selectivedeploymentanchor_name].append({
                    "name": selectivedeploymentanchor_name,
                    "type": "deleted",
                    "time": str(datetime.now()),
                })
                w.stop() # STOP IF THE OBJECT IS DELETED
            else:
                event_dict[selectivedeploymentanchor_name].append({
                    "name": selectivedeploymentanchor_name,
                    "type": "modified",
                    "time": str(datetime.now()),
                })

def retrieve_namespace_events(kubeconfig_file, namespace, event_list) -> list[dict]:
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        core = client.CoreV1Api(api_client)
        w = watch.Watch()

        for event in w.stream(core.list_namespace):
            event_type = event['type']
            event_object = event['object'].to_dict()

            if not event_object['metadata']['name'] == namespace: continue

            if event_type == "ADDED":
                event_list.append({
                    "name": namespace,
                    "type": "created",
                    "time": str(datetime.now()),
                })
            elif event_type == "DELETED":
                event_list.append({
                    "name": namespace,
                    "type": "deleted",
                    "time": str(datetime.now()),
                })
                w.stop() # STOP IF IT DEPLOYMENT IS DELETED
            else:
                event_list.append({
                    "name": namespace,
                    "type": "modified",
                    "time": str(datetime.now()),
                })

def util_create_selectivedeployment(kubeconfig_file, selectivedeployment_namespace, selectivedeployment_name, deployment_name, deployment_replicas):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        coa = client.CustomObjectsApi(api_client)

        deployment_object = client.V1Deployment(
                api_version="v1",
                kind="Deployment",
                metadata=client.V1ObjectMeta(
                    name=deployment_name,
                    labels={
                        'app': 'test'
                    },
                ),
                spec=client.V1DeploymentSpec(
                    replicas=deployment_replicas,
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
                            termination_grace_period_seconds=0,
                            containers=[
                                client.V1Container(
                                    name="test-container",
                                    image="busybox",
                                    command=["/bin/sh", "-c", "sleep 9999"],
                                    resources=client.V1ResourceRequirements(
                                        limits={
                                            'cpu': '50m',
                                            'memory': '50Mi'
                                        },
                                        requests={
                                            'cpu': '50m',
                                            'memory': '50Mi'
                                        }
                                    ),
                                ),
                            ]
                        )
                    )
                ))

        selectivedeployment_object = {
            'apiVersion': 'apps.edgenet.io/v1alpha2',
            'kind': 'SelectiveDeployment',
            'metadata': {
                'name': selectivedeployment_name,
                'namespace': selectivedeployment_namespace
            },
            'spec': {
                'workloads': {
                    'deployment': [
                        deployment_object
                    ]
                },
                'clusterAffinity': {
                    'matchLabels': {
                        'edge-net.io/city': 'Izmir'
                    }
                },
                'clusterReplicas': 1
            }
        }

        try:
            coa.create_namespaced_custom_object(group="apps.edgenet.io", 
                                                namespace=selectivedeployment_namespace, 
                                                version="v1alpha2", 
                                                plural="selectivedeployments", 
                                                body=selectivedeployment_object)
        except client.ApiException as e:
            return e

def util_create_selectivedeployments(kubeconfig_file, selectivedeployment_namespace, selectivedeployment_name, deployment_name, selectivedeployment_count):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        coa = client.CustomObjectsApi(api_client)

        for i in range(selectivedeployment_count):
            deployment_object = client.V1Deployment(
                    api_version="v1",
                    kind="Deployment",
                    metadata=client.V1ObjectMeta(
                        name=f"{deployment_name}-{i}",
                        labels={
                            'app': 'test'
                        },
                    ),
                    spec=client.V1DeploymentSpec(
                        replicas=1,
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
                                termination_grace_period_seconds=0,
                                containers=[
                                    client.V1Container(
                                        name="test-container",
                                        image="busybox",
                                        command=["/bin/sh", "-c", "sleep 9999"],
                                        resources=client.V1ResourceRequirements(
                                            limits={
                                                'cpu': '50m',
                                                'memory': '50Mi'
                                            },
                                            requests={
                                                'cpu': '50m',
                                                'memory': '50Mi'
                                            }
                                        ),
                                    ),
                                ]
                            )
                        )
                    ))

            selectivedeployment_object = {
                'apiVersion': 'apps.edgenet.io/v1alpha2',
                'kind': 'SelectiveDeployment',
                'metadata': {
                    'name': f"{selectivedeployment_name}-{i}",
                    'namespace': selectivedeployment_namespace
                },
                'spec': {
                    'workloads': {
                        'deployment': [
                            deployment_object
                        ]
                    },
                    'clusterAffinity': {
                        'matchLabels': {
                            'edge-net.io/city': 'Izmir'
                        }
                    },
                    'clusterReplicas': 1
                }
            }

            try:
                r = coa.create_namespaced_custom_object(group="apps.edgenet.io", 
                                                    namespace=selectivedeployment_namespace, 
                                                    version="v1alpha2", 
                                                    plural="selectivedeployments", 
                                                    body=selectivedeployment_object)
            except client.ApiException as e:
                return e

def util_delete_selectivedeployment(kubeconfig_file, namespace, selectivedeployment_name):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        coa = client.CustomObjectsApi(api_client)

        try:
            coa.delete_namespaced_custom_object(name=selectivedeployment_name, 
                                             namespace=namespace, 
                                             group="apps.edgenet.io", 
                                             version="v1alpha2", 
                                             plural="selectivedeployments")
        except client.ApiException as e:
            return e

def util_delete_selectivedeployments(kubeconfig_file, namespace, selectivedeployment_name, selectivedeployment_count):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        coa = client.CustomObjectsApi(api_client)

        for i in range(selectivedeployment_count):
            try:
                coa.delete_namespaced_custom_object(name=f"{selectivedeployment_name}-{i}", 
                                                namespace=namespace, 
                                                group="apps.edgenet.io", 
                                                version="v1alpha2", 
                                                plural="selectivedeployments")
            except client.ApiException as e:
                return e

def util_delete_selectivedeploymentanchors(kubeconfig_file, namespace):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        coa = client.CustomObjectsApi(api_client)

        try:
            coa.delete_collection_namespaced_custom_object(namespace=namespace, 
                                             group="federation.edgenet.io", 
                                             version="v1alpha1", 
                                             plural="selectivedeploymentanchors")
        except client.ApiException as e:
            return e
    
def util_delete_namespace(kubeconfig_file, namespace):
    configuration = client.Configuration()
    config.load_kube_config(config_file=kubeconfig_file, client_configuration=configuration)

    with client.ApiClient(configuration) as api_client:
        core = client.CoreV1Api(api_client)

        try:
            core.delete_namespace(name=namespace)
        except client.ApiException as e:
            return e


# if __name__ == "__main__":
#     configuration = client.Configuration()
#     config.load_kube_config(config_file="~/.kube/config-worker-2", client_configuration=configuration)

#     with client.ApiClient(configuration) as api_client:
#         coa = client.CustomObjectsApi(api_client)

#         response = coa.list_namespaced_custom_object(group="apps.edgenet.io", namespace="71959dc7-5064-4ad1-b72a-a0cbe6a7df5c-test-34390dac", plural="selectivedeployments", version="v1alpha2")
        
#         for item in response['items']:
#             print(item['metadata']['name'])

#     # w = watch.Watch()

#     # for event in w.stream(coa.list_namespaced_custom_object, group="apps.edgenet.io", namespace="71959dc7-5064-4ad1-b72a-a0cbe6a7df5c-test-34390dac", plural="selectivedeployments", version="v1alpha2"):
#     #     print(event['type'])

#     # print(response["items"][0]["metadata"]["name"])