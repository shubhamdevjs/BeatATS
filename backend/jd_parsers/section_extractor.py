"""JD section extraction and classification."""
import re
from typing import Dict, List, Optional, Tuple


# Section header patterns
SECTION_PATTERNS = {
    'requirements': [
        r'(?:key\s+)?requirements?',
        r'qualifications?',
        r'what\s+you(?:\'ll)?\s+need',
        r'must\s+have',
        r'required\s+skills?',
        r'minimum\s+qualifications?',
        r'basic\s+qualifications?',
    ],
    'preferred': [
        r'preferred\s+qualifications?',
        r'nice\s+to\s+have',
        r'bonus\s+(?:points?|skills?)',
        r'desired\s+(?:skills?|qualifications?)',
        r'additional\s+qualifications?',
        r'plus(?:es)?',
    ],
    'responsibilities': [
        r'responsibilities',
        r'what\s+you(?:\'ll)?\s+do',
        r'job\s+duties',
        r'role\s+(?:overview|description)',
        r'key\s+(?:duties|tasks)',
        r'day\s+to\s+day',
    ],
    'about': [
        r'about\s+(?:us|the\s+(?:company|team|role))',
        r'who\s+we\s+are',
        r'company\s+(?:overview|description)',
    ],
    'benefits': [
        r'benefits?',
        r'perks?',
        r'what\s+we\s+offer',
        r'compensation',
    ]
}

# Hard requirement signal words
HARD_SIGNALS = [
    'required', 'must', 'need', 'essential', 'mandatory',
    'minimum', 'at least', 'necessary'
]

# Soft requirement signal words
SOFT_SIGNALS = [
    'preferred', 'nice to have', 'bonus', 'ideal', 'desired',
    'plus', 'advantage', 'beneficial', 'helpful'
]


def extract_sections(text: str) -> Dict[str, Dict]:
    """
    Extract and classify sections from JD text.
    
    Args:
        text: Full job description text
        
    Returns:
        Dict with section names mapped to content and metadata
    """
    lines = text.split('\n')
    sections = {}
    current_section = None
    current_content = []
    current_is_hard = True
    
    for i, line in enumerate(lines):
        section_match = _detect_section(line)
        
        if section_match:
            # Save previous section
            if current_section:
                sections[current_section] = {
                    'content': '\n'.join(current_content),
                    'items': _extract_list_items('\n'.join(current_content)),
                    'is_hard_requirement': current_is_hard
                }
            
            current_section = section_match[0]
            current_is_hard = section_match[1]
            current_content = []
        elif current_section:
            current_content.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = {
            'content': '\n'.join(current_content),
            'items': _extract_list_items('\n'.join(current_content)),
            'is_hard_requirement': current_is_hard
        }
    
    # If no sections detected, try to infer from content
    if not sections:
        sections['_raw'] = {
            'content': text,
            'items': _extract_list_items(text),
            'is_hard_requirement': True
        }
    
    return sections


def _detect_section(line: str) -> Optional[Tuple[str, bool]]:
    """
    Detect if line is a section header.
    
    Returns:
        Tuple of (section_name, is_hard_requirement) or None
    """
    line_clean = line.strip().lower()
    line_clean = re.sub(r'^[\*\-\#\:]+\s*', '', line_clean)
    line_clean = line_clean.rstrip(':')
    
    if not line_clean or len(line_clean) > 60:
        return None
    
    for section_type, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, line_clean, re.IGNORECASE):
                is_hard = section_type in ['requirements', 'responsibilities']
                return (section_type, is_hard)
    
    return None


def _extract_list_items(text: str) -> List[str]:
    """Extract bullet/numbered list items from text."""
    items = []
    
    for line in text.split('\n'):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Check for bullet patterns
        match = re.match(r'^[\u2022\u2023\u25E6\u2043\u2219●○◦•\-\*]\s*(.+)$', line)
        if match:
            items.append(match.group(1).strip())
            continue
        
        # Check for numbered patterns
        match = re.match(r'^\d+[\.\)]\s*(.+)$', line)
        if match:
            items.append(match.group(1).strip())
            continue
        
        # Check for lettered patterns
        match = re.match(r'^[a-z][\.\)]\s+(.+)$', line, re.IGNORECASE)
        if match:
            items.append(match.group(1).strip())
    
    return items


def classify_requirement(text: str) -> str:
    """
    Classify if a requirement text is hard or soft.
    
    Returns:
        'hard', 'soft', or 'neutral'
    """
    text_lower = text.lower()
    
    for signal in HARD_SIGNALS:
        if signal in text_lower:
            return 'hard'
    
    for signal in SOFT_SIGNALS:
        if signal in text_lower:
            return 'soft'
    
    return 'neutral'


def extract_role_info(text: str) -> Dict[str, Optional[str]]:
    """
    Extract role metadata from JD.
    
    Returns:
        Dict with title, level, location_policy, employment_type
    """
    role = {
        'title': None,
        'level': None,
        'location_policy': None,
        'employment_type': None
    }
    
    text_lower = text.lower()
    
    # Detect level
    if any(w in text_lower for w in ['senior', 'sr.', 'sr ', 'lead', 'principal', 'staff']):
        role['level'] = 'senior'
    elif any(w in text_lower for w in ['junior', 'jr.', 'jr ', 'entry', 'associate', 'i ', ' i,']):
        role['level'] = 'junior'
    elif any(w in text_lower for w in ['mid', 'intermediate', 'ii ', ' ii,']):
        role['level'] = 'mid'
    
    # Detect location policy
    if 'remote' in text_lower:
        if any(w in text_lower for w in ['fully remote', '100% remote', 'remote only']):
            role['location_policy'] = 'remote'
        elif 'hybrid' in text_lower:
            role['location_policy'] = 'hybrid'
        else:
            role['location_policy'] = 'remote_possible'
    elif 'on-site' in text_lower or 'onsite' in text_lower or 'in-office' in text_lower:
        role['location_policy'] = 'onsite'
    
    # Detect employment type
    if 'full-time' in text_lower or 'full time' in text_lower:
        role['employment_type'] = 'full_time'
    elif 'part-time' in text_lower or 'part time' in text_lower:
        role['employment_type'] = 'part_time'
    elif 'contract' in text_lower or 'contractor' in text_lower:
        role['employment_type'] = 'contract'
    elif 'intern' in text_lower:
        role['employment_type'] = 'internship'
    
    # Try to extract title from first lines
    lines = text.split('\n')
    for line in lines[:5]:
        line = line.strip()
        if line and 10 < len(line) < 60:
            if any(w in line.lower() for w in ['engineer', 'developer', 'manager', 'analyst', 'designer']):
                role['title'] = line
                break
    
    return role
