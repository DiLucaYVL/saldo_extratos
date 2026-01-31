"""
Script for retroactive backfill of January 2026 bank statements.
"""
import sys
import logging
from datetime import date, timedelta
from pathlib import Path

# Ensure server module is importable
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

from server.config import setup_logging
from main import process_date

logger = logging.getLogger("backfill")

def run_backfill():
    setup_logging()
    logger.info("Starting Backfill for January 2026")
    
    # Iterate from Jan 1st to Jan 31st 2026
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    
    current_date = start_date
    while current_date <= end_date:
        # Only process weekdays? The prompt implies "analise retroativa" of everything.
        # But usually we only look for files generated on weekdays.
        # Let's process valid business days logic implicitly via "process_date" which 
        # calculates "previous business day" for the upload date.
        # However, "process_date" uses the `target_date` as the SEARCH date in Drive.
        # So we should run for every weekday where a file might exist.
        
        if current_date.weekday() < 5: # Mon-Fri
            logger.info(f"Processing Backfill Date: {current_date}")
            try:
                process_date(current_date)
            except Exception as e:
                logger.error(f"Failed to process {current_date}: {e}")
        
        current_date += timedelta(days=1)

    logger.info("Backfill Completed.")

if __name__ == "__main__":
    run_backfill()
