"""
Configuration module for the Application.
Centralizes environment variable loading and logging setup.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Define project root
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(ROOT_DIR / "server" / ".env")

class Config:
    """Application Configuration Settings."""
    
    # Google Sheets
    GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
    GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
    
    # Google Drive
    DRIVE_ROOT_ID = os.getenv("DRIVE_ROOT_ID")
    DRIVE_SA_CREDENTIALS_PATH = os.getenv("DRIVE_SA_CREDENTIALS_PATH", "./secrets/google_drive.json")
    
    # External APIs
    BRASIL_API_URL = os.getenv("BRASIL_API_URL", "https://brasilapi.com.br/api/feriados/v1")
    
    # Database (Postgres)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "seta")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    
    # App Settings
    STATEMENTS_ROOT = os.getenv("STATEMENTS_ROOT", "/data/extratos")
    REPORTS_DIR = os.getenv("REPORTS_DIR", "./dados/relatorios")
    
    @classmethod
    def validate(cls):
        """Validate critical configuration."""
        if not cls.GOOGLE_SHEETS_ID:
            logging.warning("GOOGLE_SHEETS_ID not set.")
        if not cls.GOOGLE_CREDENTIALS_PATH:
            logging.warning("GOOGLE_CREDENTIALS_PATH not set.")

def setup_logging(level=logging.INFO):
    """
    Configure logging for the application.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Add FileHandler if needed
        ]
    )
