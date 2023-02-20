from kubernetes import client, config, watch
import time 

def load_kube_config(config_file: str=None):
    config.load_kube_config(config_file=config_file)

def check_namespace(namespace: str):
    '''
        Checks if the given namespace exists, if not creates the namespace. Returns an exception
        if an error occurs. Go style.

        namespace: Non-empty string name of the namespace.
    '''
    v1 = client.CoreV1Api()

    try:
        namespace_list = [ns.metadata.name for ns in v1.list_namespace().items]
    except Exception as e:
        return e 

    if namespace in namespace_list:
        return

    try:
        v1.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace)))
    except client.ApiException as e:
        return e

def create_deployment(namespace: str, replicas: int, deployment_name: str, container_name: str, container_image: str):
    '''
        Creates a basic deployment with specified attributes.
    '''
    appsv1 = client.AppsV1Api()

    deployment = client.V1Deployment(
        # api_version="apps/v1",
        # kind="Deployment",
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
                            name=container_name,
                            image=container_image
                        )
                    ]
                )
            )
        ))

    try:
        appsv1.create_namespaced_deployment(namespace=namespace, body=deployment)
    except client.ApiException as e:
        return e

def delete_deployment(namespace: str, deployment_name: str):
    appsv1 = client.AppsV1Api()

    try:
        appsv1.delete_namespaced_deployment(name=deployment_name, namespace=namespace)
    except client.ApiException as e:
        return e

def wait_until_deployment_ready(namespace: str, deployment_name: str, timeout: int | None =None):
    '''
        Waits until the deployment is ready. Return and exception if timeout occur. 
        Default timeout is none.
    '''
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

if __name__ == "__main__":
    load_kube_config()
    print("kubeconfig loaded.")

    print("Checking namespace")
    check_namespace("experiments")

    print("Creating deployment")
    create_deployment("experiments", 1, "dp1", "cnt1", "nginx")

    print("Waiting...")
    wait_until_deployment_ready("experiments", "dp1")

    print("Deleting deployment")
    delete_deployment("experiments", "dp1")

    print("Experiment coldstart done!")