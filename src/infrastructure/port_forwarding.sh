#!/bin/bash

# Global array to store the PIDs of all background kubectl port-forward processes
declare -a FORWARD_PIDS=()

# Function to start a robust kubectl port-forward process
# Usage: start_k8s_port_forward <namespace> <resource_type/name> <local_port> <remote_port>
start_k8s_port_forward() {
    local NAMESPACE="$1"
    local RESOURCE="$2"
    local LOCAL_PORT="$3"
    local REMOTE_PORT="$4"
    local PORTS="${LOCAL_PORT}:${REMOTE_PORT}"

    # Basic argument validation
    if [ -z "$NAMESPACE" ] || [ -z "$RESOURCE" ] || [ -z "$LOCAL_PORT" ] || [ -z "$REMOTE_PORT" ]; then
        echo "Error: Missing arguments for port-forward."
        echo "Usage: start_k8s_port_forward <namespace> <resource> <local_port> <remote_port>"
        return 1
    fi

    echo "Starting port-forward: ${NAMESPACE}/${RESOURCE} ${PORTS}"

    # Start kubectl port-forward in the background, suppressing all output.
    kubectl -n "${NAMESPACE}" port-forward "${RESOURCE}" "${PORTS}" > /dev/null 2>&1 &
    local PID=$!

    # Check if kubectl successfully started (PID exists)
    if ! ps -p "$PID" > /dev/null; then
        echo "Error: kubectl failed to start for ${RESOURCE}. Check resource name or connectivity."
        return 1
    fi

    # Store the PID in the global array
    FORWARD_PIDS+=("$PID")
    
    # Wait for the local port to become available
    local MAX_WAIT_SECONDS=10
    local SECONDS_WAITED=0

    echo "Waiting for local port ${LOCAL_PORT} to become available..."

    while ! nc -z localhost "${LOCAL_PORT}" > /dev/null 2>&1; do
        if [ "${SECONDS_WAITED}" -ge "${MAX_WAIT_SECONDS}" ]; then
            echo "Timeout: Port ${LOCAL_PORT} did not become available. Killing background process ${PID}."
            kill "$PID" 2>/dev/null 
            return 1
        fi
        sleep 0.2
        SECONDS_WAITED=$((SECONDS_WAITED + 1))
    done

    echo "Port-forward established for ${RESOURCE} at http://localhost:${LOCAL_PORT}"
    return 0
}

# ----------------------------------------------------------------------
# Trap and Cleanup Function (Runs on script exit)
# ----------------------------------------------------------------------

cleanup_forwards() {
    echo -e "\n--- Terminating all background port-forwards ---"
    
    # Iterate through all stored PIDs and kill them
    for PID in "${FORWARD_PIDS[@]}"; do
        if kill "$PID" 2>/dev/null; then
            echo "Killed PID: ${PID}"
        fi
    done
    echo "------------------------------------------------"
}

# Set the global trap to run the cleanup function on script exit (Ctrl+C, etc.)
trap cleanup_forwards EXIT INT TERM

# ----------------------------------------------------------------------
# All Port Forwards (Example Calls)
# ----------------------------------------------------------------------
# TODO: add more port forwardings here!
start_k8s_port_forward "argo" "svc/argo-workflows-server" "2746" "2746"


# ----------------------------------------------------------------------
# Keep the Main Script Alive
# ----------------------------------------------------------------------

echo -e "\nAll forwards running in the background. Press Ctrl+C to stop them all."

# Wait for all background processes (which now includes the last-started kubectl,
# though we are just using 'wait' to pause the main script indefinitely).
wait