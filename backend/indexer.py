"""Term indexing and evidence collection for resume parsing."""
import re
from typing import Dict, List, Any, Set
from collections import defaultdict


def build_term_index(parsed_data: Dict[str, Any], raw_text: str) -> Dict[str, List[Dict]]:
    """
    Build an inverted index mapping terms to their locations.
    
    Args:
        parsed_data: Parsed resume data (sections, profile, etc.)
        raw_text: Raw resume text
        
    Returns:
        Dict mapping terms to list of occurrences
    """
    index = defaultdict(list)
    
    # Collect all terms to index
    terms_to_index = set()
    
    # Add skills
    skills_data = parsed_data.get('sections', {}).get('skills', {})
    terms_to_index.update(s.lower() for s in skills_data.get('all', []))
    
    # Add tech stack from projects
    for project in parsed_data.get('sections', {}).get('projects', []):
        terms_to_index.update(s.lower() for s in project.get('stack', []))
    
    # Add skills from experience bullets
    for exp in parsed_data.get('sections', {}).get('experience', []):
        terms_to_index.update(s.lower() for s in exp.get('skills_summary', []))
    
    # Index each term
    for term in terms_to_index:
        occurrences = _find_term_occurrences(term, parsed_data, raw_text)
        if occurrences:
            index[term] = occurrences
    
    return dict(index)


def _find_term_occurrences(term: str, parsed_data: Dict, raw_text: str) -> List[Dict]:
    """Find all occurrences of a term in the resume."""
    occurrences = []
    term_lower = term.lower()
    pattern = r'\b' + re.escape(term) + r'\b'
    
    # Search in skills section
    skills_text = parsed_data.get('sections', {}).get('skills', {})
    for mention in skills_text.get('mentions', []):
        if mention.get('term', '').lower() == term_lower:
            occurrences.append({
                'section': 'skills',
                'page': mention.get('page', 1),
                'snippet': mention.get('context', '')
            })
    
    # Search in experience
    for i, exp in enumerate(parsed_data.get('sections', {}).get('experience', [])):
        for bullet in exp.get('bullets', []):
            if term_lower in [s.lower() for s in bullet.get('skills_found', [])]:
                occurrences.append({
                    'section': 'experience',
                    'entity_id': f'exp_{i}',
                    'snippet': bullet.get('text', '')[:100]
                })
    
    # Search in projects
    for i, proj in enumerate(parsed_data.get('sections', {}).get('projects', [])):
        # Check stack
        if term_lower in [s.lower() for s in proj.get('stack', [])]:
            snippet = proj.get('name', '')
            if proj.get('bullets'):
                snippet += ' - ' + proj['bullets'][0].get('text', '')[:50]
            occurrences.append({
                'section': 'projects',
                'entity_id': f'proj_{i}',
                'snippet': snippet
            })
    
    # If no structured occurrences found, search raw text
    if not occurrences:
        for match in re.finditer(pattern, raw_text, re.IGNORECASE):
            start = max(0, match.start() - 30)
            end = min(len(raw_text), match.end() + 30)
            snippet = raw_text[start:end]
            occurrences.append({
                'section': 'unknown',
                'page': 1,
                'snippet': ' '.join(snippet.split())
            })
            if len(occurrences) >= 5:  # Limit occurrences
                break
    
    return occurrences


def collect_evidence(parsed_data: Dict[str, Any], raw_text: str) -> List[Dict]:
    """
    Collect evidence entries for all extracted fields.
    
    Args:
        parsed_data: Parsed resume data
        raw_text: Raw resume text
        
    Returns:
        List of evidence entries
    """
    evidence = []
    
    # Profile evidence
    profile = parsed_data.get('profile', {})
    
    if profile.get('name'):
        evidence.append(_create_evidence(
            'profile.name', profile['name'], raw_text, 0.9
        ))
    
    for i, email in enumerate(profile.get('emails', [])):
        evidence.append(_create_evidence(
            f'profile.emails[{i}]', email, raw_text, 0.99
        ))
    
    for i, phone in enumerate(profile.get('phones', [])):
        evidence.append(_create_evidence(
            f'profile.phones[{i}]', phone, raw_text, 0.95
        ))
    
    # Experience evidence
    for i, exp in enumerate(parsed_data.get('sections', {}).get('experience', [])):
        if exp.get('company'):
            evidence.append(_create_evidence(
                f'sections.experience[{i}].company', 
                exp['company'], raw_text, 0.85
            ))
        if exp.get('title'):
            evidence.append(_create_evidence(
                f'sections.experience[{i}].title',
                exp['title'], raw_text, 0.85
            ))
    
    # Education evidence
    for i, edu in enumerate(parsed_data.get('sections', {}).get('education', [])):
        if edu.get('school'):
            evidence.append(_create_evidence(
                f'sections.education[{i}].school',
                edu['school'], raw_text, 0.9
            ))
        if edu.get('degree'):
            evidence.append(_create_evidence(
                f'sections.education[{i}].degree',
                edu['degree'], raw_text, 0.85
            ))
    
    return evidence


def _create_evidence(field: str, value: str, text: str, confidence: float) -> Dict:
    """Create an evidence entry."""
    context = _find_context(value, text)
    
    return {
        'field': field,
        'value': value,
        'page': 1,
        'context': context,
        'confidence': confidence
    }


def _find_context(value: str, text: str, chars: int = 50) -> str:
    """Find surrounding context for a value."""
    idx = text.find(value)
    if idx == -1:
        # Try case-insensitive
        idx = text.lower().find(value.lower())
    
    if idx == -1:
        return value
    
    start = max(0, idx - chars)
    end = min(len(text), idx + len(value) + chars)
    
    context = text[start:end]
    return ' '.join(context.split())


def calculate_parse_quality(
    parsed_data: Dict[str, Any],
    signals: Dict[str, bool]
) -> Dict[str, Any]:
    """
    Calculate parse quality score and generate warnings.
    
    Args:
        parsed_data: Parsed resume data
        signals: Layout detection signals
        
    Returns:
        Parse quality dict with score, warnings, errors, signals
    """
    score = 1.0
    warnings = []
    errors = []
    
    profile = parsed_data.get('profile', {})
    sections = parsed_data.get('sections', {})
    
    # Check profile completeness
    if profile.get('name'):
        warnings.append('name_found')
    else:
        score -= 0.1
        errors.append('name_not_found')
    
    if profile.get('emails'):
        warnings.append('email_found')
    else:
        score -= 0.05
    
    if profile.get('phones'):
        warnings.append('phone_found')
    
    # Check sections
    if sections.get('experience'):
        warnings.append('experience_section_found')
        if len(sections['experience']) > 0:
            exp = sections['experience'][0]
            if not exp.get('bullets'):
                score -= 0.1
                warnings.append('experience_bullets_missing')
    else:
        score -= 0.15
        errors.append('experience_section_not_found')
    
    if sections.get('skills', {}).get('all'):
        warnings.append('skills_section_found')
    else:
        score -= 0.1
        warnings.append('skills_section_missing')
    
    if sections.get('education'):
        warnings.append('education_section_found')
    else:
        score -= 0.05
    
    # Check layout signals
    if signals.get('likely_two_column'):
        score -= 0.15
        warnings.append('two_column_layout_detected')
    
    if signals.get('contains_tables'):
        score -= 0.05
        warnings.append('tables_detected')
    
    if signals.get('low_text_density'):
        score -= 0.2
        errors.append('low_text_density')
    
    return {
        'score': round(max(0, min(1, score)), 2),
        'warnings': warnings,
        'errors': errors,
        'signals': signals
    }
