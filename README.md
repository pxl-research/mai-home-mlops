# MAI Home MLOps pipeline

Currently loose experiments which will turn in a fully working MLOps pipeline on Azure taking IaC from Happy@Home when applicable.

TODO list:
* Add Experiment Tracking to flowchart.
* ONLY USE AZURE BLOB STORAGE OR ADLS FOR BACKUP (save InfluxDB data locally in volume in container in VM and let InfluxDB handle the rest):
Configuring InfluxDB 3.0 to use Azure Blob Storage as long-term persistence with a local cache in VM for real-time operations is a core feature of its architecture. This is a powerful, hybrid approach that combines the high performance of local storage for recent data with the cost-effective, scalable nature of object storage for historical data.
https://www.influxdata.com/blog/azure-blob-storage-influxdb/
Then use DVC on the object store (not in the VM).
```
influxdb3 serve \
    --object-store=azure \
    --node-id=azure01 \
    --cluster-id=cluster01 \
    --wal-flush-interval=1s \
    --azure-storage-access-key="YOUR_ACCESS_KEY" \
    --azure-storage-account=influxdb3blobstorage \
    --bucket=influxdb3-data
```
Approximately every 10 minutes, the contents of the queryable buffer are persisted to Parquet files in your Azure Blob Storage container.

* For DVC: After your pg_parquet script creates a new Parquet file locally, you can use the DVC Python API to add this file to DVC's tracking system and then push it to your Azure Blob Storage remote. (Given that DVC is initialized as using Azure Blob Storage as a remote backend.)

* Use OpenBao instead of HashiCorp Vault.
* Make vault not in-memory but instead use Docker volume for persistent key storage.
* InfluxDB 3 from tutorial to working ingest flow.
* InfluxDB 3 with Azure Data Lake Storage.
* FastStream with Redis backend for streaming from IoT to ingest flow, simulate this (initial bulk ingest from CSV), then real-time streaming to InfluxDB in local VM storage (async in background to blob storage).
* ...
* The rest of the pipeline.
* Actual machine learning.
* Profit?

## Dependencies

Linux (Ubuntu) as OS or Ubuntu in WSL2 on Windows or Ubuntu VM on MacOS.

### Git
Install Git on Linux
```
sudo su
add-apt-repository ppa:git-core/ppa
apt update; apt install git
```

### Docker
[Install Docker on Linux](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)

### Azure CLI

[Install the Azure CLI on Linux](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-linux?view=azure-cli-latest&pivots=apt)

### OpenTofu

[Install OpenTofu for infrastructure-as-code on Linux](https://opentofu.org/docs/intro/install/deb/)


### DVC
Install DVC for version control for data.
```
wget https://downloads.dvc.org/deb/pool/stable/d/dv/dvc_3.63.0_amd64.deb -O dvc.deb && sudo dpkg -i dvc.deb
```

### Pipeline orchestration

#### minikube

[Install minikube for local single-node cluster (in development)](https://minikube.sigs.k8s.io/docs/start/?arch=%2Fwindows%2Fx86-64%2Fstable%2F.exe+download)

```
curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
minikube start
```

#### Metaflow
```
pip install metaflow # or: pip install --upgrade metaflow
metaflow-dev up
```

## Infrastructure set up

First time initialization:

```
az login --use-device-code
az account show --query id --output tsv
export ARM_SUBSCRIPTION_ID="ENTER YOUR SUBSCRIPTION ID"
cd src/infrastructure
tofu init
```

Add changes in infrastructure:

```
tofu plan
tofu apply
```

Destroy architecture:

```
tofu destroy
```

## Appendix: Kubeflow
Although we do not use Kubeflow due to it being more heavyweight than Metaflow, we provide the following installation guide.
One can adjust the yaml file in the manifests folder to exclude certain Kubeflow components.

### kubectl

```
sudo apt install snapd
sudo snap install kubectl --classic
alias kubectl="minikube kubectl --"
```

### kustomize
```
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh"  | bash
sudo install kustomize /usr/local/bin/kustomize && rm kustomize
```

### Kubeflow

[Install with a single command](https://github.com/kubeflow/manifests?tab=readme-ov-file#install-with-a-single-command)
```
[ $(uname -m) = x86_64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.30.0/kind-linux-amd64
sudo mv ./kind /usr/local/bin/kind

cat <<EOF | kind create cluster --name=kubeflow --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  image: kindest/node:v1.32.0@sha256:c48c62eac5da28cdadcf560d1d8616cfa6783b58f0d94cf63ad1bf49600cb027
  kubeadmConfigPatches:
  - |
    kind: ClusterConfiguration
    apiServer:
      extraArgs:
        "service-account-issuer": "https://kubernetes.default.svc"
        "service-account-signing-key-file": "/etc/kubernetes/pki/sa.key"
EOF

kind get kubeconfig --name kubeflow > /tmp/kubeflow-config

docker login

kubectl create secret generic regcred \
    --from-file=.dockerconfigjson=$HOME/.docker/config.json \
    --type=kubernetes.io/dockerconfigjson

while ! kustomize build example | kubectl apply --server-side --force-conflicts -f -; do echo "Retrying to apply resources"; sleep 20; done


kubectl port-forward svc/istio-ingressgateway -n istio-system 8080:80
# Go to http://localhost:8080

Log in with the default user's credentials. The default email address is user@example.com, and the default password is 12341234.
```