from datetime import datetime
import pandas as pd 
from dataclasses import dataclass

@dataclass
class ExperimentRound():
    # First time the experiment started
    experiment_start_date: datetime

    # The time experiment finished
    experiment_finsh_date: datetime

    # When the deployments becomes ready
    experiment_deployment_becoma_ready_date: datetime

    # Start and finish dates of deployment creation
    experiment_deployment_creation_started_date: datetime
    experiment_deployment_creation_finished_date: datetime

    # Start and finish dates of deplotment deletion
    experiment_deployment_deletion_started_date: datetime
    experiment_deployment_deletion_finished_date: datetime

    # Number of replicas
    replicas: int

    # Name of the federation framework
    framework: str 

    # If any error occured
    error_occured: bool

    # Kubernetes API exception (string representation)
    exception: str

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
