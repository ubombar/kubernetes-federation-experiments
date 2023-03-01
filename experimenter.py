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

def calculate_number_of_replicas(max_replicas: int, number_of_experiments: int) -> np.array:
    '''
        We assume in each experiment, number of replicas grows exponentially. This function 
        calculates number of replicas for a given maximum replica and number of experiments.
        For the base experiment we also add replica=1 as the first experiment. So return
        will have number_of_experiments elements.

        max_replicas: Maximum number of replicas that can be created in the experiment.
        number_of_experiments: Requested number of experiments (expluding the replica=1)
    '''
    alpha = max_replicas / np.exp(number_of_experiments - 2)

    # First experiment's replica count is allways set to 1.
    experiments = np.array(range(-1, number_of_experiments - 1))

    replicas = alpha * np.exp(experiments)
    replicas[0] = 1

    return replicas.astype(int)

@dataclass
class ExperimentRound():
    # Measurement taken just before creation
    before_create_timestamp: datetime

    # Measurement taken just before first waiting
    before_firstwait_timestamp: datetime

    # Measurement taken just before delete
    before_delete_timestamp: datetime

    # Measurement taken just before second waiting
    before_secondwait_timestamp: datetime

    # Measurement taken just after cooldown
    before_cooldown_timestamp: datetime

    # Measurement taken just after cooldown
    before_join_timestamp: datetime

    # Number of replicas
    replicas: int

    # Name of the federation framework
    framework: str 

    # If any error occured
    error_occured: bool

    # Kubernetes API exception (string representation)
    errors_rised: str

    # Experiment's current step
    step: int

    # Total steps for the experiment
    total_steps: int

    # Time waited in seconds after deployment created
    cool_period: float

    # Driver of the kubernetes cluster
    driver: str

    # Command used to run the container
    command: list[str]

    # Event timestamps
    event_created_at: datetime
    event_deleted_at: datetime

    # Timestamp list for each modificaion event
    event_modified_at: list[datetime]

    # Number of replicas for each event received
    event_replicas_at: list[datetime]
    
    # Pod metrics, when deployment controller creates and deletes pod objects
    first_created_at: datetime
    last_created_at: datetime
    first_deleted_at: datetime 
    last_deleted_at: datetime

def append_to_feather(filename, new_df: pd.DataFrame):
    if os.path.exists(filename):
        old_df: pd.DataFrame = pd.read_feather(filename)
    else:
        old_df = pd.DataFrame()
    big_df = pd.concat([old_df, new_df], ignore_index=True)
    big_df.to_feather(filename)

def generate_feather_name():
    current_date = datetime.now()
    return f"./exps/{str(current_date).split('.')[0].replace(' ', '_').replace('-', '').replace(':', '')}.feather"

@dataclass
class ExperimentConfig():
    # native, liqo, kubefed, edgenet
    framework: str 
    
    # minikube, kwok, native
    driver: str 
    
    # Number of replicas
    replicas: int 
    
    # cooldown in seconds
    cooldown: float 

    # Number of steps
    steps: int

    # Container command
    container_command: list[str]
    
    # Namespace
    namespace: str = "experiments"
    
    # Container image
    container_image: str = "busybox"

    # Deployment name
    deployment_name: str = "test-deployment"

    # Cotnainer name
    container_name: str = "test-container"

class CreateDeleteHandler():
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    def create_deployment():
        raise NotImplementedError
    
    def delete_deployment():
        raise NotImplementedError
    
    def wait_until_deployment_ready(self, timeout: int | None =None):
        '''
            Waits until the deployment is ready. Return and exception if timeout occur. 
            Default timeout is none.
        '''
        w = watch.Watch()
        appsv1 = client.AppsV1Api()

        try:
            for event in w.stream(appsv1.list_namespaced_deployment, namespace=self.config.namespace, _request_timeout=timeout):
                deployment = event['object'].to_dict()

                if deployment['metadata']['name'] != self.config.deployment_name: continue
                
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

class Experimenter():
    def __init__(self, config: ExperimentConfig, handler: CreateDeleteHandler) -> None:
        self.config = config
        self.handler = handler

    def estimate_time(self, delay_per_replica: float=0.1):
        return int(self.config.steps * (delay_per_replica * self.config.replicas + self.config.cooldown))

    def run(self, timeout=99999):
        self.load_kube_config()
        self.check_namespace()
        experiment_list = []

        estimated_time = self.estimate_time()
        print(f"Experiment of {self.config.steps} step(s) with {self.config.replicas} replica(s) in '{self.config.framework}' and '{self.config.container_image}' image in namespace '{self.config.namespace}'. Estimated time for the experiment: {estimated_time} second(s)")

        def event_thread_deployment_fn(watcher_dict: dict):
            '''There is no need for locking watcher_dict, no concurrent access.'''
            w = watch.Watch()
            appsv1 = client.AppsV1Api()

            for event in w.stream(appsv1.list_namespaced_deployment, namespace=self.config.namespace):
                event_type = event['type']
                event_object = event['object'].to_dict()

                if not event_object['metadata']['name'] == self.config.deployment_name: continue

                if event_type == "ADDED":
                    watcher_dict['created_at'] = datetime.now()
                elif event_type == "DELETED":
                    watcher_dict['deleted_at'] = datetime.now()
                    w.stop()
                else:
                    watcher_dict['modified_at'].append(str(datetime.now()))
                    ready_replicas = event_object['status']['ready_replicas']
                    watcher_dict['ready_replica_counts'].append(ready_replicas)

        def event_thread_pods_fn(event_thread_pods: dict):
            '''There is no need for locking watcher_dict, no concurrent access.'''
            w = watch.Watch()
            v1 = client.CoreV1Api()

            pods_measurements = collections.defaultdict(dict)
            first_created_at = None 
            last_created_at = None
            first_deleted_at = None 
            last_deleted_at = None 
            number_of_pods = 0

            for event in w.stream(v1.list_namespaced_pod, namespace="experiments"):
                event_type = event['type']
                event_object = event['object'].to_dict()
        
                # if not event_object['metadata']['name'] == self.config.deployment_name: continue
        
                print(f"evet_type: {event_type}")
                # print(event_object.keys()) # 'api_version', 'kind', 'metadata', 'spec', 'status'
                pod_name = event_object["metadata"]["name"]

                if event_type == "ADDED":
                    pods_measurements[pod_name]["created_at"] = datetime.now()
                    number_of_pods += 1
                elif event_type == "DELETED":
                    pods_measurements[pod_name]["deleted_at"] = datetime.now()
                    pods_measurements[pod_name]["pods_started_time"] = event_object["status"]["start_time"]
                    number_of_pods -= 1
                if number_of_pods == 0: w.stop()
            
            for pod_name, dates in pods_measurements.items():
                first_created_at = dates["created_at"] if not first_created_at else min(first_created_at, dates["created_at"])
                last_created_at = dates["created_at"] if not last_created_at else max(last_created_at, dates["created_at"])
                first_deleted_at = dates["deleted_at"] if not first_deleted_at else min(first_deleted_at, dates["deleted_at"])
                last_deleted_at = dates["deleted_at"] if not last_deleted_at else max(last_deleted_at, dates["deleted_at"])
            
            event_thread_pods["first_created_at"] = first_created_at 
            event_thread_pods["last_created_at"] = last_created_at
            event_thread_pods["first_deleted_at"] = first_deleted_at 
            event_thread_pods["last_deleted_at"] = last_deleted_at 

        for s in range(self.config.steps):
            errors_rised = []
            watcher_dict = {
                'created_at': None,
                'deleted_at': None,
                'modified_at': [],
                'ready_replica_counts': [],
            }
            watcher_dict_pods = {}

            event_thread_deployment = threading.Thread(target=event_thread_deployment_fn, args=[watcher_dict,])
            event_thread_pods = threading.Thread(target=event_thread_deployment_fn, args=[watcher_dict_pods,])
            event_thread_deployment.start()
            event_thread_pods.start()
            time.sleep(0.5)
            # Wait until event thread is watching k8s api events.
            
            # CREATE
            before_create_timestamp = datetime.now()
            errors_rised.append(self.handler.create_deployment())

            # FIRST WAIT
            before_firstwait_timestamp = datetime.now()
            errors_rised.append(self.handler.wait_until_deployment_ready())
            time.sleep(1)

            # DELETE
            before_delete_timestamp = datetime.now()
            errors_rised.append(self.handler.delete_deployment())

            # # SECOND WAIT
            before_secondwait_timestamp = datetime.now()
            # errors_rised.append(self.wait_until_deployment_deleted())

            # COOLDOWN
            before_cooldown_timestamp = datetime.now()
            time.sleep(self.config.cooldown)

            # JOIN
            before_join_timestamp = datetime.now()
            event_thread_deployment.join(timeout=timeout)
            event_thread_pods.join(timeout=timeout)

            exception_occured = len([e for e in errors_rised if e != None]) != 0



            experiment_list.append(ExperimentRound(
                # Measurements of the experiment
                before_create_timestamp=before_create_timestamp,
                before_firstwait_timestamp=before_firstwait_timestamp,
                before_delete_timestamp=before_delete_timestamp,
                before_secondwait_timestamp=before_secondwait_timestamp,
                before_cooldown_timestamp=before_cooldown_timestamp,
                before_join_timestamp=before_join_timestamp,

                # Experiment metadata
                cool_period=self.config.cooldown,
                framework=self.config.framework,
                replicas=self.config.replicas,
                step=int(s), # Change this to round
                total_steps=self.config.steps, # total_round
                error_occured=exception_occured,
                errors_rised=[str(e) for e in errors_rised],
                driver=self.config.driver,
                command=self.config.container_command,

                # Event related measurements
                event_created_at=watcher_dict["created_at"],
                event_deleted_at=watcher_dict["deleted_at"],
                event_modified_at=watcher_dict["modified_at"],
                event_replicas_at=watcher_dict["ready_replica_counts"],

                # Pod measurements
                first_created_at=watcher_dict_pods["first_created_at"],
                last_created_at=watcher_dict_pods["last_created_at"],
                first_deleted_at=watcher_dict_pods["first_deleted_at"], 
                last_deleted_at=watcher_dict_pods["last_deleted_at"],
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

        if self.config.namespace in namespace_list:
            return

        try:
            v1.create_namespace(client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=self.config.namespace
                )
            ))
        except client.ApiException as e:
            return e

class NativeHandler(CreateDeleteHandler):
    def __init__(self, config: ExperimentConfig) -> None:
        super().__init__(config)

    def create_deployment(self):
        appsv1 = client.AppsV1Api()

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=self.config.deployment_name,
                labels={
                    'app': 'test'
                },
            ),
            spec=client.V1DeploymentSpec(
                replicas=self.config.replicas,
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
                                name=self.config.container_name,
                                image=self.config.container_image,
                                command=self.config.container_command
                            ),
                        ]
                    )
                )
            ))

        try:
            appsv1.create_namespaced_deployment(namespace=self.config.namespace, body=deployment)
        except client.ApiException as e:
            return e

    def delete_deployment(self):
        appsv1 = client.AppsV1Api()

        try:
            appsv1.delete_namespaced_deployment(name=self.config.deployment_name, namespace=self.config.namespace)
        except client.ApiException as e:
            return e

def get_handler_from(config, framework, driver):
    if framework == "native":
        if driver == "minikube" or driver == "native":
            return NativeHandler(config=config)
    raise NotImplementedError

class NativeKWOKHandler(NativeHandler):
    def __init__(self, config: ExperimentConfig) -> None:
        super().__init__(config)

    def create_deployment(self):
        appsv1 = client.AppsV1Api()

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=self.config.deployment_name,
                labels={
                    'app': 'fake'
                },
            ),
            spec=client.V1DeploymentSpec(
                replicas=self.config.replicas,
                selector=client.V1LabelSelector(
                    match_labels={
                        'app': 'fake',
                    },
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={
                            'app': 'fake',
                        },
                    ),
                    spec=client.V1PodSpec(
                        affinity=client.V1Affinity(
                            node_affinity=client.V1NodeAffinity(
                                required_during_scheduling_ignored_during_execution=client.V1NodeSelector(
                                    node_selector_terms=[
                                        client.V1NodeSelectorTerm(
                                            match_expressions=[
                                                client.V1NodeSelectorRequirement(
                                                    key="type",
                                                    operator="In",
                                                    values=[
                                                        "kwok"
                                                    ]
                                                ),
                                            ]
                                        )
                                    ]
                                ),
                            ),
                        ),
                        tolerations=[
                            client.V1Toleration(
                                key="kwok.x-k8s.io/node",
                                operator="Exists",
                                effect="NoSchedule"
                            )
                        ],
                        containers=[
                            client.V1Container(
                                name=self.config.container_name,
                                image=self.config.container_image,
                                command=self.config.container_command
                            ),
                        ]
                    )
                )
            ))

        try:
            appsv1.create_namespaced_deployment(namespace=self.config.namespace, body=deployment)
        except client.ApiException as e:
            return e

def get_handler_from(config, framework, driver):
    if framework == "native":
        if driver == "minikube" or driver == "native":
            return NativeHandler(config=config)
        elif driver == "kwok":
            return NativeKWOKHandler(config=config)
    raise NotImplementedError

def experiment_with(framework, driver, num_step, replica_list, cooldown_list):
    experiment_objects = []
    for replica, cooldown in zip(replica_list, cooldown_list):
        config = ExperimentConfig(
            framework=framework, 
            driver=driver, 
            replicas=replica, 
            steps=num_step, 
            cooldown=cooldown, 
            container_command=["/bin/sh", "-c", "sleep 9999"])
        
        handler = get_handler_from(config=config, framework=framework, driver=driver)
        experiment_objects.append(Experimenter(config=config, handler=handler))

    filename = generate_feather_name()
    total_time_reuired = sum([k.estimate_time() for k in experiment_objects])
    
    print(f"Estimated time {total_time_reuired} second(s) will be saved in '{filename}'.")

    for experiment in experiment_objects:        
        results = experiment.run()
        results_df = pd.DataFrame(results)
        append_to_feather(filename, results_df)

    print("Done!")

if __name__ == "__main__":
    experiment_with("native", "minikube", 1, [1], [1])
    # config.load_kube_config()
    # w = watch.Watch()
    # v1 = client.CoreV1Api()

    # pods_measurements = collections.defaultdict(dict)
    # first_created_at = None 
    # last_created_at = None
    # first_deleted_at = None 
    # last_deleted_at = None 
    # number_of_pods = 0

    # try:
    #     for event in w.stream(v1.list_namespaced_pod, namespace="experiments"):
    #         event_type = event['type']
    #         event_object = event['object'].to_dict()
    
    #         # if not event_object['metadata']['name'] == self.config.deployment_name: continue
    
    #         print(f"evet_type: {event_type}")
    #         # print(event_object.keys()) # 'api_version', 'kind', 'metadata', 'spec', 'status'
    #         pod_name = event_object["metadata"]["name"]

    #         if event_type == "ADDED":
    #             pods_measurements[pod_name]["created_at"] = datetime.now()
    #             number_of_pods += 1
    #         elif event_type == "DELETED":
    #             pods_measurements[pod_name]["deleted_at"] = datetime.now()
    #             pods_measurements[pod_name]["pods_started_time"] = event_object["status"]["start_time"]
    #             number_of_pods -= 1
    #         if number_of_pods == 0: w.stop()
        
    #     for pod_name, dates in pods_measurements.items():
    #         first_created_at = dates["created_at"] if not first_created_at else min(first_created_at, dates["created_at"])
    #         last_created_at = dates["created_at"] if not last_created_at else max(last_created_at, dates["created_at"])
    #         first_deleted_at = dates["deleted_at"] if not first_deleted_at else min(first_deleted_at, dates["deleted_at"])
    #         last_deleted_at = dates["deleted_at"] if not last_deleted_at else max(last_deleted_at, dates["deleted_at"])

    #     # print(first_created_at, last_created_at)
    #     # print(first_deleted_at, last_deleted_at)
            
    # except KeyboardInterrupt:
    #     ...

    # print(pods_measurements)