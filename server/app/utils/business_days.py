from datetime import date, timedelta
import httpx
from loguru import logger

def get_holidays(year: int) -> set[date]:
    """Fetches national holidays from BrasilAPI for a given year."""
    try:
        response = httpx.get(f"https://brasilapi.com.br/api/feriados/v1/{year}", timeout=10.0)
        response.raise_for_status()
        holidays = {date.fromisoformat(h["date"]) for h in response.json()}
        return holidays
    except Exception as e:
        logger.error(f"Failed to fetch holidays for {year}: {e}")
        return set()

def calculate_transaction_period(saving_date: date) -> tuple[date, date]:
    """
    Calculates the transaction period based on the saving date (execution date).
    Logic mirrors the provided C# logic:
    
    1. Fetch holidays for the saving date's year.
    2. Check conditions:
       - saving_date - 1 is NOT a holiday
       - saving_date - 2 IS NOT a holiday
       - saving_date - 2 is NOT Saturday
       - saving_date - 2 is NOT Sunday
       
    3. If all conditions met (diaUtil2 scenario):
       - Period start: saving_date - 2 days
       - Period end: saving_date - 2 days
       
    4. Else if saving_date - 1 is Sunday:
       - Period start: saving_date - 3 days
       - Period end: saving_date - 3 days
       
    5. Else (Standard case):
       - Period start: saving_date - 1 day
       - Period end: saving_date - 1 day
       
    Note: The user request implies the period is a single day or range. 
    The provided logic 'DateTime.Now.AddDays(-X).ToString("dd/MM/yyyy - dd/MM/yyyy")' 
    suggests the start and end dates are the same for the determined day.
    """
    
    # We might need holidays from previous year if saving_date is Jan 1st/2nd
    holidays = get_holidays(saving_date.year)
    if saving_date.month == 1:
        holidays.update(get_holidays(saving_date.year - 1))

    # Helper dates
    d_minus_1 = saving_date - timedelta(days=1)
    d_minus_2 = saving_date - timedelta(days=2)
    d_minus_3 = saving_date - timedelta(days=3)

    # Condition checks
    # Weekday in python: Mon=0, Sun=6. Saturday=5, Sunday=6
    
    # "dicFeriados.Contains(DateTime.Now.AddDays(-1).ToString("yyyy-MM-dd"))" -> d_minus_1 in holidays
    # Wait, user logic said:
    # dicFeriados.Contains(...) && !dicFeriados.Contains(...)
    # Let's re-read carefully:
    # dicFeriados.Contains(d-1) && !dicFeriados.Contains(d-2) && d-2 not Sat && d-2 not Sun
    
    cond_d_minus_1_is_holiday = d_minus_1 in holidays
    cond_d_minus_2_not_holiday = d_minus_2 not in holidays
    cond_d_minus_2_not_weekend = d_minus_2.weekday() not in (5, 6) # 5=Sat, 6=Sun
    
    dia_util_2 = (
        cond_d_minus_1_is_holiday and 
        cond_d_minus_2_not_holiday and 
        cond_d_minus_2_not_weekend
    )
    
    period_start = None
    period_end = None

    if dia_util_2:
        # DateTime.Now.AddDays(-2)
        target_date = d_minus_2
    elif d_minus_1.weekday() == 6: # Sunday
        # DateTime.Now.AddDays(-3) -> Friday likely
        target_date = d_minus_3
    else:
        # DateTime.Now.AddDays(-1)
        target_date = d_minus_1
        
    return target_date, target_date
