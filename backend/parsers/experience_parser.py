"""Experience section parsing from resumes."""
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.date_utils import parse_date_range
from utils.text_utils import extract_bullets, extract_metrics
from parsers.skills_parser import extract_skills_from_text


# Patterns for detecting experience entries
COMPANY_TITLE_PATTERNS = [
    # Title at Company
    r'^(.+?)\s+at\s+(.+?)(?:\s*[\|,]\s*(.+?))?$',
    # Company | Title or Company - Title
    r'^(.+?)\s*[\|\-–—]\s*(.+?)$',
    # Just Title (Company on next line)
    r'^([A-Z][A-Za-z\s]+(?:Engineer|Developer|Manager|Analyst|Designer|Lead|Director|Architect|Specialist|Coordinator|Consultant|Intern))$',
]

# Employment type patterns
EMPLOYMENT_TYPES = {
    'full_time': ['full-time', 'full time', 'permanent'],
    'part_time': ['part-time', 'part time'],
    'contract': ['contract', 'contractor', 'consulting'],
    'internship': ['intern', 'internship', 'trainee'],
    'freelance': ['freelance', 'self-employed', 'independent']
}


def parse_experience(section_text: str) -> List[Dict[str, Any]]:
    """
    Parse experience section into structured entries.
    
    Args:
        section_text: Text from experience section
        
    Returns:
        List of experience entry dicts
    """
    if not section_text:
        return []
    
    entries = []
    
    # Split into individual experience blocks
    blocks = _split_experience_blocks(section_text)
    
    for block in blocks:
        entry = _parse_experience_block(block)
        if entry:
            entries.append(entry)
    
    return entries


def _split_experience_blocks(text: str) -> List[str]:
    """
    Split experience section into individual job blocks.
    """
    blocks = []
    lines = text.split('\n')
    current_block = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if not stripped:
            # Empty line might indicate block boundary
            if current_block and len(current_block) > 1:
                # Check if next non-empty line looks like a new entry
                next_lines = [l.strip() for l in lines[i+1:i+3] if l.strip()]
                if next_lines and _looks_like_new_entry(next_lines[0]):
                    blocks.append('\n'.join(current_block))
                    current_block = []
            continue
        
        # Check if this line starts a new entry
        if current_block and _looks_like_new_entry(stripped):
            blocks.append('\n'.join(current_block))
            current_block = [line]
        else:
            current_block.append(line)
    
    if current_block:
        blocks.append('\n'.join(current_block))
    
    return blocks


def _looks_like_new_entry(line: str) -> bool:
    """
    Check if a line looks like the start of a new experience entry.
    """
    line = line.strip()
    
    # Contains a date range
    if re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Present|\d{4})', line, re.IGNORECASE):
        return True
    
    # Contains separator that might indicate company | title
    if re.search(r'\s+[\|\-–—]\s+', line):
        return True
    
    # Contains "at" which often indicates "Title at Company"
    if re.search(r'\s+at\s+', line, re.IGNORECASE):
        return True
    
    # All caps or title case and relatively short (might be company name)
    if line.isupper() and len(line) < 50:
        return True
    
    return False


def _parse_experience_block(block: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single experience block into structured data.
    """
    lines = [l.strip() for l in block.split('\n') if l.strip()]
    
    if not lines:
        return None
    
    entry = {
        'company': None,
        'company_normalized': None,
        'title': None,
        'title_normalized': None,
        'employment_type': 'full_time',
        'location': {'raw': None},
        'dates': {'start': None, 'end': None, 'raw': None},
        'bullets': [],
        'skills_summary': []
    }
    
    # First line(s) typically contain company/title info
    header_lines = []
    bullet_lines = []
    
    for line in lines:
        if line.startswith(('•', '-', '*', '◦', '●')) or re.match(r'^\d+\.', line):
            bullet_lines.append(line)
        elif not header_lines or (not bullet_lines and len(header_lines) < 3):
            header_lines.append(line)
        else:
            bullet_lines.append(line)
    
    # Parse header
    _parse_experience_header(header_lines, entry)
    
    # Parse bullets
    all_skills = set()
    for bullet_text in bullet_lines:
        # Clean bullet markers
        text = re.sub(r'^[\•\-\*\◦\●]\s*', '', bullet_text)
        text = re.sub(r'^\d+\.\s*', '', text)
        text = text.strip()
        
        if not text or len(text) < 10:
            continue
        
        metrics = extract_metrics(text)
        skills_found = extract_skills_from_text(text)
        all_skills.update(skills_found)
        
        entry['bullets'].append({
            'text': text,
            'metrics': metrics,
            'skills_found': skills_found,
            'confidence': 0.85
        })
    
    entry['skills_summary'] = list(all_skills)
    
    # Only return if we have meaningful data
    if entry['company'] or entry['title']:
        return entry
    
    return None


def _parse_experience_header(lines: List[str], entry: Dict) -> None:
    """
    Parse header lines to extract company, title, dates, location.
    """
    if not lines:
        return
    
    combined = ' '.join(lines)
    
    # Try to extract dates first
    date_match = re.search(
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{2,4}|\d{1,2}/\d{2,4}|\d{4})'
        r'\s*[\-–—to]+\s*'
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{2,4}|\d{1,2}/\d{2,4}|\d{4}|Present|Current)',
        combined,
        re.IGNORECASE
    )
    
    if date_match:
        entry['dates'] = parse_date_range(date_match.group(0))
        # Remove date from combined for further parsing
        combined = combined.replace(date_match.group(0), ' ')
    
    # Try patterns to extract company and title
    for pattern in COMPANY_TITLE_PATTERNS:
        match = re.match(pattern, combined.strip(), re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                # Determine which is company vs title
                part1, part2 = groups[0].strip(), groups[1].strip()
                
                # Heuristic: if "at" pattern, first is title
                if ' at ' in combined.lower():
                    entry['title'] = part1
                    entry['company'] = part2
                else:
                    # Usually Company | Title format
                    entry['company'] = part1
                    entry['title'] = part2
                break
    
    # Fallback: use first line as title/company combo
    if not entry['company'] and not entry['title'] and lines:
        first_line = lines[0]
        
        # Check for separator
        if re.search(r'\s*[\|\-–—]\s*', first_line):
            parts = re.split(r'\s*[\|\-–—]\s*', first_line, 1)
            if len(parts) == 2:
                entry['company'] = parts[0].strip()
                entry['title'] = parts[1].strip()
        else:
            entry['title'] = first_line.strip()
    
    # Look for location in remaining lines
    for line in lines[1:]:
        if re.search(r'[A-Z][a-z]+,?\s*[A-Z]{2}', line):
            entry['location']['raw'] = line.strip()
            break
    
    # Normalize
    if entry['company']:
        entry['company_normalized'] = entry['company'].lower().strip()
    if entry['title']:
        entry['title_normalized'] = _normalize_title(entry['title'])
    
    # Detect employment type
    combined_lower = combined.lower()
    for emp_type, keywords in EMPLOYMENT_TYPES.items():
        if any(kw in combined_lower for kw in keywords):
            entry['employment_type'] = emp_type
            break


def _normalize_title(title: str) -> str:
    """Normalize job title for matching."""
    title = title.lower().strip()
    
    # Remove level indicators
    title = re.sub(r'\b(senior|sr\.?|junior|jr\.?|lead|staff|principal|associate)\b', '', title)
    title = re.sub(r'\b[iv]+\b', '', title)  # Roman numerals
    title = re.sub(r'\b[1-5]\b', '', title)  # Level numbers
    
    # Normalize common variations
    title = title.replace('software engineer', 'software engineer')
    title = title.replace('software developer', 'software engineer')
    title = title.replace('web developer', 'software engineer')
    title = title.replace('swe', 'software engineer')
    
    return ' '.join(title.split())
