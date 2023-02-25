from datetime import datetime
import pandas as pd 
from dataclasses import dataclass
import os

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