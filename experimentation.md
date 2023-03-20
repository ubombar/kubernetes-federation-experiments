# Experimentation
## Creating a Minikube Cluster and Running the Experiment
We create a regular cluster on our VM. VM has 16Gb of memory and 8 CPUs. We will give 12Gb and 7CPUs to the minikube cluster.

```sh
    minikube start --cpus='7' --memory='12g'
```

Then we will start the experimenter to save all of the data it received.

```sh
    python ./scripts/minikube.py 
```
