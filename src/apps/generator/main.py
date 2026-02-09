import asyncio
import random
import psycopg
from datetime import datetime

async def generate_data():
    # Retry logic for DB connection
    while True:
        try:
            async with await psycopg.AsyncConnection.connect(
                conninfo="host=database dbname=postgres user=postgres password=password",
                autocommit=True
            ) as conn:
                async with conn.cursor() as cur:
                    while True:
                        val = random.uniform(20.0, 30.0)
                        await cur.execute(
                            "INSERT INTO sensor_data (time, sensor_id, value) VALUES (%s, %s, %s)",
                            (datetime.now(), "sensor-01", val)
                        )
                        print(f"Generated: {val}")
                        await asyncio.sleep(5)
        except Exception as e:
            print(f"Waiting for DB... {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(generate_data())
