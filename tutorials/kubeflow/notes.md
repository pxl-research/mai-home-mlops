# Kubeflow notes

Prepare data => Create and store features (Feast) => Retrieve features => Model Development => Train model & Hyperparameter Tuning => Register model (Kubeflow Model Registry) => Serve model (KServe)

Full pipeline:
https://github.com/hbelmiro/fraud_detection_e2e_demo/blob/kubeflow/pipeline/fraud-detection-e2e.py


* Analyse prediction results and model behavior.
* Iterating on data preparation and validation strategies
* Reproducible experiments.
* Automatic scaling without code changes.
* Portable local and cloud agnostic.

Uiteindelijk IaC for Kubernetes doen via OpenTofu provider for kind:
https://search.opentofu.org/provider/marcwickenden/kind/latest

Install standalone Kubeflow Pipelines:
https://www.kubeflow.org/docs/components/pipelines/operator-guides/installation/#deploying-kubeflow-pipelines
* each step of a pipeline runs inside a container
* Use custom container images for each component:
    * docker-compose.yml file to kubernetes yml files via: kompose convert (do this 1 time only if needed) and then 
    kubectl apply -f my_new_file.yaml,my_other.yaml,...
    (do this in OpenTofu)
* Build each container image (instead use docker compose build):
    docker build -t mai-home-data-preparation:latest .
* Push container images:

Install Azure CLI
NOTE: use Azurite instead of MinIO for local blob storage emulation. (Only for Blob Storage, not Data Lake Storage Gen2!)
https://medium.com/@khuongntrd/emulating-azure-storage-with-azurite-on-kubernetes-7839c6352ed6
Make sure to couple the local data folder with this pod:
* create the required bucket and directory structure in Azurite and upload your raw datasets, making them available for the pipeline. (tight coupling is preferred)


Create cluster:
kind create cluster -n mai-home-cluster --image kindest/node:v1.34.0

Install Model registry:
kubectl apply -k "https://github.com/kubeflow/model-registry/manifests/kustomize/overlays/db?ref=v0.2.16"


Feast feature store commands (instead use Azurite as coupling):
https://github.com/hbelmiro/fraud_detection_e2e_demo/blob/kubeflow/feature_engineering/feast_feature_engineering.py
https://github.com/hbelmiro/fraud_detection_e2e_demo/tree/kubeflow/feature_engineering/feature_repo


Model training and uploading (instead use Azurite as coupling and pickle or scikit-ONNX):
https://github.com/hbelmiro/fraud_detection_e2e_demo/blob/kubeflow/train/train.py

# References:
https://github.com/hbelmiro/fraud_detection_e2e_demo/tree/kubeflow