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