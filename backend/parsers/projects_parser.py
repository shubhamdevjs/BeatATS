"""Projects section parsing from resumes."""
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.skills_parser import extract_skills_from_text
from utils.text_utils import extract_metrics


def parse_projects(section_text: str) -> List[Dict[str, Any]]:
    """
    Parse projects section into structured entries.
    
    Args:
        section_text: Text from projects section
        
    Returns:
        List of project dicts
    """
    if not section_text:
        return []
    
    projects = []
    blocks = _split_project_blocks(section_text)
    
    for block in blocks:
        project = _parse_project_block(block)
        if project:
            projects.append(project)
    
    return projects


def _split_project_blocks(text: str) -> List[str]:
    """Split projects section into individual project blocks."""
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
        
        # Check if this looks like a new project entry
        if current_block and _looks_like_project_header(stripped):
            blocks.append('\n'.join(current_block))
            current_block = [line]
        else:
            current_block.append(line)
    
    if current_block:
        blocks.append('\n'.join(current_block))
    
    return blocks


def _looks_like_project_header(line: str) -> bool:
    """Check if line looks like start of a new project."""
    line = line.strip()
    
    # Starts with a bullet but short (project name)
    if re.match(r'^[\•\-\*]\s*.+$', line) and len(line) < 60:
        return True
    
    # Contains pipe or dash separator (common in "Project Name | Tech Stack")
    if re.search(r'\s+[\|\-–—]\s+', line) and len(line) < 80:
        return True
    
    # Contains parentheses at end (common in "Project Name (React, Node.js)")
    if re.search(r'\([A-Za-z,\s]+\)\s*$', line):
        return True
    
    # Has link indicator
    if 'github.com' in line.lower() or 'http' in line.lower():
        return True
    
    # Relatively short and starts with capital (potential project name)
    words = line.split()
    if len(words) <= 6 and words and words[0][0].isupper():
        return True
    
    return False


def _parse_project_block(block: str) -> Optional[Dict[str, Any]]:
    """Parse a single project block."""
    lines = [l.strip() for l in block.split('\n') if l.strip()]
    
    if not lines:
        return None
    
    project = {
        'name': None,
        'description': None,
        'stack': [],
        'url': None,
        'bullets': [],
        'dates': None
    }
    
    # First line typically contains project name
    header = lines[0]
    header = re.sub(r'^[\•\-\*]\s*', '', header)  # Remove bullet
    
    # Extract URL if present
    url_match = re.search(r'(https?://[^\s]+)', header)
    if url_match:
        project['url'] = url_match.group(1)
        header = header.replace(url_match.group(1), '').strip()
    
    # Look for URL in other lines too
    for line in lines[1:]:
        url_match = re.search(r'(https?://(?:github\.com|gitlab\.com)[^\s]+)', line)
        if url_match and not project['url']:
            project['url'] = url_match.group(1)
    
    # Extract tech stack from parentheses or after separator
    stack_match = re.search(r'\(([A-Za-z,\s\-\.]+)\)\s*$', header)
    if stack_match:
        stack_str = stack_match.group(1)
        project['stack'] = [s.strip() for s in stack_str.split(',') if s.strip()]
        header = header[:stack_match.start()].strip()
    else:
        # Check for separator pattern
        sep_match = re.search(r'\s*[\|\-–—]\s*(.+)$', header)
        if sep_match:
            stack_str = sep_match.group(1)
            project['stack'] = [s.strip() for s in stack_str.split(',') if s.strip()]
            header = header[:sep_match.start()].strip()
    
    # Clean up the name
    project['name'] = header.strip(' -|')
    
    if not project['name']:
        return None
    
    # Parse remaining lines as bullets/description
    all_skills = set(project['stack'])
    
    for line in lines[1:]:
        text = line.strip()
        text = re.sub(r'^[\•\-\*]\s*', '', text)  # Remove bullets
        text = re.sub(r'^\d+\.\s*', '', text)  # Remove numbers
        
        if not text or len(text) < 10:
            continue
        
        # Skip if it's just a URL
        if text.startswith('http'):
            continue
        
        skills_found = extract_skills_from_text(text)
        all_skills.update(skills_found)
        
        project['bullets'].append({
            'text': text,
            'skills_found': skills_found,
            'metrics': extract_metrics(text)
        })
    
    # Update stack with all found skills
    project['stack'] = list(all_skills)
    
    return project


def parse_awards(section_text: str) -> List[Dict[str, Any]]:
    """
    Parse awards/achievements section.
    
    Args:
        section_text: Text from awards section
        
    Returns:
        List of award dicts
    """
    if not section_text:
        return []
    
    awards = []
    lines = section_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove bullet markers
        line = re.sub(r'^[\•\-\*]\s*', '', line)
        
        if len(line) < 5:
            continue
        
        award = {
            'title': line,
            'raw': line,
            'date': None,
            'issuer': None
        }
        
        # Try to extract date
        date_match = re.search(r'((?:19|20)\d{2})', line)
        if date_match:
            award['date'] = date_match.group(1)
        
        # Try to extract issuer (often after " - " or "by")
        issuer_match = re.search(r'(?:[-–—]|by)\s+([A-Z][A-Za-z\s]+)$', line)
        if issuer_match:
            award['issuer'] = issuer_match.group(1).strip()
        
        awards.append(award)
    
    return awards
