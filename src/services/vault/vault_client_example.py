"""
This script generates a Fernet key and uses the `requests` library to
interact with the FastAPI server to store, retrieve, and delete the key.
"""
from dotenv import load_dotenv
import requests
import nacl.utils # Import PyNaCl's utility functions
import nacl.secret

import json
import time
import os

load_dotenv()

# Define the FastAPI server's base URL and API Key from a .env file
API_URL = "http://127.0.0.1:8080"
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    print("Error: API_KEY not found. Make sure it's set in your .env file.")
    exit()

# Define headers for authentication
headers = {
    "x_api_key": API_KEY, # Use the underscore as expected by the server's dependency
    "Content-Type": "application/json"
}


# --- PART 1: Generate and Send the Key ---
# Define a constant key name and value to use for storing, retrieving, and deleting
KEY_NAME = "secret_key"
# Generate a random 32-byte key using PyNaCl
# The secret_box key length is fixed at 32 bytes
nacl_key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
# Convert the bytes to a hexadecimal string for easy storage and transfer
# The server expects a string, not bytes.
nacl_key = nacl_key.hex()
print(f"Generated PyNaCl key (hex): {nacl_key}")

post_data = {
    "key_name": KEY_NAME,
    "secret_value": nacl_key
}

# 1. Inspect the URL, headers, and body before sending
print("\n--- Outgoing Request Details ---")
print(f"URL: {API_URL}/api/vault/store_key")
print(f"Method: POST")
print(f"Headers: {json.dumps(headers, indent=2)}")
print(f"Body: {json.dumps(post_data, indent=2)}")

try:
    print("\nAttempting to send key to the server...")
    # Using 'json=' parameter is the standard and most reliable way
    response = requests.post(f"{API_URL}/api/vault/store_key", json=post_data, headers=headers)
    
    # 2. Check the response status code immediately
    print(f"\nResponse Status Code: {response.status_code}")
    
    # 3. Check the response content, even if it's an error
    try:
        response_json = response.json()
        print("Response JSON Body:")
        print(json.dumps(response_json, indent=2))
    except json.JSONDecodeError:
        print("Response Body (not JSON):")
        print(response.text)

    response.raise_for_status() # This will raise an HTTPError for 4xx/5xx responses

    print("\nSuccess! The key was sent successfully.")

except requests.exceptions.RequestException as e:
    print(f"\nAn error occurred during POST request: {e}")
    # The 'raise_for_status' will print the error message from the response body, which is what we need.

time.sleep(1)

# --- PART 2: Retrieve the Key ---
try:
    print("\nAttempting to retrieve key from the server...")
    # The endpoint is /api/vault/get_key/{key_name}
    response = requests.get(f"{API_URL}/api/vault/get_key/{KEY_NAME}", headers=headers)
    response.raise_for_status()
    retrieved_data = response.json()
    print("Server response (GET):", json.dumps(retrieved_data, indent=2))
    
    # Retrieve the key from the returned dictionary using its name
    retrieved_key = retrieved_data.get(KEY_NAME)
    if retrieved_key == nacl_key:
        print("\nSuccess! The retrieved key matches the generated key.")
    else:
        print("\nError! The keys do not match.")
except requests.exceptions.RequestException as e:
    print(f"An error occurred during GET request: {e}")
    if e.response:
        print(f"Response details: {e.response.text}")
    exit()

time.sleep(1)

# --- PART 3: Delete the Key ---
try:
    print("\nAttempting to delete the key from the server...")
    # The endpoint is /api/vault/delete_key/{key_name}
    response = requests.delete(f"{API_URL}/api/vault/delete_key/{KEY_NAME}", headers=headers)
    response.raise_for_status()
    print("Server response (DELETE):", json.dumps(response.json(), indent=2))
except requests.exceptions.RequestException as e:
    print(f"An error occurred during DELETE request: {e}")
    if e.response:
        print(f"Response details: {e.response.text}")
    exit()

time.sleep(1)

# --- PART 4: Confirm Deletion ---
try:
    print("\nAttempting to retrieve the key again to confirm it's gone...")
    # The endpoint is /api/vault/get_key/{key_name}
    response = requests.get(f"{API_URL}/api/vault/get_key/{KEY_NAME}", headers=headers)
    response.raise_for_status()
    print("Server response (GET after delete):", json.dumps(response.json(), indent=2))
except requests.exceptions.RequestException as e:
    print(f"\nAs expected, a request error occurred (status {e.response.status_code}). The key was successfully deleted.")