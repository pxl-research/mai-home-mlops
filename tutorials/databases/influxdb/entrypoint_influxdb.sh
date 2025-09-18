#!/bin/bash
set -e


# Start InfluxDB in the background
influxdb3 serve --node-id host01 --object-store file --data-dir /var/lib/influxdb3 &

# Wait a few seconds for the server to start
sleep 5

if ! [ -f /secrets/influxdb_token ]; then
    # Create admin token
    export INFLUXDB_TOKEN=$(influxdb3 create token --admin | awk '/Token:/ {print $2}')
    # Write new token file
    echo "$INFLUXDB_TOKEN" > /secrets/influxdb_token
fi

# Keep container running
wait