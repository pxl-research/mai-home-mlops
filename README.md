# MAI Home MLOps pipeline

Currently loose experiments which will turn in a fully working MLOps pipeline on Azure taking IaC from Happy@Home when applicable.

TODO list:
* ONLY USE AZURE BLOB STORAGE OR ADLS FOR BACKUP (save InfluxDB data locally in volume in container in VM and let InfluxDB handle the rest):
Configuring InfluxDB 3.0 to use Azure Blob Storage as long-term persistence with a local cache in VM for real-time operations is a core feature of its architecture. This is a hybrid approach that combines the high performance of local storage for recent data with the cost-effective, scalable nature of object storage for historical data.
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

* Model registry and experiment tracking:
    ```
    -- generic training runs (experiments or retraining)
    CREATE TABLE runs (
      run_id SERIAL PRIMARY KEY,
      run_type TEXT NOT NULL,          -- ['manual', 'auto_retrain']
      created_at TIMESTAMP DEFAULT NOW(),
      git_commit_hash VARCHAR(40),     -- Needs commit (only locally) before saving to database, in production take last saved commit hash from .env file written by CI/CD
      dvc_hash TEXT
    );
    
    -- separate table to keep runs table more lightweight since JSONB can be big
    CREATE TABLE run_details (
      run_id INT PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
      training_script_path TEXT NULL,             -- only for manual runs, nullable for auto
      scheduled_at TIMESTAMP NULL,                -- only for auto runs, nullable for manual

      train_start_timestamp TIMESTAMP,
      train_end_timestamp TIMESTAMP,
      validation_start_timestamp TIMESTAMP NULL,  -- only for manual runs, nullable for auto
      validation_end_timestamp TIMESTAMP NULL,    -- only for manual runs, nullable for auto
      test_start_timestamp TIMESTAMP NULL,        -- only for manual runs, nullable for auto
      test_end_timestamp TIMESTAMP NULL,          -- only for manual runs, nullable for auto

      train_metrics JSONB,                        -- (e.g., {'rmse': 12.5})
      validation_metrics JSONB NULL,              -- only for manual runs, nullable for auto
      test_metrics JSONB NULL,                    -- only for manual runs, nullable for auto

      input_features JSONB,                       -- list of feature names
      target_features JSONB,                      -- list of feature names
      hyperparameters JSONB,                      -- list of feature names
      metadata JSONB,                             -- dict of use-case specific metadata, e.g. {"household_id_list": []}
    );

    -- promoted models
    CREATE TABLE model_registry (
      model_id SERIAL PRIMARY KEY,
      name TEXT NOT NULL,                     -- model name
      type TEXT DEFAULT 'none',               -- ['none', 'predictive_maintainance', ...]
      stage TEXT DEFAULT 'none',              -- ['none', 'staging', 'production', 'archived']
      description TEXT,
      created_at TIMESTAMP DEFAULT NOW(),
      model_path TEXT,                        -- local or on cloud (prefix gets chosen automatically if local or on cloud and is not stored in database, only the part after)

      run_id INT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE, -- links back to any run (only auto in practice but by design can be auto or manual)
      deployment_info JSONB                   -- {'endpoint': '...', 'deployed_at': '2025-09-13T12:00'}
    );

    -- Optional indexes:
    CREATE INDEX idx_model_registry_type_stage ON model_registry(type, stage);
    CREATE INDEX idx_runs_created_at ON runs(created_at);

    # Keep only last 5 models per type
    import os
    import psycopg2
    work_environment = os.getenv("WORK_ENVIRONMENT")
    if work_environment == "production":
        # Azure Blob client setup
        from azure.storage.blob import BlobServiceClient
        connection_string = "<your-azure-blob-connection-string>"
        container_name = "<your-container-name>"
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)

    conn = psycopg2.connect("dbname=mlops user=postgres password=secret")
    cur = conn.cursor()

    # Step 1: Get model paths to delete
    cur.execute("""
    WITH to_delete AS (
        SELECT model_id, model_path
        FROM model_registry
        WHERE type = 'predictive_maintainance'
        ORDER BY created_at DESC
        OFFSET 5
    )
    DELETE FROM model_registry
    WHERE model_id IN (SELECT model_id FROM to_delete)
    RETURNING model_path;
    """)

    paths_to_delete = [row[0] for row in cur.fetchall()]

    # Step 2: Delete files locally (development) or Azure Blob Storage (production)
    if work_environment == "production":
        for blob_path in paths_to_delete:
            try:
                container_client.delete_blob(blob_path) # TODO: might want to add correct prefix
                print(f"Deleted Azure blob: {blob_path}")
            except Exception as e:
                print(f"Failed to delete blob {blob_path}: {e}")
    else:
        for path in paths_to_delete:
            try:
                os.remove(path)
                print(f"Deleted local model: {path}")
            except FileNotFoundError:
                print(f"File not found, skipping: {path}")

    conn.commit()
    cur.close()
    conn.close()
    ```

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