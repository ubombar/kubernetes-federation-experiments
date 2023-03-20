import numpy as np 
import matplotlib.pyplot as plt 
import seaborn as sns 
import experimenter
import pandas as pd 
import matplotlib.pyplot as plt 

# Maximum number of replicas that the system can manage.
# MAX_REPLICA_COUNT = 100

# Number of experiments
# NUMBER_OF_EXPERIMENTS = 5

# Each experiment will be done by this many times for consistency.
EXPERIMENT_REPITITION = 5 

# Int array of replicas for each experiment
# REPLICAS: np.ndarray = experimenter.calculate_number_of_replicas(MAX_REPLICA_COUNT, NUMBER_OF_EXPERIMENTS)
REPLICAS = np.array([1, 5, 20])

# How much should we wait for the kubernetes api to be stabilized
# COOLDOWNS: np.ndarray = 2 * np.ones((NUMBER_OF_EXPERIMENTS,), dtype=int) + (REPLICAS * 0.004).astype(int) # Make it ~3 mins
COOLDOWNS = np.array([3, 3, 3])

# Namespace of the experimentation
NAMESPACE = "experiments"

# Driver used in kubectl
DRIVER = "minikube" # minikube, kwok, native

# Framework
FRAMEWORK = "native" # native, edgenet (Nisan ortasi) | liqo, kubefed (Sonradan)
# EdgeNet scalability test, how many compute cluster can be tested...

filename = experimenter.experiment_with(FRAMEWORK, DRIVER, EXPERIMENT_REPITITION, REPLICAS.tolist(), COOLDOWNS.tolist())
# filename = experimenter.experiment_with(FRAMEWORK, DRIVER, 1, [1], [1])

print(filename)