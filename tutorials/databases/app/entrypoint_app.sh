#!/bin/bash
set -e

# Wait a few seconds for the server to start
sleep 5

export INFLUXDB_TOKEN=$(cat /secrets/influxdb_token)
# echo "INFLUXDB_TOKEN=$INFLUXDB_TOKEN" # Debug only!

python app.py

# Keep container running
wait