# Water network GIS and non-revenue water toolkit

Tools for mapping a town water distribution network, checking the data, and finding where water is lost. Built from my work mapping the network and building an everyday-use database for **Narok Water and Sewerage Services Company** (2021).

## Why it matters

Kenyan utilities often lose 40% or more of the water they produce as non-revenue water (NRW): leaks, illegal connections and unbilled use. Climate change is making water scarcer in towns like Narok, so cutting losses is one of the cheapest forms of adaptation. You can only manage what you have mapped.

## What it does

| Part | Purpose |
|---|---|
| `sql/schema.sql` | PostGIS schema for pipes, valves, customer meters, district metered areas (DMAs), bulk input and billing, plus an `nrw_by_dma` view |
| `validate.py` | Quality checks before loading: duplicate IDs, missing diameters, dangling pipe ends, meters too far from any pipe |
| `nrw.py` | Monthly NRW volume and ratio per DMA, classified as high (≥40%), medium (≥25%) or low |
| `sample_data.py` | A synthetic two-DMA network so the workflow runs without confidential utility data |

All layers use **EPSG:21036 (Arc 1960 / UTM 36S)**, the local projected CRS for Narok.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q                # run the tests
```

Run the demonstration on the synthetic network:

```bash
PYTHONPATH=src python -m water_network_gis.cli      # Windows: set PYTHONPATH=src
```

Example output (synthetic data):

```
dma_id      month  input_m3  billed_m3  nrw_m3  nrw_ratio nrw_class
 DMA-B 2026-01-01    650.00     360.58  289.42       0.45      high
 DMA-A 2026-01-01    900.00     543.28  356.72       0.40    medium
```

## Data note

The sample network is generated, not real. Utility asset and customer data are confidential and are not included.

## Author

Kiplangat Elisha · Climate adaptation and geospatial analyst · [geonova.co.ke](https://www.geonova.co.ke)
