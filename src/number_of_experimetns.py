import numpy as np 

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
        
