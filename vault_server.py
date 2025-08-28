# filename: server.py

"""
pip install fastapi "uvicorn[standard]" hvac cryptography requests

docker pull hashicorp/vault


docker volume create vault_data

docker run -d --name=prod-vault --cap-add=IPC_LOCK -p 8200:8200 -v vault_data:/vault/file hashicorp/vault > /dev/null \
&& sleep 5 \
&& docker logs prod-vault 2>&1 | awk '/Unseal Key:/ {uk = $3} /Root Token:/ {rt = $3; printf "{\n\"unseal_key\": \"%s\",\n\"root_token\": \"%s\"\n}\n", uk, rt; exit}'

# Output:
{
"unseal_key": "/x3WBUtblwfRSXfCnc9WtrGnCxuF0FXzlVFXqYHEG48=",
"root_token": "hvs.ezrUIHcHPmLTZsfrhlbdvJsO"
}


# Environment variables
export VAULT_UNSEAL_KEY="/x3WBUtblwfRSXfCnc9WtrGnCxuF0FXzlVFXqYHEG48="
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="hvs.ezrUIHcHPmLTZsfrhlbdvJsO"


# Unseal
docker exec prod-vault vault operator unseal -address=$VAULT_ADDR $VAULT_UNSEAL_KEY

# Seal (only do this on shutdown)
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=$VAULT_TOKEN prod-vault vault operator seal




docker stop prod-vault
docker rm prod-vault
docker volume rm vault_data
"""


"""
This script sets up a FastAPI server that uses the `hvac` library to
store, retrieve, and delete secrets from a HashiCorp Vault server.

Prerequisites:
- A running HashiCorp Vault server.
- The hvac library installed: pip install hvac
- Environment variables VAULT_ADDR and VAULT_TOKEN must be set.
"""

from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import asyncio
import hvac
import os
import uvicorn

# Define the path where the secret will be stored in Vault's KV v2 engine.
VAULT_SECRET_PATH = "my-fastapi-app/secret-key"

app = FastAPI()

# Create a mutex lock to ensure that Vault operations are thread-safe.
vault_lock = asyncio.Lock()

# Initialize the hvac client outside the endpoints to avoid creating a new one on every request.
try:
    vault_client = hvac.Client()
    if not vault_client.is_authenticated():
        raise ValueError("Vault client is not authenticated. Check your VAULT_TOKEN.")
except Exception as e:
    # If the connection fails on startup, log the error and exit.
    print(f"Error connecting to Vault: {e}")
    exit()

@app.post("/api/store_key")
async def store_key(data: Dict[str, str]) -> Dict[str, str]:
    """
    Accepts a Fernet key, then stores it in Vault.
    Uses an asyncio.Lock to prevent concurrent write operations.
    """
    secret_key = data.get("secret_key")

    if not secret_key:
        raise HTTPException(status_code=400, detail="No secret_key provided.")

    try:
        async with vault_lock:
            # Use asyncio.to_thread() to run the blocking hvac operation.
            await asyncio.to_thread(
                vault_client.secrets.kv.v2.create_or_update_secret,
                path=VAULT_SECRET_PATH,
                secret={'secret_key': secret_key}
            )
        return {"message": "Key stored successfully in Vault."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store key: {str(e)}")

@app.get("/api/get_key")
async def get_key() -> Dict[str, str]:
    """
    Retrieves the stored key from Vault.
    Uses an asyncio.Lock to prevent concurrent read operations.
    """
    try:
        async with vault_lock:
            # Use asyncio.to_thread() to run the blocking hvac operation.
            read_response = await asyncio.to_thread(
                vault_client.secrets.kv.v2.read_secret_version,
                path=VAULT_SECRET_PATH
            )
        
        # Access the key. For KV v2, the data is nested under ['data']['data'].
        if read_response and 'data' in read_response and 'data' in read_response['data']:
            retrieved_key = read_response['data']['data'].get('secret_key')
            if retrieved_key:
                return {"retrieved_key": retrieved_key}

        raise HTTPException(status_code=404, detail="Key not found in Vault.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve key: {str(e)}")

@app.delete("/api/delete_key")
async def delete_key() -> Dict[str, str]:
    """
    Deletes the stored key from Vault.
    """
    try:
        async with vault_lock:
            # Use asyncio.to_thread() to run the blocking hvac operation.
            await asyncio.to_thread(
                vault_client.secrets.kv.v2.delete_latest_version_of_secret,
                path=VAULT_SECRET_PATH
            )
        return {"message": "Key deleted successfully from Vault."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete key: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("vault_server:app", host="0.0.0.0", port=8080, reload=False)
