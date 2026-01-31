"""
Module for extracting balance information from bank statement files.
"""
import logging
from pathlib import Path
import pandas as pd

from server.app.ingestao.file_parsers import StatementParserRegistry
from server.utils import get_real_date

logger = logging.getLogger(__name__)

from typing import List, Union

def extract_balances(source: Union[Path, List[Path]]) -> pd.DataFrame:
    """
    Extracts balances from supported files.
    
    Args:
        source: Path to directory OR list of file paths.
        
    Returns:
        pd.DataFrame: A DataFrame with columns ['Data', 'Conta', 'Banco', 'Saldo'].
    """
    files = []
    
    if isinstance(source, list):
        files = [f for f in source if f.exists()]
    elif isinstance(source, Path) and source.exists():

        if source.is_dir():
            # Support multiple extensions
            extensions = ["*.pdf"]
            for ext in extensions:
                files.extend(list(source.glob(ext)))
        else:
             files = [source]
    else:
        logger.error(f"Invalid source provided: {source}")
        return pd.DataFrame()
    
    if not files:
        logger.warning(f"No supported files found in source")
        return pd.DataFrame()

    registry = StatementParserRegistry()
    rows = []
    
    for f in files:
        logger.debug(f"Processing file: {f.name}")
        try:
            result = registry.parse(f)
            if result:
                # Apply date logic from utils
                raw_date = result.get("data_arquivo")
                real_date = get_real_date(raw_date)
                
                rows.append({
                    "Data": real_date,
                    "Conta": result.get("conta"),
                    "Banco": result.get("banco"),
                    "Saldo": result.get("saldo"),
                    "Origem": f.name
                })
            else:
                # Fallback: Extract info from filename/path and set Saldo=0
                logger.warning(f"Failed to parse {f.name}. Using fallback Saldo=0.00.")
                
                # Derive Banco/Conta from path/filename
                # Path structure expected: .../Banco/MM-YYYY/DD-MM/Filename.pdf
                # Or Filename: Extrato_Banco_Conta.pdf
                
                # Try Path first for Bank
                try:
                    # heuristic: drive_locator creates temp/Banco/...
                    # Let's try to find supported bank name in parts
                    found_bank = "Unknown"
                    for part in f.parts:
                        if part in ["Santander", "Bradesco", "Caixa", "BB"]:
                            found_bank = part
                            break
                    
                    if found_bank == "Unknown":
                        # Try filename
                        if "Santander" in f.name: found_bank = "Santander"
                        elif "Bradesco" in f.name: found_bank = "Bradesco"
                        elif "Caixa" in f.name: found_bank = "Caixa"
                        elif "BB" in f.name: found_bank = "BB"
                        
                    # Extract Account fro Filename
                    # Same logic as file_parsers
                    stem = f.stem
                    import re
                    match = re.search(r"_([A-Za-z0-9-]+)$", stem)
                    if match:
                         conta = match.group(1)
                    else:
                         conta = stem.split("_")[-1]
                    
                    rows.append({
                        "Data": None, # Will be overridden by main.py
                        "Conta": conta,
                        "Banco": found_bank,
                        "Saldo": 0.00,
                        "Origem": f.name
                    })
                        
                except Exception as ex:
                    logger.error(f"Fallback failed for {f.name}: {ex}")
                    
        except Exception as e:
            logger.error(f"Error parsing file {f.name}: {e}")
            
    df = pd.DataFrame(rows)
    
    # Reorder columns as requested
    if not df.empty:
        required_cols = ["Data", "Conta", "Banco", "Saldo"]
        # Ensure all cols exist
        for col in required_cols:
            if col not in df.columns:
                 df[col] = None
        df = df[required_cols]
        
    logger.info(f"Extracted balances from {len(df)} files.")
    return df
