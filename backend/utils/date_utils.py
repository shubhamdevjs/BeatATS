"""Date parsing and normalization utilities."""
import re
from typing import Dict, Optional, Tuple
from datetime import datetime
from dateutil import parser as date_parser


# Common date patterns in resumes
DATE_PATTERNS = [
    # Month Year formats
    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*'?\d{2,4}",
    # MM/YYYY or MM-YYYY
    r'\d{1,2}[/\-]\d{4}',
    # YYYY-MM
    r'\d{4}[/\-]\d{1,2}',
    # Just year
    r'(?:19|20)\d{2}',
]

PRESENT_KEYWORDS = ['present', 'current', 'now', 'ongoing', 'today']


def normalize_date(date_str: str) -> Optional[str]:
    """
    Normalize a date string to ISO format (YYYY-MM).
    
    Args:
        date_str: Raw date string from resume
        
    Returns:
        ISO formatted date string (YYYY-MM) or None if unparseable
    """
    if not date_str:
        return None
    
    date_str = date_str.strip().lower()
    
    # Check for present/current
    if any(keyword in date_str for keyword in PRESENT_KEYWORDS):
        return None  # None indicates present/ongoing
    
    try:
        # Try dateutil parser first
        parsed = date_parser.parse(date_str, fuzzy=True)
        return parsed.strftime('%Y-%m')
    except (ValueError, TypeError):
        pass
    
    # Try extracting just year
    year_match = re.search(r'(19|20)\d{2}', date_str)
    if year_match:
        return f"{year_match.group(0)}-01"
    
    return None


def parse_date_range(text: str) -> Dict[str, Optional[str]]:
    """
    Parse a date range string like "Jan 2020 - Present" or "2019-2021".
    
    Args:
        text: Raw date range text
        
    Returns:
        Dict with 'start', 'end', and 'raw' keys
    """
    result = {
        "start": None,
        "end": None,
        "raw": text.strip()
    }
    
    if not text:
        return result
    
    text = text.strip()
    
    # Common separators
    separators = [' - ', ' – ', ' — ', '-', '–', '—', ' to ', ' until ']
    
    parts = None
    for sep in separators:
        if sep in text.lower():
            parts = text.split(sep, 1) if sep in text else text.lower().split(sep, 1)
            break
    
    if parts and len(parts) == 2:
        result["start"] = normalize_date(parts[0])
        result["end"] = normalize_date(parts[1])
    elif parts and len(parts) == 1:
        result["start"] = normalize_date(parts[0])
    else:
        # Single date or just year
        result["start"] = normalize_date(text)
    
    return result


def extract_date_from_text(text: str) -> Optional[str]:
    """
    Extract the first date-like pattern from text.
    
    Args:
        text: Text to search for dates
        
    Returns:
        Extracted date string or None
    """
    combined_pattern = '|'.join(f'({p})' for p in DATE_PATTERNS)
    match = re.search(combined_pattern, text, re.IGNORECASE)
    
    if match:
        return match.group(0)
    return None


def calculate_duration_months(start: Optional[str], end: Optional[str]) -> Optional[int]:
    """
    Calculate duration in months between two dates.
    
    Args:
        start: Start date in YYYY-MM format
        end: End date in YYYY-MM format (None = present)
        
    Returns:
        Duration in months or None if cannot calculate
    """
    if not start:
        return None
    
    try:
        start_dt = datetime.strptime(start, '%Y-%m')
        
        if end:
            end_dt = datetime.strptime(end, '%Y-%m')
        else:
            end_dt = datetime.now()
        
        months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)
        return max(0, months)
    except ValueError:
        return None
