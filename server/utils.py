"""
Utility functions for the application.
"""
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def get_real_date(date_str: str | None) -> str:
    """
    Adjusts the transaction date to the previous business day.
    
    Logic:
    - Monday (0) -> Friday (-3 days)
    - Other days -> Previous day (-1 day)
    
    Args:
        date_str: Date string in 'DD/MM/YYYY' or 'YYYY-MM-DD' format.
        
    Returns:
        Adjusted date string in 'DD/MM/YYYY' format, or "N/A" if invalid.
    """
    if not date_str:
        return "N/A"
    
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        try:
             dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
             logger.warning(f"Could not parse date: {date_str}")
             return date_str # Return original if parse fails

    weekday = dt.weekday() # Monday passed as 0, Sunday as 6
    
    if weekday == 0: # Monday
        real_date = dt - timedelta(days=3) # Shift back to Friday
    else:
        real_date = dt - timedelta(days=1) # Shift back 1 day
        
    return real_date.strftime("%d/%m/%Y")

def is_holiday(date_obj: datetime.date) -> bool:
    """
    Check if a date is a national holiday in Brazil using BrasilAPI.
    
    Args:
        date_obj: Date to check.
        
    Returns:
        bool: True if it is a holiday, False otherwise.
    """
    import requests
    try:
        from server.config import Config
        year = date_obj.year
        url = f"{Config.BRASIL_API_URL}/{year}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        holidays = response.json()
        
        target_str = date_obj.strftime("%Y-%m-%d")
        for h in holidays:
            if h.get("date") == target_str:
                logger.info(f"Holiday detected: {h.get('name')} on {target_str}")
                return True
        return False
    except Exception as e:
        logger.warning(f"Failed to check holidays via API: {e}. Assuming business day.")
        return False

def get_previous_business_day(reference_date: datetime.date = None) -> str:
    """
    Calculate the previous business day relative to the reference date.
    Considers weekends and national holidays.
    
    Args:
        reference_date: Starting date. Defaults to today.
        
    Returns:
        str: Previous business day in 'DD/MM/YYYY' format.
    """
    if reference_date is None:
        reference_date = datetime.now().date()
        
    # Start checking from yesterday
    candidate = reference_date - timedelta(days=1)
    
    while True:
        # Check weekend (Saturday=5, Sunday=6)
        if candidate.weekday() >= 5:
            candidate -= timedelta(days=1)
            continue
            
        # Check holiday
        if is_holiday(candidate):
            candidate -= timedelta(days=1)
            continue
            
        # Found business day
        break
        
    return candidate.strftime("%d/%m/%Y")
