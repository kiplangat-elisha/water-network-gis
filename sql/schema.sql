-- PostGIS schema for a town water distribution network.
-- CRS: EPSG:21036 (Arc 1960 / UTM zone 36S), suitable for Narok, Kenya.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS dma (
    dma_id      TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    geom        geometry(MultiPolygon, 21036) NOT NULL
);

CREATE TABLE IF NOT EXISTS pipe (
    pipe_id       TEXT PRIMARY KEY,
    material      TEXT CHECK (material IN ('uPVC', 'HDPE', 'GI', 'AC', 'DI', 'Steel', 'Unknown')),
    diameter_mm   INTEGER CHECK (diameter_mm > 0),
    install_year  INTEGER CHECK (install_year BETWEEN 1900 AND 2100),
    status        TEXT DEFAULT 'active' CHECK (status IN ('active', 'abandoned', 'proposed')),
    geom          geometry(LineString, 21036) NOT NULL
);

CREATE TABLE IF NOT EXISTS valve (
    valve_id    TEXT PRIMARY KEY,
    valve_type  TEXT CHECK (valve_type IN ('gate', 'air', 'washout', 'pressure_reducing', 'other')),
    is_open     BOOLEAN DEFAULT TRUE,
    geom        geometry(Point, 21036) NOT NULL
);

CREATE TABLE IF NOT EXISTS customer_meter (
    account_no   TEXT PRIMARY KEY,
    customer     TEXT,
    category     TEXT CHECK (category IN ('domestic', 'commercial', 'institutional', 'kiosk')),
    pipe_id      TEXT REFERENCES pipe (pipe_id),
    geom         geometry(Point, 21036) NOT NULL
);

CREATE TABLE IF NOT EXISTS monthly_volume (
    dma_id         TEXT REFERENCES dma (dma_id),
    month          DATE NOT NULL,
    input_m3       NUMERIC CHECK (input_m3 >= 0),
    PRIMARY KEY (dma_id, month)
);

CREATE TABLE IF NOT EXISTS monthly_billing (
    account_no   TEXT REFERENCES customer_meter (account_no),
    month        DATE NOT NULL,
    billed_m3    NUMERIC CHECK (billed_m3 >= 0),
    PRIMARY KEY (account_no, month)
);

CREATE INDEX IF NOT EXISTS pipe_geom_gix ON pipe USING GIST (geom);
CREATE INDEX IF NOT EXISTS valve_geom_gix ON valve USING GIST (geom);
CREATE INDEX IF NOT EXISTS meter_geom_gix ON customer_meter USING GIST (geom);
CREATE INDEX IF NOT EXISTS dma_geom_gix ON dma USING GIST (geom);

-- Non-revenue water by DMA and month (input volume minus billed volume).
CREATE OR REPLACE VIEW nrw_by_dma AS
SELECT v.dma_id,
       v.month,
       v.input_m3,
       COALESCE(SUM(b.billed_m3), 0)                                   AS billed_m3,
       v.input_m3 - COALESCE(SUM(b.billed_m3), 0)                      AS nrw_m3,
       CASE WHEN v.input_m3 > 0
            THEN (v.input_m3 - COALESCE(SUM(b.billed_m3), 0)) / v.input_m3
       END                                                             AS nrw_ratio
FROM monthly_volume v
JOIN dma d ON d.dma_id = v.dma_id
LEFT JOIN customer_meter m ON ST_Within(m.geom, d.geom)
LEFT JOIN monthly_billing b ON b.account_no = m.account_no AND b.month = v.month
GROUP BY v.dma_id, v.month, v.input_m3;
