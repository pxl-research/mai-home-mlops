# MAI Home MLOps pipeline

Currently loose experiments which will turn in a fully working MLOps pipeline on Azure taking IaC from Happy@Home when applicable.

TODO list:

* Use OpenBao instead of Vault.
* Make Vault not in-memory but instead use Docker volume for persistent key storage.
* InfluxDB 3 from experiment to working transform pipeline.
* InfluxDB 3 with Azure Data Lake Storage.
* FastStream with rabbitmq backend for streaming from IoT to Transform.
* ...
* The rest of the pipeline.
* Actual machine learning.
* Profit?

## Dependencies

Linux (Ubuntu) as OS or Ubuntu in WSL2 on Windows or Ubuntu VM on MacOS.

### Azure CLI
[Install the Azure CLI on Linux](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-linux?view=azure-cli-latest&pivots=apt)

### OpenTofu
[Install OpenTofu for infrastructure-as-code on Linux](https://opentofu.org/docs/intro/install/deb/)

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