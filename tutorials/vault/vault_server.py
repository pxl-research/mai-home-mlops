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
"unseal_key": "J3TCOHtFZ6Zik88Lq/0Gb6oylkfoTkZpmaCEZ96dOxU=",
"root_token": "s.91QdcVjUTFTcRPjQg2gpXN7z"
}


# Environment variables
export BAO_UNSEAL_KEY="J3TCOHtFZ6Zik88Lq/0Gb6oylkfoTkZpmaCEZ96dOxU="
export BAO_ADDR="http://127.0.0.1:8200"
export BAO_TOKEN="s.91QdcVjUTFTcRPjQg2gpXN7z"


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
BAO_ADDR = os.environ.get("BAO_ADDR", "http://127.0.0.1:8200")
BAO_TOKEN = os.environ.get("BAO_TOKEN", "dev-only-token")
# Define the base directory for secrets. Must end with a slash.
BAO_SECRET_BASE_PATH = os.getenv("BAO_SECRET_BASE_PATH", "kv/data/my-service/")
API_KEY = os.getenv("API_KEY")

app = FastAPI()

# --- Global Components ---
vault_lock = asyncio.Lock()

# Initialize the OpenBao client at startup
try:
    vault_client = hvac.Client(url=BAO_ADDR, token=BAO_TOKEN)
    if not vault_client.is_authenticated():
        raise ValueError("OpenBao client is not authenticated. Check your BAO_TOKEN.")
except Exception as e:
    print(f"Error connecting to OpenBao: {e}")
    raise RuntimeError("Failed to connect to OpenBao on startup.") from e

# Dependency to validate the API Key
def validate_api_key(x_api_key: str = Header(..., convert_underscores=False)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")
    return x_api_key

## --- API Endpoints ---
@app.post("/api/vault/store_key")
async def store_key(data: dict[str, str], api_key: str = Depends(validate_api_key)) -> dict[str, str]:
    """
    Accepts a secret key and stores it in OpenBao.
    """
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body must not be empty.")

    key_name = list(data.keys())[0]
    secret_value = data.get(key_name)
    
    if not secret_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No secret value provided.")
    
    try:
        async with vault_lock:
            await asyncio.to_thread(
                vault_client.secrets.kv.v2.create_or_update_secret,
                # Correct path: combine the base path with the key name
                path=f"{BAO_SECRET_BASE_PATH}{key_name}",
                secret={key_name: secret_value}
            )
        return {"message": f"Key '{key_name}' stored successfully in OpenBao."}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to store key: {str(e)}")


@app.get("/api/vault/get_key/{key_name}")
async def get_key(key_name: str, api_key: str = Depends(validate_api_key)) -> dict[str, Any]:
    """
    Retrieves a specific key from OpenBao by its name.
    """
    full_path = f"{BAO_SECRET_BASE_PATH}{key_name}"

    try:
        async with vault_lock:
            read_response = await asyncio.to_thread(
                vault_client.secrets.kv.v2.read_secret_version,
                path=full_path
            )
        
        if read_response and "data" in read_response and "data" in read_response["data"]:
            secret_data = read_response["data"]["data"]
            return secret_data

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Secret '{key_name}' not found.")
    except hvac.exceptions.InvalidRequest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Secret '{key_name}' not found at the specified path.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve key: {str(e)}")


@app.get("/api/vault/list_keys")
async def list_keys(api_key: str = Depends(validate_api_key)) -> dict[str, Any]:
    """
    Retrieves a list of all secrets (keys) at the specified path.
    """
    list_path = BAO_SECRET_BASE_PATH
    
    try:
        async with vault_lock:
            list_response = await asyncio.to_thread(
                vault_client.secrets.kv.v2.list_secrets,
                path=list_path
            )
        
        if list_response and "data" in list_response and "keys" in list_response["data"]:
            keys_list = list_response["data"]["keys"]
            return {"keys": keys_list}
        
        # If no keys are found, list_secrets might return an empty dict or a response without "keys"
        return {"keys": []}
    
    except hvac.exceptions.InvalidRequest:
        # Occurs if the path itself does not exist in OpenBao
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Path '{list_path}' does not exist or is not a directory.")
    except hvac.exceptions.InvalidPath:
        return {"keys": []}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list keys: {str(e)}")


@app.delete("/api/vault/delete_key/{key_name}")
async def delete_key(key_name: str, api_key: str = Depends(validate_api_key)) -> dict[str, str]:
    """
    Deletes the stored key from OpenBao.
    """
    secret_path = f"{BAO_SECRET_BASE_PATH}{key_name}"
    try:
        await asyncio.to_thread(
            vault_client.secrets.kv.v2.delete_metadata_and_all_versions,
            path=secret_path
        )

        return {"message": f"Key '{key_name}' deleted successfully from OpenBao."}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete key: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("vault_server:app", host="0.0.0.0", port=8080, reload=False)