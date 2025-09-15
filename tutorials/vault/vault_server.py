# filename: server.py

"""
pip install fastapi "uvicorn[standard]" hvac cryptography requests

docker pull quay.io/openbao/openbao:2.4.1


docker volume create vault_data

docker run -d --name=prod-vault --cap-add=IPC_LOCK -p 8200:8200 -v vault_data:/vault/file quay.io/openbao/openbao:2.4.1 > /dev/null \
&& sleep 5 \
&& docker logs prod-vault 2>&1 | awk '/Unseal Key:/ {uk = $3} /Root Token:/ {rt = $3; printf "{\n\"unseal_key\": \"%s\",\n\"root_token\": \"%s\"\n}\n", uk, rt; exit}'

# Output:
{
"unseal_key": "S81vt6Xq8713jX/aNci6l4K5ISO941cfGFgThHTb42g=",
"root_token": "s.f0ciVdiezWCysBn40qiYptLq"
}


# Environment variables
export BAO_UNSEAL_KEY="S81vt6Xq8713jX/aNci6l4K5ISO941cfGFgThHTb42g="
export BAO_ADDR="http://127.0.0.1:8200"
export BAO_TOKEN="s.f0ciVdiezWCysBn40qiYptLq"


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
import os
import asyncio
from typing import Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, status, Depends
import hvac

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
# You can set these in a .env file
BAO_ADDR = os.environ.get("BAO_ADDR", "http://127.0.0.1:8200")
BAO_TOKEN = os.environ.get("BAO_TOKEN", "dev-only-token")
BAO_SECRET_PATH = os.getenv("BAO_SECRET_PATH", "kv/data/my-service/fernet-key")
API_KEY = os.getenv("API_KEY")

app = FastAPI()

# --- Global Components ---
# Create a mutex lock for thread-safe access to the OpenBao client
vault_lock = asyncio.Lock()

# Initialize the OpenBao client at startup
try:
    # Correctly initialize the client with the OpenBao address and token
    vault_client = hvac.Client(url=BAO_ADDR, token=BAO_TOKEN)
    if not vault_client.is_authenticated():
        raise ValueError("OpenBao client is not authenticated. Check your BAO_TOKEN.")
except Exception as e:
    print(f"Error connecting to OpenBao: {e}")
    # Instead of `exit()`, it's better to let FastAPI handle the startup failure
    raise RuntimeError("Failed to connect to OpenBao on startup.") from e

# Dependency to validate the API Key
def validate_api_key(x_api_key: str = Header(..., convert_underscores=False)):
    """Validates the API key provided in the 'X-Api-Key' header."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")
    return x_api_key


# --- API Endpoints ---
@app.post("/api/vault/store_key/")
async def store_key(data: dict[str, str], api_key: str = Depends(validate_api_key)) -> dict[str, str]:
    """
    Accepts a secret key and stores it in OpenBao.
    Uses an asyncio.Lock to prevent concurrent write operations.
    """
    key_name = list(data.keys())[0]
    secret_key = data.get(key_name)
    
    if not secret_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No 'secret_key' provided.")
    
    try:
        async with vault_lock:
            # Use asyncio.to_thread() to run the blocking hvac operation
            await asyncio.to_thread(
                vault_client.secrets.kv.v2.create_or_update_secret,
                path=f"{BAO_SECRET_PATH}{key_name}",
                secret={key_name: secret_key}
            )
        return {"message": "Key stored successfully in OpenBao."}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to store key: {str(e)}")


@app.get("/api/vault/get_key/{key_name}")
async def get_key(key_name: str, api_key: str = Depends(validate_api_key)) -> dict[str, str]:
    """
    Retrieves a specific key from OpenBao by its name.
    """

    try:
        async with vault_lock:
            read_response = await asyncio.to_thread(
                vault_client.secrets.kv.v2.read_secret_version,
                path=f"{BAO_SECRET_PATH}{key_name}"
            )
        
        # Access the nested data for KV v2 secrets
        if read_response and "data" in read_response and "data" in read_response["data"]:
            # Retrieve all key-value pairs stored in the secret
            secret_data = read_response["data"]["data"]
            return secret_data

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Secret '{key_name}' not found.")
    except hvac.exceptions.InvalidRequest:
        # This exception is raised by hvac if the path doesn't exist
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Secret '{key_name}' not found at the specified path.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve key: {str(e)}")


@app.get("/api/vault/list_keys")
async def list_keys(api_key: str = Depends(validate_api_key)) -> dict[str, Any]:
    """
    Retrieves a list of all secrets (keys) at the specified path.
    """
    # The path for listing secrets needs to be the directory, not the full secret path
    list_path = os.path.dirname(BAO_SECRET_PATH)
    if not list_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="VAULT_SECRET_PATH is a single file and cannot be listed. Provide a valid path like 'kv/data/my-service/'.")
    
    try:
        async with vault_lock:
            list_response = await asyncio.to_thread(
                vault_client.secrets.kv.v2.list_secrets,
                path=list_path
            )
        
        # Correctly access the data
        if list_response and "data" in list_response and "keys" in list_response["data"]:
            keys_list = list_response["data"]["keys"]
            return {"keys": keys_list}
        
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No keys found in path '{list_path}'.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list keys: {str(e)}")


@app.delete("/api/vault/delete_key/{key_name}")
async def delete_key(key_name: str, api_key: str = Depends(validate_api_key)) -> dict[str, str]:
    """
    Deletes the stored key from OpenBao.
    """
    try:
        async with vault_lock:
            await asyncio.to_thread(
                vault_client.secrets.kv.v2.delete_latest_version_of_secret,
                path=f"{BAO_SECRET_PATH}{key_name}"
            )
        return {"message": "Key deleted successfully from OpenBao."}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete key: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # The `uvicorn.run` command needs the module and app object, e.g., "your_file_name:app"
    uvicorn.run("vault_server:app", host="0.0.0.0", port=8080, reload=False)