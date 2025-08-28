import os
import time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Get environment variables
url = os.getenv('INFLUXDB_URL')
token = os.getenv('INFLUXDB_TOKEN')
org = os.getenv('INFLUXDB_ORG')
bucket = os.getenv('INFLUXDB_BUCKET') # Retrieve the bucket name from the environment variable

# Ensure all necessary variables are set
if not all([url, token, org, bucket]):
    raise ValueError("Missing one or more required environment variables: INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET")

print(f"Connecting to InfluxDB at {url}...")

client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)

point = Point("mem").tag("host", "server1").field("used_percent", 23.43).time(time.time_ns(), WritePrecision.NS)

print("Writing data point...")
try:
    write_api.write(bucket=bucket, org=org, record=point)
    print("Data point written successfully.")
except Exception as e:
    print(f"Error writing data: {e}")
    # You might want to retry or handle the error gracefully here
    
print("Querying data...")
query_api = client.query_api()
query = f'from(bucket: "{bucket}") |> range(start: -1h) |> filter(fn: (r) => r["_measurement"] == "mem")'
tables = query_api.query(query, org=org)

for table in tables:
  for record in table.records:
    print(record)

print("Script finished.")