"""Education section parsing from resumes."""
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.date_utils import parse_date_range


# Degree patterns
DEGREE_PATTERNS = {
    'doctorate': [r'ph\.?d\.?', r'doctor', r'doctorate'],
    'masters': [r'm\.?s\.?', r'master', r'm\.?a\.?', r'm\.?b\.?a\.?', r'm\.?eng\.?'],
    'bachelors': [r'b\.?s\.?', r'bachelor', r'b\.?a\.?', r'b\.?e\.?', r'b\.?tech\.?'],
    'associate': [r'a\.?s\.?', r'associate', r'a\.?a\.?'],
    'certificate': [r'certificate', r'certification', r'diploma']
}

# Common field keywords
FIELD_KEYWORDS = [
    'computer science', 'software engineering', 'information technology',
    'electrical engineering', 'mechanical engineering', 'data science',
    'artificial intelligence', 'machine learning', 'business administration',
    'mathematics', 'physics', 'chemistry', 'biology', 'economics',
    'information systems', 'cybersecurity', 'computer engineering'
]


def parse_education(section_text: str) -> List[Dict[str, Any]]:
    """Parse education section into structured entries."""
    if not section_text:
        return []
    
    entries = []
    blocks = _split_education_blocks(section_text)
    
    for block in blocks:
        entry = _parse_education_block(block)
        if entry:
            entries.append(entry)
    
    return entries


def _split_education_blocks(text: str) -> List[str]:
    """Split education section into individual entries."""
    blocks = []
    lines = text.split('\n')
    current_block = []
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped:
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
            continue
        
        if current_block and _looks_like_school(stripped):
            blocks.append('\n'.join(current_block))
            current_block = [line]
        else:
            current_block.append(line)
    
    if current_block:
        blocks.append('\n'.join(current_block))
    
    return blocks


def _looks_like_school(line: str) -> bool:
    """Check if line looks like start of a school entry."""
    line_lower = line.lower()
    
    school_keywords = ['university', 'college', 'institute', 'school', 'academy']
    if any(kw in line_lower for kw in school_keywords):
        return True
    
    for patterns in DEGREE_PATTERNS.values():
        for pattern in patterns:
            if re.search(pattern, line_lower):
                return True
    
    return False


def _parse_education_block(block: str) -> Optional[Dict[str, Any]]:
    """Parse a single education block."""
    lines = [l.strip() for l in block.split('\n') if l.strip()]
    
    if not lines:
        return None
    
    entry = {
        'school': None,
        'degree': None,
        'major': None,
        'minor': None,
        'gpa': None,
        'dates': {'start': None, 'end': None, 'raw': None},
        'courses': [],
        'honors': []
    }
    
    combined = ' '.join(lines)
    
    entry['school'] = _extract_school(combined)
    entry['degree'] = _extract_degree(combined)
    entry['major'] = _extract_major(combined)
    
    # Extract dates
    date_match = re.search(
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*'?\d{2,4}|\d{4})"
        r"\s*[-\u2013\u2014]+\s*"
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*'?\d{2,4}|\d{4}|Present|Current|Expected)",
        combined,
        re.IGNORECASE
    )
    
    if date_match:
        entry['dates'] = parse_date_range(date_match.group(0))
    else:
        year_match = re.search(r'(?:Expected|Graduation|Class of)?\s*(20\d{2})', combined, re.IGNORECASE)
        if year_match:
            entry['dates']['end'] = f"{year_match.group(1)}-05"
            entry['dates']['raw'] = year_match.group(0)
    
    # Extract GPA
    gpa_match = re.search(r'GPA[:\s]*(\d+\.\d+)', combined, re.IGNORECASE)
    if gpa_match:
        entry['gpa'] = float(gpa_match.group(1))
    
    # Extract coursework
    course_match = re.search(r'(?:Relevant\s+)?Courses?(?:work)?[:\s]+(.+?)(?=\n\n|$)', combined, re.IGNORECASE | re.DOTALL)
    if course_match:
        entry['courses'] = _parse_course_list(course_match.group(1))
    
    # Extract honors
    honors_keywords = ['magna cum laude', 'summa cum laude', 'cum laude', "dean's list", 'honors', 'distinction']
    for keyword in honors_keywords:
        if keyword in combined.lower():
            entry['honors'].append(keyword.title())
    
    if entry['school'] or entry['degree']:
        return entry
    
    return None


def _extract_school(text: str) -> Optional[str]:
    """Extract school name from text."""
    patterns = [
        r'([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:University|College|Institute|School)(?:\s+of\s+[A-Za-z]+)?)',
        r'((?:University|College|Institute)\s+of\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return None


def _extract_degree(text: str) -> Optional[str]:
    """Extract degree type from text."""
    text_lower = text.lower()
    
    for degree_type, patterns in DEGREE_PATTERNS.items():
        for pattern in patterns:
            if re.search(r'\b' + pattern + r'\b', text_lower):
                match = re.search(r'(' + pattern + r'\.?\s*(?:in|of)?\s*[A-Za-z\s]+)', text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
                
                abbrevs = {
                    'doctorate': 'Ph.D.',
                    'masters': 'M.S.',
                    'bachelors': 'B.S.',
                    'associate': 'A.S.',
                    'certificate': 'Certificate'
                }
                return abbrevs.get(degree_type)
    
    return None


def _extract_major(text: str) -> Optional[str]:
    """Extract major/field of study from text."""
    text_lower = text.lower()
    
    for field in FIELD_KEYWORDS:
        if field in text_lower:
            return field.title()
    
    match = re.search(r'(?:in|major(?:ing)?(?:\s+in)?)[:\s]+([A-Za-z\s]+?)(?:\,|\.|with|and|\n|$)', text, re.IGNORECASE)
    if match:
        major = match.group(1).strip()
        if 3 < len(major) < 50:
            return major.title()
    
    return None


def _parse_course_list(text: str) -> List[str]:
    """Parse a list of courses from text."""
    courses = []
    
    if ',' in text:
        parts = text.split(',')
    elif ';' in text:
        parts = text.split(';')
    else:
        parts = text.split('\n')
    
    for part in parts:
        course = part.strip()
        course = re.sub(r'^[-*\u2022]\s*', '', course)
        
        if course and 3 < len(course) < 60:
            courses.append(course)
    
    return courses[:10]
