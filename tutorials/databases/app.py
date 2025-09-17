import os
from datetime import datetime, timezone
import time
import requests
from influxdb_client_3 import InfluxDBClient3, Point
import pandas as pd

# Environment variables
print("ole")
host = os.getenv("INFLUXDB_URL")
token = os.getenv("INFLUXDB_TOKEN")
database = os.getenv("INFLUXDB_BUCKET")

if not all([host, token, database]):
    raise ValueError("Missing InfluxDB configuration environment variables")

# Connect to InfluxDB
client = InfluxDBClient3(
    host=host,
    database=database,
    token=token
)

# Write a sample point (synchronously, but async is also possible)
# NOTE: Point is safe from SQL injection!
point = Point("census") \
    .tag("location", "Brussels") \
    .field("ant", 14) \
    .field("bees", 99) \
    .time(datetime.now(timezone.utc).isoformat())
client.write(point)
print("Data is written to database.")

# Prepare SQL query
query = '''
    SELECT "location", "ant", "bees", "time"
    FROM "census"
    WHERE time >= now() - interval '7 days'
    ORDER BY time ASC
'''

# Run the query and get the result as a pyarrow.Table
result = client.query(query)
# Convert to pd.DataFrame
df = result.to_pandas()

# Convert time column from ns to human readable datetime
df["time"] = pd.to_datetime(df["time"], unit="ns")


print("---")
print(df.to_string(index=False))
print("---")


"""
# Later we can do this:
data = {
    "measurement": "temperature",
    "tags": {
        "location": "office",
        "device": "sensor1"
    },
    "fields": {
        "value": 23.5,
        "humidity": 55
    },
    "timestamp": "2025-09-17T12:00:00Z"
}

# Convert JSON to Point
point = Point(data["measurement"])

# Add tags
for tag_key, tag_value in data.get("tags", {}).items():
    point.tag(tag_key, tag_value)

# Add fields
for field_key, field_value in data.get("fields", {}).items():
    point.field(field_key, field_value)

# Add timestamp if provided
if "timestamp" in data:
    point.time(datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")))

# Write to InfluxDB
client.write(point)
print("Point written:", point)
"""