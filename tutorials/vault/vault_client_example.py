"""
This script generates a Fernet key and uses the `requests` library to
interact with the FastAPI server to store, retrieve, and delete the key.
"""

import requests
from cryptography.fernet import Fernet
import json
import time

# Define the FastAPI server's base URL
API_URL = "http://127.0.0.1:8080"

# --- PART 1: Generate and Send the Key ---
fernet_key = Fernet.generate_key().decode('utf-8')
print(f"Generated Fernet key: {fernet_key}")

post_data = {"secret_key": fernet_key}
try:
    print("\nAttempting to send key to the server...")
    response = requests.post(f"{API_URL}/api/store_key", json=post_data)
    response.raise_for_status()
    print("Server response (POST):", json.dumps(response.json(), indent=2))
except requests.exceptions.RequestException as e:
    print(f"An error occurred during POST request: {e}")
    exit()

time.sleep(1)

# --- PART 2: Retrieve the Key ---
try:
    print("\nAttempting to retrieve key from the server...")
    response = requests.get(f"{API_URL}/api/get_key")
    response.raise_for_status()
    retrieved_data = response.json()
    print("Server response (GET):", json.dumps(retrieved_data, indent=2))
    
    retrieved_key = retrieved_data.get("retrieved_key")
    if retrieved_key == fernet_key:
        print("\nSuccess! The retrieved key matches the generated key.")
    else:
        print("\nError! The keys do not match.")
except requests.exceptions.RequestException as e:
    print(f"An error occurred during GET request: {e}")
    exit()

time.sleep(1)

# --- PART 3: Delete the Key ---
try:
    print("\nAttempting to delete the key from the server...")
    response = requests.delete(f"{API_URL}/api/delete_key")
    response.raise_for_status()
    print("Server response (DELETE):", json.dumps(response.json(), indent=2))
except requests.exceptions.RequestException as e:
    print(f"An error occurred during DELETE request: {e}")
    exit()

time.sleep(1)

# --- PART 4: Confirm Deletion ---
try:
    print("\nAttempting to retrieve the key again to confirm it's gone...")
    response = requests.get(f"{API_URL}/get_key")
    response.raise_for_status()
    print("Server response (GET after delete):", json.dumps(response.json(), indent=2))
except requests.exceptions.RequestException as e:
    print(f"\nAs expected, a request error occurred (status {e.response.status_code}). The key was successfully deleted.")
