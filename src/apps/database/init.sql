CREATE TYPE household_id_t AS ENUM (
    'single_be', 'single_nl', 'couple_be', 'couple_nl', 'family_be', 'family_nl'
);

CREATE TABLE household_water_usage (
    timestamp                 TIMESTAMPTZ NOT NULL,
    household_id              household_id_t NOT NULL,
    volume_liter               REAL NOT NULL,
    is_leakage                 BOOLEAN NOT NULL,   -- ground-truth simulated leak flag
    has_leakage                BOOLEAN NOT NULL,   -- detector's final prediction (is_leak)
    zero_gap_anomaly           BOOLEAN NOT NULL,
    isolation_forest_anomaly   BOOLEAN NOT NULL,
    predicted                  BOOLEAN NOT NULL,   -- false during detector warm-up
    PRIMARY KEY (household_id, timestamp)
);

SELECT create_hypertable(
    'household_water_usage', 'timestamp',
    chunk_time_interval => INTERVAL '30 days'
);

CREATE INDEX ON household_water_usage (household_id, timestamp DESC);

ALTER TABLE household_water_usage SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'household_id',
    timescaledb.compress_orderby = 'timestamp'
);
SELECT add_compression_policy('household_water_usage', INTERVAL '7 days');
