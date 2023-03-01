# KWOK Guide
## Adding a Real Node 
Sometimes we need a real node to test specific components. This part will show how to add (similar to `minikube node add`).

There are many methods to add a container to the cluster as a worker node. For simplicity we will create a minikube node and add it to our kwok cluster.

These ports are used by the kubernetes so they should be open. These ports are opened by default if you use minikube.
```
Port            Protocol    Purpose
10250 	        TCP         This port is used for Kubelet API
30000-32767     TCP         NodePort Services
179             TCP         Calico networking (BGP)
```

```sh
minikube node add 
```

This command will create a node and adds it to the cluster. If we `kubectl get nodes minikub-m02 -o yaml` we get the following. Note that minikube-m02 is the default name of the node we added. It can change. 

```yaml
apiVersion: v1
kind: Node
metadata:
  annotations:
    kubeadm.alpha.kubernetes.io/cri-socket: /var/run/cri-dockerd.sock
    node.alpha.kubernetes.io/ttl: "0"
    volumes.kubernetes.io/controller-managed-attach-detach: "true"
  creationTimestamp: "2023-03-01T13:07:51Z"
  labels:
    beta.kubernetes.io/arch: amd64
    beta.kubernetes.io/os: linux
    kubernetes.io/arch: amd64
    kubernetes.io/hostname: minikube-m02
    kubernetes.io/os: linux
  name: minikube-m02
  resourceVersion: "239970"
  uid: aeab790d-7b0e-4c7d-a093-749e3ffa44b1
spec:
  podCIDR: 10.244.1.0/24
  podCIDRs:
  - 10.244.1.0/24
```

> TODO: Make a better tutorial