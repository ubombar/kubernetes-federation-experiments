from kubernetes import client, config, watch
from datetime import datetime
from experiment import ExperimentRound
import time 
import pandas as pd
import numpy as np 
from number_of_experimetns import calculate_number_of_replicas

class KnativeExperimenter():
    def __init__(self, namespace: str, replicas: int, container_image: str, framework: str, cooldown: float) -> None:
        self.namespace = namespace
        self.replicas = replicas
        self.container_image = container_image
        self.framework = framework
        self.cooldown = cooldown

        self.deployment_name = "test-deployment"
        self.container_name = "test-container"

    def run(self, steps):
        self.load_kube_config()
        self.check_namespace()
        experiment_list = []

        estimated_time = int(steps * (1.5 * self.replicas + self.cooldown))
        print(f"Experiment of {steps} step(s) with {self.replicas} replica(s) in '{self.framework}' and '{self.container_image}' image in namespace '{self.namespace}'. Estimated time for the experiment: {estimated_time} second(s)")

        for s in range(steps):
            eess = []
            experiment_start_date = datetime.now()
            experiment_deployment_creation_started_date = experiment_start_date
            eess.append(self.create_deployment())
            experiment_deployment_creation_finished_date = datetime.now()

            eess.append(self.wait_until_deployment_ready())

            experiment_deployment_becoma_ready_date = datetime.now()

            time.sleep(self.cooldown)

            experiment_deployment_deletion_started_date = datetime.now()
            eess.append(self.delete_deployment())
            experiment_deployment_deletion_finished_date = datetime.now()
            experiment_finsh_date = experiment_deployment_deletion_finished_date

            exception_occured = eess == [None, None, None]

            experiment_list.append(ExperimentRound(
                experiment_start_date=experiment_start_date,
                experiment_finsh_date=experiment_finsh_date,

                experiment_deployment_becoma_ready_date=experiment_deployment_becoma_ready_date,
                
                experiment_deployment_creation_started_date=experiment_deployment_creation_started_date,
                experiment_deployment_creation_finished_date=experiment_deployment_creation_finished_date,

                experiment_deployment_deletion_started_date=experiment_deployment_deletion_started_date,
                experiment_deployment_deletion_finished_date=experiment_deployment_deletion_finished_date,

                cool_period=self.cooldown,
                framework=self.framework,
                replicas=self.replicas,
                step=s,
                total_steps=steps,
                error_occured=exception_occured,
                exception=str(eess),
            ))

        return experiment_list

    def load_kube_config(self):
        config.load_kube_config()

    def check_namespace(self):
        '''
            Checks if the given namespace exists, if not creates the namespace. Returns an exception
            if an error occurs. Go style.

            namespace: Non-empty string name of the namespace.
        '''
        v1 = client.CoreV1Api()

        try:
            namespace_list = [ns.metadata.name for ns in v1.list_namespace().items]
        except client.ApiException as e:
            return e 

        if self.namespace in namespace_list:
            return

        try:
            v1.create_namespace(client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=self.namespace
                )
            ))
        except client.ApiException as e:
            return e

    def create_deployment(self):
        '''
            Creates a basic deployment with specified attributes.
        '''
        appsv1 = client.AppsV1Api()

        deployment = client.V1Deployment(
            # api_version="apps/v1",
            # kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=self.deployment_name,
                labels={
                    'app': 'test'
                },
            ),
            spec=client.V1DeploymentSpec(
                replicas=self.replicas,
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
                                name=self.container_name,
                                image=self.container_image
                            )
                        ]
                    )
                )
            ))

        try:
            appsv1.create_namespaced_deployment(namespace=self.namespace, body=deployment)
        except client.ApiException as e:
            return e

    def delete_deployment(self):
        appsv1 = client.AppsV1Api()

        try:
            appsv1.delete_namespaced_deployment(name=self.deployment_name, namespace=self.namespace)
        except client.ApiException as e:
            return e

    def wait_until_deployment_ready(self, timeout: int | None =None):
        '''
            Waits until the deployment is ready. Return and exception if timeout occur. 
            Default timeout is none.
        '''
        w = watch.Watch()
        appsv1 = client.AppsV1Api()

        try:
            for event in w.stream(appsv1.list_namespaced_deployment, namespace=self.namespace, _request_timeout=timeout):
                deployment = event['object'].to_dict()

                if deployment['metadata']['name'] != self.deployment_name: continue
                
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

def experiment_with(replicas, namespace_experiment, cooldowns, step):
    for replica , cooldown in zip(replicas, cooldowns):
        k = KnativeExperimenter(namespace=namespace_experiment, container_image="nginx", replicas=replica, framework="knative", cooldown=cooldown)
        results = k.run(step)
    
        results_df = pd.DataFrame(results)
        current_date = datetime.now()
        filename = f"./exps/{str(current_date).split('.')[0].replace(' ', '_').replace('-', '').replace(':', '')}_{replica}.feather"
        results_df.to_feather(filename)
