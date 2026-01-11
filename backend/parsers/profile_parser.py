"""Profile extraction from resume header."""
import re
from typing import Dict, List, Any, Optional


# Email pattern
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# Phone patterns (various formats)
PHONE_PATTERNS = [
    r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
    r'\+\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',  # International
]

# URL patterns
URL_PATTERNS = {
    'linkedin': r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+/?',
    'github': r'(?:https?://)?(?:www\.)?github\.com/[\w\-]+/?',
    'portfolio': r'(?:https?://)?(?:www\.)?[\w\-]+\.(?:com|io|dev|me|co|org)/[\w\-/]*',
    'twitter': r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/[\w\-]+/?',
}

# Location patterns
LOCATION_PATTERNS = [
    # City, State, Country
    r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),?\s*([A-Z]{2}),?\s*(?:USA?|United States)?',
    # City, Country
    r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),?\s*(USA?|UK|India|Canada|Australia|Germany)',
]


def parse_profile(text: str, header_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract profile information from resume text.
    
    Args:
        text: Full resume text
        header_text: Optional header portion (before first section)
        
    Returns:
        Profile dict with name, contact info, location, links
    """
    # Use header text if available, otherwise use first portion
    search_text = header_text or text[:2000]
    
    profile = {
        'name': _extract_name(search_text),
        'headline': _extract_headline(search_text),
        'emails': _extract_emails(search_text),
        'phones': _extract_phones(search_text),
        'location': _extract_location(search_text),
        'links': _extract_links(search_text)
    }
    
    return profile


def _extract_name(text: str) -> Optional[str]:
    """
    Extract candidate name from header text.
    Heuristic: First line that looks like a name (2-4 capitalized words).
    Skip section headers and contact info.
    """
    lines = text.split('\n')
    
    # Common section headers to skip
    section_headers = {
        'education', 'experience', 'skills', 'projects', 'summary', 
        'work experience', 'technical skills', 'objective', 'profile',
        'certifications', 'awards', 'publications', 'languages'
    }
    
    for line in lines[:15]:  # Check first 15 lines
        line = ' '.join(line.split())  # Normalize all whitespace
        
        if not line or len(line) < 3:
            continue
        
        # Skip if it's a known section header
        if line.lower() in section_headers:
            continue
        
        # Skip if it looks like contact info
        if '@' in line or 'http' in line.lower() or re.search(r'\d{3}[-.\s]?\d{3}', line):
            continue
        
        # Skip if ALL CAPS (likely a header) and single word
        if line.isupper() and len(line.split()) <= 2:
            continue
        
        # Skip if contains pipe (usually "Title | Location")
        if '|' in line and any(kw in line.lower() for kw in ['engineer', 'developer', 'manager']):
            continue
        
        # Check if it looks like a name (2-4 capitalized words)
        words = line.split()
        if 2 <= len(words) <= 4:
            # All words should start with uppercase
            if all(word[0].isupper() for word in words if word):
                # Only letters, hyphens, apostrophes, spaces, and periods
                if re.match(r"^[A-Za-z\-'\s\.]+$", line):
                    return line
    
    return None


def _extract_headline(text: str) -> Optional[str]:
    """
    Extract job title/headline from header.
    Usually appears near the name or in summary.
    """
    lines = text.split('\n')
    
    # Common title keywords
    title_keywords = [
        'engineer', 'developer', 'designer', 'manager', 'analyst',
        'scientist', 'architect', 'consultant', 'specialist', 'lead',
        'director', 'administrator', 'coordinator', 'intern', 'associate'
    ]
    
    for line in lines[:15]:
        line = line.strip()
        
        if not line or len(line) > 100:
            continue
        
        line_lower = line.lower()
        
        # Check if line contains a title keyword
        if any(keyword in line_lower for keyword in title_keywords):
            # Make sure it's not part of experience section
            if not any(word in line_lower for word in ['at', 'from', 'to', '-', '–']):
                # Clean up the line
                cleaned = re.sub(r'\|.*', '', line).strip()
                if len(cleaned) < 60:
                    return cleaned
    
    return None


def _extract_emails(text: str) -> List[str]:
    """Extract all email addresses from text."""
    emails = re.findall(EMAIL_PATTERN, text, re.IGNORECASE)
    return list(set(emails))


def _extract_phones(text: str) -> List[str]:
    """Extract phone numbers from text."""
    phones = []
    
    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, text)
        phones.extend(matches)
    
    # Clean and normalize
    cleaned = []
    for phone in phones:
        # Remove extra characters
        normalized = re.sub(r'[^\d+]', '', phone)
        if 10 <= len(normalized) <= 15:
            cleaned.append(phone.strip())
    
    return list(set(cleaned))


def _extract_location(text: str) -> Dict[str, Optional[str]]:
    """Extract location information from text."""
    location = {
        'city': None,
        'state': None,
        'country': None,
        'raw': None
    }
    
    # Check for location patterns
    for pattern in LOCATION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            location['city'] = groups[0] if groups else None
            if len(groups) > 1:
                # Determine if second group is state or country
                second = groups[1]
                if len(second) == 2 and second.isupper():
                    location['state'] = second
                    location['country'] = 'US'
                else:
                    location['country'] = second
            
            location['raw'] = match.group(0)
            break
    
    return location


def _extract_links(text: str) -> List[Dict[str, str]]:
    """Extract social and professional links from text."""
    links = []
    
    for link_type, pattern in URL_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Ensure URL has protocol
            url = match if match.startswith('http') else f'https://{match}'
            links.append({
                'type': link_type,
                'url': url.rstrip('/')
            })
    
    return links


def build_profile_evidence(profile: Dict, text: str) -> List[Dict]:
    """
    Build evidence entries for profile fields.
    
    Args:
        profile: Parsed profile dict
        text: Source text
        
    Returns:
        List of evidence entries
    """
    evidence = []
    
    # Find context for each field
    if profile.get('name'):
        context = _find_context(profile['name'], text)
        evidence.append({
            'field': 'profile.name',
            'value': profile['name'],
            'page': 1,
            'context': context,
            'confidence': 0.9
        })
    
    for i, email in enumerate(profile.get('emails', [])):
        context = _find_context(email, text)
        evidence.append({
            'field': f'profile.emails[{i}]',
            'value': email,
            'page': 1,
            'context': context,
            'confidence': 0.99
        })
    
    for i, phone in enumerate(profile.get('phones', [])):
        context = _find_context(phone, text)
        evidence.append({
            'field': f'profile.phones[{i}]',
            'value': phone,
            'page': 1,
            'context': context,
            'confidence': 0.95
        })
    
    return evidence


def _find_context(value: str, text: str, context_chars: int = 50) -> str:
    """Find surrounding context for a value in text."""
    idx = text.find(value)
    if idx == -1:
        return value
    
    start = max(0, idx - context_chars)
    end = min(len(text), idx + len(value) + context_chars)
    
    context = text[start:end]
    # Clean up whitespace
    context = ' '.join(context.split())
    
    return context
