"""Utility function to export the final coal generation capacities data to a CSV file"""
import csv
import os
from pathlib import Path
from db.generation_capacities import fetch_coal_generation_capacities_data
from utils.logger import get_logger
logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXPORT_CSV = PROJECT_ROOT / "data" / "processed" / "coal_generation_capacities.csv"


def export_coal_generation_capacities_to_csv() -> None:
    """Export coal generation capacities data to a CSV file for Power BI import."""
    
    try:
        rows = fetch_coal_generation_capacities_data()
        if not rows:
            logger.warning("No coal generation capacities data found to export.")
            return
        
        os.makedirs(PROJECT_ROOT / "data" / "processed", exist_ok=True) 
        

        # Write to CSV
        with open(EXPORT_CSV, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            writer.writerow(["period", "state", "state_description", "coal_capability", "coal_capability_change", "coal_percent_share", "total_capability"])
            # Write data rows
            for row in rows:
                writer.writerow(row)

        logger.info("Successfully exported coal generation capacities data to %s", EXPORT_CSV)

    except FileNotFoundError as exc:
        logger.error("Could not find CSV file: %s", exc)
        raise
    except Exception as exc:
        logger.error("Error exporting coal generation capacities data: %s", exc)
