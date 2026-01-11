"""Section detection and splitting for resumes."""
import re
from typing import Dict, List, Tuple, Optional


# Standard section names to normalize to
STANDARD_SECTIONS = [
    'summary', 'experience', 'education', 'skills', 
    'projects', 'certifications', 'awards', 'publications',
    'volunteer', 'languages', 'interests'
]

# Mapping of common variations to standard names
SECTION_ALIASES = {
    # Experience variations
    'work experience': 'experience',
    'professional experience': 'experience',
    'employment': 'experience',
    'employment history': 'experience',
    'work history': 'experience',
    'career history': 'experience',
    'relevant experience': 'experience',
    
    # Skills variations
    'technical skills': 'skills',
    'core competencies': 'skills',
    'technologies': 'skills',
    'tech stack': 'skills',
    'competencies': 'skills',
    'areas of expertise': 'skills',
    'expertise': 'skills',
    'proficiencies': 'skills',
    
    # Education variations
    'academic background': 'education',
    'academics': 'education',
    'academic': 'education',
    'qualifications': 'education',
    'educational background': 'education',
    
    # Summary variations
    'professional summary': 'summary',
    'career summary': 'summary',
    'executive summary': 'summary',
    'objective': 'summary',
    'career objective': 'summary',
    'profile': 'summary',
    'about me': 'summary',
    'about': 'summary',
    
    # Projects variations
    'personal projects': 'projects',
    'academic projects': 'projects',
    'side projects': 'projects',
    'key projects': 'projects',
    'portfolio': 'projects',
    
    # Certifications variations
    'certificates': 'certifications',
    'licenses': 'certifications',
    'licenses & certifications': 'certifications',
    'professional certifications': 'certifications',
    
    # Awards variations
    'honors': 'awards',
    'achievements': 'awards',
    'accomplishments': 'awards',
    'honors & awards': 'awards',
    'recognition': 'awards',
    
    # Other
    'publications & research': 'publications',
    'research': 'publications',
    'volunteering': 'volunteer',
    'community involvement': 'volunteer',
    'extracurricular': 'volunteer',
    'hobbies': 'interests',
    'hobbies & interests': 'interests',
}


def detect_sections(text: str) -> Dict[str, Dict]:
    """
    Detect and extract sections from resume text.
    
    Args:
        text: Full resume text
        
    Returns:
        Dict mapping section names to their content and metadata
    """
    lines = text.split('\n')
    sections = {}
    current_section = None
    current_content = []
    current_start_line = 0
    
    # First pass: identify section headers
    for i, line in enumerate(lines):
        header_name = _detect_header(line)
        
        if header_name:
            # Save previous section
            if current_section:
                sections[current_section] = {
                    'content': '\n'.join(current_content),
                    'start_line': current_start_line,
                    'end_line': i - 1,
                    'raw_header': lines[current_start_line - 1] if current_start_line > 0 else ''
                }
            
            current_section = header_name
            current_content = []
            current_start_line = i + 1
        elif current_section:
            current_content.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = {
            'content': '\n'.join(current_content),
            'start_line': current_start_line,
            'end_line': len(lines) - 1,
            'raw_header': lines[current_start_line - 1] if current_start_line > 0 else ''
        }
    
    # If no sections detected, treat everything as unknown
    if not sections:
        sections['_raw'] = {
            'content': text,
            'start_line': 0,
            'end_line': len(lines) - 1,
            'raw_header': ''
        }
    
    return sections


def _detect_header(line: str) -> Optional[str]:
    """
    Detect if a line is a section header.
    
    Args:
        line: Single line from resume
        
    Returns:
        Normalized section name or None
    """
    original_line = line
    line = line.strip()
    
    if not line or len(line) < 3:
        return None
    
    # Skip lines that are clearly content (too long)
    if len(line) > 50:
        return None
    
    # Remove common decorations
    line = re.sub(r'^[_\-=\*\#]+\s*', '', line)
    line = re.sub(r'\s*[_\-=\*\#]+$', '', line)
    line = line.strip(':').strip()
    
    if not line:
        return None
    
    line_lower = line.lower()
    
    # Direct match with standard sections
    if line_lower in STANDARD_SECTIONS:
        return line_lower
    
    # Check aliases
    if line_lower in SECTION_ALIASES:
        return SECTION_ALIASES[line_lower]
    
    # Check for partial matches
    for alias, standard in SECTION_ALIASES.items():
        if alias in line_lower or line_lower in alias:
            return standard
    
    # Heuristic: ALL CAPS and short (likely header)
    if line.isupper() and len(line) < 30:
        # Check if any keywords match
        for alias, standard in SECTION_ALIASES.items():
            if any(word in line_lower for word in alias.split()):
                return standard
    
    return None


def get_section_content(sections: Dict, section_name: str) -> Optional[str]:
    """
    Get content of a specific section.
    
    Args:
        sections: Dict from detect_sections
        section_name: Standard section name
        
    Returns:
        Section content or None
    """
    if section_name in sections:
        return sections[section_name].get('content')
    return None


def get_header_portion(text: str, max_lines: int = 15) -> str:
    """
    Get the header portion of the resume (before first section).
    This typically contains contact info and sometimes summary.
    
    Args:
        text: Full resume text
        max_lines: Maximum lines to consider as header
        
    Returns:
        Header portion text
    """
    lines = text.split('\n')
    header_lines = []
    
    for i, line in enumerate(lines[:max_lines]):
        if _detect_header(line):
            break
        header_lines.append(line)
    
    return '\n'.join(header_lines)
