from kubernetes import client, config, watch
from datetime import datetime
from experiment import ExperimentRound, append_to_feather, generate_feather_name
import time 
import pandas as pd
import numpy as np 
from number_of_experimetns import calculate_number_of_replicas
import threading 

EVENT_ADDED    = "ADDED"
EVENT_MODIFIED = "MODIFIED"
EVENT_DELETED  = "DELETED"

class KnativeExperimenter():
    def __init__(self, namespace: str, replicas: int, container_image: str, framework: str, cooldown: float, steps: int, container_command: list[str], driver: str) -> None:
        self.namespace = namespace
        self.replicas = replicas
        self.container_image = container_image
        self.framework = framework
        self.cooldown = cooldown
        self.steps = steps
        self.container_command = container_command
        self.driver = driver

        self.deployment_name = "test-deployment"
        self.container_name = "test-container"

    def estimate_time(self, delay_per_replica: float=0.1):
        return int(self.steps * (delay_per_replica * self.replicas + self.cooldown))

    def run(self, timeout=99999):
        self.load_kube_config()
        self.check_namespace()
        experiment_list = []

        estimated_time = self.estimate_time(self.steps)
        print(f"Experiment of {self.steps} step(s) with {self.replicas} replica(s) in '{self.framework}' and '{self.container_image}' image in namespace '{self.namespace}'. Estimated time for the experiment: {estimated_time} second(s)")

        def event_thread_fn(watcher_dict: dict):
            '''There is no need for locking watcher_dict, no concurrent access.'''
            w = watch.watch()
            appsv1 = client.AppsV1Api()

            for event in w.stream(appsv1.list_namespaced_deployment, namespace=self.namespace):
                event_type = event['type']
                event_object = event['object'].to_dict()

                if not event_object['metadata']['name'] == self.deployment_name: continue

                if event_type == EVENT_ADDED:
                    watcher_dict['created_at'] = datetime.now()
                elif event_type == EVENT_DELETED:
                    watcher_dict['deleted_at'] = datetime.now()
                    w.stop()
                else:
                    watcher_dict['modified_at'].append(datetime.now())
                    ready_replicas = event_object['status']['ready_replicas']
                    watcher_dict['ready_replica_counts'].append(ready_replicas)


        for s in range(self.steps):
            errors_rised = []
            watcher_dict = {
                'created_at': None,
                'deleted_at': None,
                'modified_at': [],
                'ready_replica_counts': [],
            }

            event_thread = threading.Thread(target=event_thread_fn, args=watcher_dict)
            event_thread.start()
            time.sleep(0.5)
            # Wait until event thread is watching k8s api events.
            
            # CREATE
            before_create_timestamp = datetime.now()
            errors_rised.append(self.create_deployment())

            # FIRST WAIT
            before_firstwait_timestamp = datetime.now()
            errors_rised.append(self.wait_until_deployment_ready())
            time.sleep(1)

            # DELETE
            before_delete_timestamp = datetime.now()
            errors_rised.append(self.delete_deployment())

            # SECOND WAIT
            before_secondwait_timestamp = datetime.now()
            time.sleep(1)

            # COOLDOWN
            before_cooldown_timestamp = datetime.now()
            time.sleep(self.cooldown)

            # JOIN
            before_join_timestamp = datetime.now()
            event_thread.join(timeout=timeout)

            exception_occured = errors_rised != [None, None, None]

            experiment_list.append(ExperimentRound(
                # Measurements of the experiment
                before_create_timestamp=before_create_timestamp,
                before_firstwait_timestamp=before_firstwait_timestamp,
                before_delete_timestamp=before_delete_timestamp,
                before_secondwait_timestamp=before_secondwait_timestamp,
                before_cooldown_timestamp=before_cooldown_timestamp,
                before_join_timestamp=before_join_timestamp,

                # Experiment metadata
                cool_period=self.cooldown,
                framework=self.framework,
                replicas=self.replicas,
                step=int(s),
                total_steps=self.steps,
                error_occured=exception_occured,
                errors_rised=[str(e) for e in errors_rised],
                driver=self.driver,
                command=self.container_command,

                # Event related measurements
                event_created_at=watcher_dict["created_at"],
                event_deleted_at=watcher_dict["deleted_at"],
                event_modified_at=watcher_dict["modified_at"],
                event_replicas_at=watcher_dict["ready_replica_counts"],
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
                                image=self.container_image,
                                command=self.container_command
                            ),
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
        
    def wait_until_deployment_deleted(self, timeout: int | None =None):
        w = watch.Watch()
        appsv1 = client.AppsV1Api()

        try:
            for event in w.stream(appsv1.list_namespaced_deployment, namespace=self.namespace, _request_timeout=timeout):
                deployment = event['object'].to_dict()

                if deployment['metadata']['name'] != self.deployment_name: continue

                if event['type'] == EVENT_DELETED:
                    w.stop()

        except client.ApiException as e:
            return e
        except KeyboardInterrupt:
            return

def experiment_with(replicas, namespace_experiment, cooldowns, step, driver):
    experiment_objects = [
        KnativeExperimenter(
            namespace=namespace_experiment,
            container_image="busybox", 
            replicas=replica, 
            framework="knative", 
            cooldown=cooldown, 
            driver=driver,
            steps=step,
            container_command=["/bin/sh", "-c", "sleep 9999"]) for replica , cooldown in zip(replicas, cooldowns) ]

    filename = generate_feather_name()
    total_time_reuired = sum([k.estimate_time() for k in experiment_objects])
    
    print(f"Estimated time {total_time_reuired} second(s) in {filename}.")

    for experiment in experiment_objects:        
        results = experiment.run()
        results_df = pd.DataFrame(results)
        append_to_feather(filename, results_df)
    
    return