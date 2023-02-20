from kubernetes import client, config, watch

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


load_kube_config()
# create_deployment("experiments", 1, "dp1", "cnt1", "nginx")
delete_deployment("experiments", "dp1")