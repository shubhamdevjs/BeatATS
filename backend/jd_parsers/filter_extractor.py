"""Extract knockout filter requirements from JD text."""
import re
from typing import Dict, List, Optional, Any


# Work authorization patterns
WORK_AUTH_PATTERNS = [
    r'(?:legally\s+)?authorized\s+to\s+work',
    r'work\s+authorization',
    r'visa\s+sponsorship',
    r'us\s+citizen',
    r'permanent\s+resident',
    r'green\s+card',
    r'h1b',
    r'require.*?sponsorship',
    r'employment\s+eligibility',
]

# Location patterns
LOCATION_PATTERNS = [
    r'(?:must\s+)?(?:be\s+)?(?:located|based)\s+in\s+([A-Za-z\s,]+)',
    r'remote\s+(?:within|from|only)\s+([A-Za-z\s]+)',
    r'(?:us|united\s+states)\s+(?:only|based)',
    r'(?:work|working)\s+(?:from|in)\s+([A-Za-z\s,]+)',
]

# Experience patterns
EXPERIENCE_PATTERNS = [
    r'(\d+)\s*-\s*(\d+)\+?\s*(?:years?|yrs?)',  # Range: 0-2 years, 0-2+ years, 3-5 years
    r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)',  # X+ years of experience
    r'(?:minimum|at\s+least)\s+(\d+)\s*(?:years?|yrs?)',  # minimum X years
]

# Degree patterns
DEGREE_PATTERNS = [
    r"(?:bachelor'?s?|b\.?s\.?|b\.?a\.?)\s+(?:degree)?(?:\s+in\s+([A-Za-z\s]+))?",
    r"(?:master'?s?|m\.?s\.?|m\.?a\.?)\s+(?:degree)?(?:\s+in\s+([A-Za-z\s]+))?",
    r"(?:ph\.?d\.?|doctorate)\s+(?:in\s+([A-Za-z\s]+))?",
    r'(?:degree\s+)?(?:in|required)\s+(?:computer\s+science|cs|engineering)',
]

# Certification patterns
CERT_PATTERNS = [
    r'aws\s+certif(?:ied|ication)',
    r'gcp\s+certif(?:ied|ication)',
    r'azure\s+certif(?:ied|ication)',
    r'pmp\s+certif(?:ied|ication)',
    r'scrum\s+master',
    r'cissp',
    r'cpa',
    r'certified\s+([A-Za-z\s]+)',
]

# Security clearance patterns
CLEARANCE_PATTERNS = [
    r'security\s+clearance',
    r'secret\s+clearance',
    r'top\s+secret',
    r'ts/sci',
    r'government\s+clearance',
    r'dod\s+clearance',
]

# Language patterns
LANGUAGE_PATTERNS = [
    r'(?:fluent|proficient)\s+(?:in\s+)?([A-Za-z]+)',
    r'([A-Za-z]+)\s+(?:language\s+)?(?:required|fluency)',
    r'(?:speak|write)\s+([A-Za-z]+)',
]


def extract_filters(text: str) -> Dict[str, Any]:
    """
    Extract all knockout filter requirements from JD.
    
    Args:
        text: Full JD text
        
    Returns:
        Dict of filter types with extracted values
    """
    text_lower = text.lower()
    
    filters = {
        'work_authorization': _extract_work_auth(text_lower),
        'location': _extract_location(text),
        'years_experience': _extract_experience(text_lower),
        'degree': _extract_degree(text_lower),
        'certifications': _extract_certifications(text_lower),
        'clearance': _extract_clearance(text_lower),
        'languages': _extract_languages(text_lower),
    }
    
    return filters


def _extract_work_auth(text: str) -> Dict[str, Any]:
    """Extract work authorization requirements."""
    result = {
        'required': False,
        'sponsorship_available': None,
        'raw': None
    }
    
    for pattern in WORK_AUTH_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['required'] = True
            result['raw'] = match.group(0)
            
            # Check if sponsorship is available or not
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end]
            
            if 'no sponsorship' in context or 'not sponsor' in context or 'unable to sponsor' in context:
                result['sponsorship_available'] = False
            elif 'sponsor' in context:
                result['sponsorship_available'] = True
            
            break
    
    return result


def _extract_location(text: str) -> Dict[str, Any]:
    """Extract location requirements."""
    result = {
        'required': None,
        'remote_policy': None,
        'raw': None
    }
    
    text_lower = text.lower()
    
    # Check remote policy
    if 'fully remote' in text_lower or '100% remote' in text_lower:
        result['remote_policy'] = 'fully_remote'
    elif 'hybrid' in text_lower:
        result['remote_policy'] = 'hybrid'
    elif 'remote' in text_lower:
        # Check for location restrictions
        if 'us only' in text_lower or 'united states only' in text_lower:
            result['required'] = 'US'
            result['remote_policy'] = 'remote_us_only'
        else:
            result['remote_policy'] = 'remote'
    elif 'on-site' in text_lower or 'onsite' in text_lower:
        result['remote_policy'] = 'onsite'
    
    # Extract specific location
    for pattern in LOCATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['raw'] = match.group(0)
            if match.groups():
                result['required'] = match.group(1).strip()
            break
    
    return result


def _extract_experience(text: str) -> Dict[str, Any]:
    """Extract years of experience requirement."""
    result = {
        'min_years': None,
        'max_years': None,
        'raw': None
    }
    
    for pattern in EXPERIENCE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['raw'] = match.group(0)
            groups = match.groups()
            
            if len(groups) == 2 and groups[1]:  # Range like 0-2 years or 3-5 years
                min_val = int(groups[0])
                max_val = int(groups[1])
                # If min is 0, it means no minimum requirement
                result['min_years'] = None if min_val == 0 else min_val
                result['max_years'] = max_val
            else:
                min_val = int(groups[0])
                # If min is 0, it means no minimum requirement
                result['min_years'] = None if min_val == 0 else min_val
            break
    
    return result


def _extract_degree(text: str) -> Dict[str, Any]:
    """Extract degree requirements."""
    result = {
        'required': None,
        'level': None,
        'accepted_levels': [],  # NEW: list of acceptable degree levels
        'field': None,
        'raw': None
    }
    
    # Check for "PhD or MS" / "MS or PhD" patterns (accepts either)
    if re.search(r'ph\.?d\.?\s+or\s+m\.?s\.?', text, re.IGNORECASE) or \
       re.search(r'm\.?s\.?\s+or\s+ph\.?d\.?', text, re.IGNORECASE) or \
       re.search(r'phd\s+or\s+ms', text, re.IGNORECASE) or \
       re.search(r'ms\s+or\s+phd', text, re.IGNORECASE):
        result['level'] = 'masters'  # Minimum acceptable
        result['accepted_levels'] = ['masters', 'doctorate']
        result['required'] = True
    elif re.search(r'ph\.?d|phd|doctorate', text, re.IGNORECASE):
        result['level'] = 'doctorate'
        result['accepted_levels'] = ['doctorate']
        result['required'] = True
    elif re.search(r"master'?s?|m\.s\.?|m\.a\.?|\bms\b", text, re.IGNORECASE):
        result['level'] = 'masters'
        result['accepted_levels'] = ['masters', 'doctorate']  # Masters or higher
        result['required'] = True
    elif re.search(r"bachelor'?s?|b\.s\.?|b\.a\.?|\bbs\b|\bba\b", text, re.IGNORECASE):
        result['level'] = 'bachelors'
        result['accepted_levels'] = ['bachelors', 'masters', 'doctorate']  # Bachelors or higher
        result['required'] = True
    
    # Check for "or equivalent experience"
    if 'equivalent experience' in text or 'or equivalent' in text:
        result['required'] = 'or_equivalent'
    
    # Check for specific field
    cs_fields = ['computer science', 'software engineering', 'information technology', 'cs', 'engineering', 'statistics', 'applied math', 'electrical engineering']
    for field in cs_fields:
        if field in text:
            result['field'] = field
            break
    
    return result


def _extract_certifications(text: str) -> Dict[str, Any]:
    """Extract certification requirements."""
    result = {
        'required': [],
        'preferred': [],
        'raw': []
    }
    
    for pattern in CERT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            cert = match.group(0)
            result['raw'].append(cert)
            
            # Check context for required vs preferred
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end].lower()
            
            if 'required' in context or 'must' in context:
                result['required'].append(cert)
            else:
                result['preferred'].append(cert)
    
    return result


def _extract_clearance(text: str) -> Dict[str, Any]:
    """Extract security clearance requirements."""
    result = {
        'required': False,
        'level': None,
        'raw': None
    }
    
    for pattern in CLEARANCE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['required'] = True
            result['raw'] = match.group(0)
            
            # Determine level
            if 'top secret' in match.group(0).lower() or 'ts/sci' in match.group(0).lower():
                result['level'] = 'top_secret'
            elif 'secret' in match.group(0).lower():
                result['level'] = 'secret'
            else:
                result['level'] = 'unknown'
            break
    
    return result


def _extract_languages(text: str) -> Dict[str, Any]:
    """Extract language requirements."""
    result = {
        'required': [],
        'raw': []
    }
    
    # Common languages to look for
    languages = ['english', 'spanish', 'french', 'german', 'mandarin', 'chinese', 'japanese', 'korean', 'portuguese']
    
    text_lower = text.lower()
    
    for lang in languages:
        if lang in text_lower:
            # Check if it's a requirement
            pattern = rf'{lang}\s+(?:required|fluency|proficiency)'
            if re.search(pattern, text_lower):
                result['required'].append(lang.title())
                result['raw'].append(lang)
    
    return result
