# MAI Home MLOps pipeline

This project is part of **MAI-HOME**, an Interreg Flanders–Netherlands initiative that uses AI to combat energy poverty and reduce CO₂ emissions in housing. Renovating homes alone rarely delivers the expected CO₂ savings, partly because undetected water leaks cause hidden structural damage and drive up costs for both housing corporations and tenants. Predicting *when* a leak will occur is unreliable, since water usage alone can't distinguish a real leak from a legitimate spike (a filled bathtub, a long shower, a stuck toilet flush) without extra signals like pipe pressure or acoustics. This project instead focuses on *detecting* leaks as they happen (e.g. water that keeps flowing uninterrupted for hours at night), which is a far more robust signal than forecasting. To demonstrate this, the repo simulates hourly water consumption for 6 households and runs it through an anomaly-detection model (isolation forest + a "zero usage per day" heuristic) to flag leaks in near real time, all stored efficiently in a TimescaleDB hypertable and visualized per household in Grafana with a leak-detection overlay. The synthetic generator is designed to later be swapped for a real, non-synthetic household data stream without changing the rest of the pipeline.

## What you need installed

- [Docker](https://docs.docker.com/engine/install/) and Docker Compose (Docker Desktop on Windows/Mac, or `docker-compose-plugin` on Linux)

That's it for running the local stack; everything else (Python, Postgres/TimescaleDB, Grafana) runs inside containers.

## Running the local stack

```
cd src/apps
docker-compose up --build
```

This starts 4 services:

| Service     | What it does                                                                                                   | Exposed at                     |
|-------------|-------------------------------------------------------------------------------------------------------------------|---------------------------------|
| `database`  | TimescaleDB (Postgres) hypertable `household_water_usage`                                                        | `localhost:5432`                |
| `generator` | Simulates hourly water usage for 6 households (`single_be`, `single_nl`, `couple_be`, `couple_nl`, `family_be`, `family_nl`), runs each hour through a pre-trained leak-detection model, and writes the result to the database. On first run it backfills from `2024-01-01 00:00` up to the last completed hour; on restart it fills any gap since the last stored datapoint, then generates one new row per household every hour. | n/a                              |
| `api`       | FastAPI read endpoint over the data                                                                              | `localhost:8000/data`           |
| `dashboard` | Grafana, pre-provisioned with the TimescaleDB datasource and a household water-usage dashboard                  | `localhost:3000` (`admin`/`admin`) |

Stop and wipe all data (fresh backfill on next start):
```
docker-compose down -v
```
Stop but keep data:
```
docker-compose down
```

## Exploring the data

- **Grafana**: open `localhost:3000`, log in with `admin`/`admin`. The "Household Water Usage Overview" dashboard has a `household` selector (pick one or "All" to stack all 6) and overlays leak-detection status (`has_leakage`) as red bars on top of the consumption line.
- **API**: `GET http://localhost:8000/data?household_id=family_be&limit=100`
- **Raw SQL** (via Grafana's "Explore" on the TimescaleDB datasource, or `psql`):
  ```sql
  SELECT * FROM household_water_usage
  WHERE household_id = 'family_be'
  ORDER BY timestamp DESC
  LIMIT 100;
  ```

## Project layout

```
src/apps/
├── docker-compose.yml
├── database/   # TimescaleDB schema (init.sql)
├── generator/  # water-usage simulation + leak detection (main.py, detector.py, models/)
├── api/        # FastAPI read endpoint
└── dashboard/  # Grafana provisioning (datasource + dashboard JSON)
```

---
