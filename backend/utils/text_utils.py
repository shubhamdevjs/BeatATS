"""Text processing utilities for resume parsing."""
import re
from typing import List, Tuple


def clean_text(text: str) -> str:
    """
    Clean and normalize text from resume.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common artifacts
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    return text.strip()


def extract_bullets(text: str) -> List[str]:
    """
    Extract bullet points from text.
    
    Args:
        text: Text potentially containing bullet points
        
    Returns:
        List of bullet point texts
    """
    bullets = []
    
    # Common bullet patterns
    bullet_patterns = [
        r'^[\u2022\u2023\u25E6\u2043\u2219●○◦•]\s*(.+)$',  # Unicode bullets
        r'^[\-\*\+]\s+(.+)$',  # ASCII bullets
        r'^(?:\d+[.\)]\s*)(.+)$',  # Numbered lists
        r'^[a-z][.\)]\s+(.+)$',  # Lettered lists
    ]
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        for pattern in bullet_patterns:
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                bullets.append(match.group(1).strip())
                break
        else:
            # Check if line starts with action verb (likely a bullet)
            action_verbs = [
                'developed', 'designed', 'implemented', 'created', 'built', 
                'led', 'managed', 'improved', 'reduced', 'increased',
                'achieved', 'established', 'executed', 'delivered', 'optimized',
                'architected', 'automated', 'collaborated', 'coordinated', 'deployed',
                'engineered', 'enhanced', 'integrated', 'launched', 'maintained',
                'mentored', 'migrated', 'orchestrated', 'pioneered', 'refactored',
                'scaled', 'spearheaded', 'streamlined', 'transformed', 'utilized'
            ]
            first_word = line.split()[0].lower() if line.split() else ''
            if first_word in action_verbs and len(line) > 20:
                bullets.append(line)
    
    return bullets


def extract_metrics(text: str) -> List[str]:
    """
    Extract quantifiable metrics from text.
    
    Args:
        text: Bullet point or description text
        
    Returns:
        List of extracted metrics
    """
    metrics = []
    
    # Patterns for common metrics
    patterns = [
        # Percentages
        r'\d+(?:\.\d+)?%',
        # Dollar amounts
        r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:M|K|B|million|billion|thousand))?',
        # Numbers with units
        r'\d+(?:,\d{3})*(?:\.\d+)?\s*(?:K|M|B|users|customers|requests|transactions|orders|visitors|downloads|installs)?',
        # Time improvements
        r'(?:\d+(?:\.\d+)?x|\d+(?:\.\d+)?-fold)',
        # Latency/performance
        r'(?:sub-?)?\d+(?:\.\d+)?\s*(?:ms|seconds?|minutes?|hours?)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        metrics.extend(matches)
    
    return list(set(metrics))  # Remove duplicates


def split_into_sections(text: str) -> List[Tuple[str, str]]:
    """
    Split text into sections based on headers.
    
    Args:
        text: Full resume text
        
    Returns:
        List of (section_name, section_content) tuples
    """
    # Common section header patterns
    section_headers = [
        'experience', 'work experience', 'professional experience', 'employment',
        'education', 'academic', 'academics',
        'skills', 'technical skills', 'core competencies', 'technologies',
        'projects', 'personal projects', 'academic projects',
        'summary', 'professional summary', 'objective', 'profile',
        'certifications', 'certificates', 'licenses',
        'awards', 'honors', 'achievements', 'accomplishments',
        'publications', 'research',
        'volunteer', 'volunteering', 'community',
        'languages', 'interests', 'hobbies'
    ]
    
    # Build regex pattern for headers
    header_pattern = r'^[\s]*(' + '|'.join(re.escape(h) for h in section_headers) + r')[\s]*[:]*[\s]*$'
    
    sections = []
    lines = text.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        # Check if this line is a section header
        match = re.match(header_pattern, line.strip(), re.IGNORECASE)
        if match or _is_section_header(line):
            if current_section:
                sections.append((current_section, '\n'.join(current_content)))
            current_section = _normalize_section_name(match.group(1) if match else line)
            current_content = []
        else:
            current_content.append(line)
    
    # Add last section
    if current_section:
        sections.append((current_section, '\n'.join(current_content)))
    elif current_content:
        sections.append(('unknown', '\n'.join(current_content)))
    
    return sections


def _is_section_header(line: str) -> bool:
    """
    Heuristic to detect if a line is likely a section header.
    """
    line = line.strip()
    if not line:
        return False
    
    # All caps and short
    if line.isupper() and len(line) < 30:
        return True
    
    # Ends with colon
    if line.endswith(':') and len(line) < 40:
        return True
    
    # Contains underlines or dashes as decorations
    if re.match(r'^[_\-=]{3,}', line) or re.match(r'^.{3,20}[_\-=]{3,}$', line):
        return True
    
    return False


def _normalize_section_name(name: str) -> str:
    """
    Normalize section name to standard form.
    """
    name = name.lower().strip().rstrip(':')
    
    mappings = {
        'work experience': 'experience',
        'professional experience': 'experience',
        'employment': 'experience',
        'employment history': 'experience',
        'career history': 'experience',
        'technical skills': 'skills',
        'core competencies': 'skills',
        'technologies': 'skills',
        'tech stack': 'skills',
        'academic': 'education',
        'academics': 'education',
        'qualifications': 'education',
        'personal projects': 'projects',
        'academic projects': 'projects',
        'side projects': 'projects',
        'professional summary': 'summary',
        'objective': 'summary',
        'profile': 'summary',
        'about me': 'summary',
        'certifications': 'certifications',
        'certificates': 'certifications',
        'licenses': 'certifications',
        'honors': 'awards',
        'achievements': 'awards',
        'accomplishments': 'awards',
    }
    
    return mappings.get(name, name)
