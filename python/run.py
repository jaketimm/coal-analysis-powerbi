#!/usr/bin/env python3
"""EIA data retrieval process."""

from utils.eia_api.fetch_generation_capacities import (
    fetch_raw_eia_capacities_data,
    create_coal_generation_capacities_table
)
from utils.export_for_powerbi import export_coal_generation_capacities_to_csv
from utils.logger import get_logger


logger = get_logger(__name__)


def main():
    """Run the complete EIA data retrieval process."""
    logger.info("Starting EIA data retrieval process...")
    
    fetch_raw_eia_capacities_data()
    create_coal_generation_capacities_table()
    export_coal_generation_capacities_to_csv()
    
    logger.info("EIA data retrieval process complete.")


if __name__ == "__main__":
    main()