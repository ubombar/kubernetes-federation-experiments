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

def create_deployment():
    v1 = client.CoreV1Api()

    v1.create_deploy