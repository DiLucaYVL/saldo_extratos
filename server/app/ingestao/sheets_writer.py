"""
Google Sheets writer for bank balance extraction results.
"""
import logging
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from server.config import Config

logger = logging.getLogger(__name__)

class GoogleSheetsWriter:
    """
    Writes bank balance data to Google Sheets.
    
    Attributes:
        credentials_path (str): Path to the Google Service Account JSON.
        spreadsheet_id (str): ID of the target Google Spreadsheet.
        service: Google Sheets API service instance.
    """
    
    def __init__(self, credentials_path: str = None, spreadsheet_id: str = None):
        """
        Initialize Google Sheets writer.
        
        Args:
            credentials_path: Optional override for credentials path.
            spreadsheet_id: Optional override for spreadsheet ID.
            
        Raises:
            ValueError: If credentials or spreadsheet ID are missing.
        """
        self.credentials_path = credentials_path or Config.GOOGLE_CREDENTIALS_PATH
        self.spreadsheet_id = spreadsheet_id or Config.GOOGLE_SHEETS_ID
        
        if not self.credentials_path:
            raise ValueError("GOOGLE_CREDENTIALS_PATH must be set in .env or passed as argument")
        if not self.spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_ID must be set in .env or passed as argument")
        
        self.service = self._get_sheets_service()
    
    def _get_sheets_service(self):
        """
        Create and return Google Sheets API service.
        
        Returns:
            Resource: The Google Sheets API service resource.
        """
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            service = build('sheets', 'v4', credentials=credentials)
            return service
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")
            raise
    
    def _get_first_sheet_title(self) -> str:
        """
        Get the title of the first sheet in the spreadsheet.
        
        Returns:
            str: Title of the first sheet, or 'Sheet1' if lookup fails.
        """
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            sheets = spreadsheet.get('sheets', [])
            if sheets:
                return sheets[0]['properties']['title']
            return 'Sheet1'
        except Exception as e:
            logger.error(f"Error getting sheet title: {e}")
            return 'Sheet1'

    def _read_existing_data(self, sheet_name: str) -> pd.DataFrame:
        """
        Read all data from the specified sheet to check for duplicates.
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_name
            ).execute()
            values = result.get('values', [])
            
            if not values:
                return pd.DataFrame()
                
            # Assume first row is header
            headers = values[0]
            data = values[1:]
            
            return pd.DataFrame(data, columns=headers)
        except Exception as e:
            logger.error(f"Error reading existing data: {e}")
            return pd.DataFrame()

    def get_existing_accounts(self, target_date: str) -> set[tuple[str, str]]:
        """
        Get a set of (Banco, Conta) that already exist for the given date.
        
        Args:
            target_date: Date string in 'DD/MM/YYYY' format to filter by.
            
        Returns:
            Set of tuples (Banco, Conta).
        """
        try:
            sheet_name = self._get_first_sheet_title()
            df = self._read_existing_data(sheet_name)
            
            existing = set()
            if df.empty:
                return existing
                
            # Filter by date
            # Ensure 'Data' column exists and handle types
            if 'Data' not in df.columns or 'Conta' not in df.columns or 'Banco' not in df.columns:
                 return existing
            
            # Key comparison: Data == target_date
            for _, row in df.iterrows():
                d = str(row.get('Data', '')).strip()
                if d == target_date:
                    c = str(row.get('Conta', '')).strip()
                    b = str(row.get('Banco', '')).strip()
                    if c and b:
                        existing.add((b, c)) # (Banco, Conta)
            
            logger.info(f"Found {len(existing)} existing accounts for date {target_date}.")
            return existing
            
        except Exception as e:
            logger.error(f"Error fetching existing accounts: {e}")
            return set()

    def append_balances(self, df: pd.DataFrame, sheet_name: str = None) -> None:
        """
        Append balance dataframe to existing Google Sheets data, avoiding duplicates.
        
        Args:
            df: DataFrame containing the balance data. 
                Expected columns: Data, Conta, Banco, Saldo.
            sheet_name: Name of the sheet to append to. 
                        If None, automatically detects the first sheet.
        """
        if df.empty:
            logger.warning("No data provided to append to Google Sheets.")
            return

        # If no sheet name provided, try to find the first one
        if sheet_name is None:
            sheet_name = self._get_first_sheet_title()
            logger.info(f"Using sheet: {sheet_name}")
            
        # 1. Check for duplicates
        try:
            existing_df = self._read_existing_data(sheet_name)
            
            if not existing_df.empty:
                # Ensure we strictly compare relevant columns for duplication
                # Key: Data, Conta, Banco
                # Note: Existing data in Sheet is all strings.
                
                # Create a set of signatures from existing data
                # Handle missing columns gracefully
                exist_sigs = set()
                for _, row in existing_df.iterrows():
                    # Get values safely, assume '' if missing
                    d = str(row.get('Data', '')).strip()
                    c = str(row.get('Conta', '')).strip()
                    b = str(row.get('Banco', '')).strip()
                    if d and c and b:
                        exist_sigs.add((d, c, b))
                
                # Filter input DF
                new_rows = []
                duplicates = 0
                
                for _, row in df.iterrows():
                    d = str(row.get('Data', '')).strip()
                    c = str(row.get('Conta', '')).strip()
                    b = str(row.get('Banco', '')).strip()
                    
                    if (d, c, b) in exist_sigs:
                        duplicates += 1
                        logger.debug(f"Skipping duplicate: {d} - {b} - {c}")
                    else:
                        new_rows.append(row)
                
                if duplicates > 0:
                    logger.info(f"Skipped {duplicates} duplicate records.")
                
                if not new_rows:
                    logger.info("All records are duplicates. Nothing to upload.")
                    return
                    
                df_to_upload = pd.DataFrame(new_rows)
            else:
                df_to_upload = df
                
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
            # Fallback: try to upload everything or abort? 
            # Abort to be safe as requested "nao correr risco de duplicar"
            logger.warning("Aborting upload due to duplicate check failure.")
            return

        # 2. Prepare for Upload
        # Convert DataFrame to native Python types and format decimals
        df_copy = df_to_upload.copy()
        
        # Format 'Saldo' column to use comma as decimal separator if it exists
        if 'Saldo' in df_copy.columns:
            # First ensure it's a float/decimal, then format
            # Using apply to handle potential string inputs gracefully
            df_copy['Saldo'] = df_copy['Saldo'].astype(str).str.replace('.', ',')

        # Force 'Data' column to be treated as text by prepending "'"
        if 'Data' in df_copy.columns:
            df_copy['Data'] = "'" + df_copy['Data'].astype(str)
            
        df_copy = df_copy.astype(str)
        
        # Convert DataFrame to list of lists (no header for append)
        values = df_copy.values.tolist()
        
        body = {
            'values': values
        }
        
        try:
            # When appending, we can just specify the sheet name as the range
            # Google Sheets will find the table and append to it
            range_name = sheet_name
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            updated_rows = result.get('updates', {}).get('updatedRows', 0)
            logger.info(f"Successfully appended {updated_rows} rows to Google Sheets (ID: {self.spreadsheet_id}).")
            
        except Exception as e:
            logger.error(f"Error appending to Google Sheets: {e}")
            raise
