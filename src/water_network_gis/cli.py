"""Command line entry point: validate the sample network and print NRW by DMA.

Run: python -m water_network_gis.cli   (from the repository root, with src on PYTHONPATH)
"""

from __future__ import annotations

import logging

from water_network_gis.nrw import nrw_by_dma
from water_network_gis.sample_data import make_sample
from water_network_gis.validate import validate_network


def main() -> None:
    """Run the demonstration workflow on synthetic data."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    data = make_sample()
    report = validate_network(data["pipes"], data["meters"])
    print("Validation report:", report)
    table = nrw_by_dma(data["dmas"], data["meters"], data["billing"], data["input_volume"])
    print(table.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))


if __name__ == "__main__":
    main()
