"""
Main automation script for Bank Statement Conciliation.
Orchestrates the flow: Drive Download -> Extraction -> Date Logic -> Sheets Upload -> Cleanup.
"""
import sys
import logging
import pandas as pd
from datetime import datetime, date
from pathlib import Path

# Ensure server module is importable
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

from server.config import setup_logging, Config
from server.utils import get_previous_business_day
from server.app.ingestao.drive_client import DriveClient
from server.app.ingestao.file_locator import StatementLocator
from server.app.ingestao.balance_extractor import extract_balances
from server.app.ingestao.sheets_writer import GoogleSheetsWriter

logger = logging.getLogger("main")

def main():
    setup_logging()
    logger.info("Starting Daily Conciliation Workflow")
    Config.validate()
    
    # 1. Determine Dates
    today = datetime.now().date()
    # today = date(2026, 1, 29) # Uncomment to simulate specific date
    
    # Calculate the date to be used in the report (Previous Business Day)
    upload_date_str = get_previous_business_day(today)
    logger.info(f"Today's Date: {today.strftime('%d/%m/%Y')}")
    logger.info(f"Target Drive Search Date: {today.strftime('%d/%m/%Y')}")
    logger.info(f"Date to Upload to Sheets: {upload_date_str}")
    
    # 2. Setup Sheets Writer (Check duplicates first)
    try:
        writer = GoogleSheetsWriter()
        existing_accounts = writer.get_existing_accounts(upload_date_str)
        if existing_accounts:
            logger.info(f"Checking for existing accounts: Found {len(existing_accounts)} already uploaded for {upload_date_str}")
        else:
            logger.info(f"No existing accounts found for {upload_date_str}. Full download.")
    except Exception as e:
         logger.warning(f"Could not fetch existing accounts to optimize download: {e}")
         existing_accounts = None

    # 3. Setup Drive Client and Locator
    # (Uses secrets/google_drive.json)
    try:
        drive_creds = Path(Config.DRIVE_SA_CREDENTIALS_PATH)
        if not drive_creds.exists():
            logger.error(f"Drive credentials not found at: {drive_creds}")
            return

        drive_client = DriveClient(
            root_id=Config.DRIVE_ROOT_ID,
            credentials_path=drive_creds
        )
        
        locator = StatementLocator(
            drive_client=drive_client,
            root_dir=None # Use temp dirs managed by locator
        )
    except Exception as e:
        logger.critical(f"Failed to initialize Drive components: {e}", exc_info=True)
        return

    # 4. Download Files from Drive
    logger.info("Searching for files in Google Drive...")
    downloaded_files = []
    try:
        # Search for today's folder, passing existing accounts to skip
        downloaded_files = locator.locate(today, today, existing_accounts)
        
        if not downloaded_files:
            logger.warning(f"No files found (or all skipped) for date {today.strftime('%d/%m/%Y')} in Drive.")
            # Depending on business rule, we might stop here.
            # But we proceed to cleanup just in case.
        else:
            logger.info(f"Downloaded {len(downloaded_files)} files to temporary locations.")
        
    except Exception as e:
        logger.error(f"Error during Drive search/download: {e}", exc_info=True)
        # Cleanup even on error if possible
        if locator: 
            locator.cleanup()
        return

    # 5. Extract Balances
    if downloaded_files:
        logger.info("Extracting balances from files...")
        try:
            df = extract_balances(downloaded_files)
            
            if df.empty:
                logger.warning("No balances extracted from the downloaded files.")
            else:
                logger.info(f"Successfully extracted {len(df)} records.")
                
                # 6. Apply Date Override Logic
                # "A data inserida na coluna 'Data' quando você subir as informações sempre será o dia útil anterior"
                logger.info(f"Overriding statement dates with Business Day: {upload_date_str}")
                df['Data'] = upload_date_str
                
                # 7. Upload to Google Sheets
                # (Uses secrets/saldo_extratos.json)
                logger.info("Writing to Google Sheets...")
                # Writer already initialized
                writer.append_balances(df)
                logger.info("Upload completed successfully.")
                
        except Exception as e:
            logger.error(f"Error during extraction or upload: {e}", exc_info=True)
    
    # 7. Cleanup
    logger.info("Cleaning up temporary files...")
    locator.cleanup()
    logger.info("Workflow finished.")

if __name__ == "__main__":
    main()
