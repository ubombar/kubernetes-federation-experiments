from datetime import datetime
import pandas as pd 
from dataclasses import dataclass
import os

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

def append_to_feather(filename, new_df):
    if not os.path.exists(filename):
        empty_df = pd.DataFrame({"test": []})
        empty_df.to_feather(filename)

    old_df: pd.DataFrame = pd.read_feather(filename)

    big_df = pd.concat([old_df, new_df], ignore_index=True)
    # old_df.append(new_df, ignore_index=True)

    big_df.to_feather(filename)

def generate_feather_name():
    current_date = datetime.now()
    return f"./exps/{str(current_date).split('.')[0].replace(' ', '_').replace('-', '').replace(':', '')}.feather"

# filename1 = "/home/manus/Documents/Development/go/github.com/ubombar/kubernetes-federation-experiments/exps/20230223_145305.feather"
# filename2 = "/home/manus/Documents/Development/go/github.com/ubombar/kubernetes-federation-experiments/exps/20230223_145004.feather"

# old_df: pd.DataFrame = pd.read_feather(filename1)
# new_df: pd.DataFrame = pd.read_feather(filename2)

# big_df = old_df.append(new_df)

# print(big_df)