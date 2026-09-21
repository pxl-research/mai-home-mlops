from fastapi import FastAPI
import psycopg
from psycopg.rows import dict_row

app = FastAPI()

@app.get("/data")
async def get_data(household_id: str | None = None, limit: int = 100):
    async with await psycopg.AsyncConnection.connect(
        conninfo="host=database dbname=postgres user=postgres password=password"
    ) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            query = "SELECT * FROM household_water_usage"
            params = []
            if household_id:
                query += " WHERE household_id = %s"
                params.append(household_id)
            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)
            await cur.execute(query, params)
            return await cur.fetchall()
