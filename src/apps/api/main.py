from fastapi import FastAPI
import psycopg
from psycopg.rows import dict_row

app = FastAPI()

@app.get("/data")
async def get_data():
    async with await psycopg.AsyncConnection.connect(
        conninfo="host=database dbname=postgres user=postgres password=password"
    ) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT * FROM sensor_data ORDER BY time DESC LIMIT 10")
            return await cur.fetchall()
