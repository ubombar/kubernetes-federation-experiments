# How to Create a KWOK Cluster?
There exists wonderful documentation for Kwok. It can be found on the official Kwok [website](https://kwok.sigs.k8s.io/docs/user/kwok-manage-nodes-and-pods/).

## Installation
To install KWOK, first install the kwokctl and kwok executables. They can be installed on Linux systems by downloading the specified commands. They will install the executables into your system.

```sh
KWOK_REPO=kubernetes-sigs/kwok

KWOK_LATEST_RELEASE=$(curl "https://api.github.com/repos/${KWOK_REPO}/releases/latest" | jq -r '.tag_name')

wget -O kwokctl -c "https://github.com/${KWOK_REPO}/releases/download/${KWOK_LATEST_RELEASE}/kwokctl-$(go env GOOS)-$(go env GOARCH)"

chmod +x kwokctl

sudo mv kwokctl /usr/local/bin/kwokctl

wget -O kwok -c "https://github.com/${KWOK_REPO}/releases/download/${KWOK_LATEST_RELEASE}/kwok-$(go env GOOS)-$(go env GOARCH)"

chmod +x kwok

sudo mv kwok /usr/local/bin/kwok
```

## Cluster Creation
Then you have to create a cluster. To do this you can use the kwokctl utility with the following command. You then have to set the kubectl context. Note that this cluster's name is `default`. It can be changed.

```sh
kwokctl create cluster --name=default

kubectl config use-context kwok-default
```

## Adding Fake Nodes
By simply creating `v1.Node` objects in the kube-apiserver, you can add fake nodes. Note that the `kwok.x-k8s.io/node: fake` annotation should be added. The following command adds a fake node to the cluster.

```sh
kubectl apply -f - <<EOF
apiVersion: v1
kind: Node
metadata:
  annotations:
    node.alpha.kubernetes.io/ttl: "0"
    kwok.x-k8s.io/node: fake
  labels:
    beta.kubernetes.io/arch: amd64
    beta.kubernetes.io/os: linux
    kubernetes.io/arch: amd64
    kubernetes.io/hostname: kwok-node-0
    kubernetes.io/os: linux
    kubernetes.io/role: agent
    node-role.kubernetes.io/agent: ""
    type: kwok
  name: kwok-node-0
spec:
  taints: # Avoid scheduling actual running pods to fake Node
    - effect: NoSchedule
      key: kwok.x-k8s.io/node
      value: fake
status:
  allocatable:
    cpu: 32
    memory: 256Gi
    pods: 110
  capacity:
    cpu: 32
    memory: 256Gi
    pods: 110
  nodeInfo:
    architecture: amd64
    bootID: ""
    containerRuntimeVersion: ""
    kernelVersion: ""
    kubeProxyVersion: fake
    kubeletVersion: fake
    machineID: ""
    operatingSystem: linux
    osImage: ""
    systemUUID: ""
  phase: Running
EOF
```

## Creating Deployments
Then you can create deployments with the following command. Note that you have to specify `nodeAffinity` and its subsections accordingly to make sure this deployment runs in the fake node we created.


```sh
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fake-pod
  namespace: default
spec:
  replicas: 10
  selector:
    matchLabels:
      app: fake-pod
  template:
    metadata:
      labels:
        app: fake-pod
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: type
                    operator: In
                    values:
                      - kwok
      # A taints was added to an automatically created Node.
      # You can remove taints of Node or add this tolerations.
      tolerations:
        - key: "kwok.x-k8s.io/node"
          operator: "Exists"
          effect: "NoSchedule"
      containers:
        - name: fake-container
          image: fake-image
EOF
```