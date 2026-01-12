"""Skill extraction from job descriptions."""
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import shared skills dictionary from resume parser
from parsers.skills_parser import ALL_SKILLS, SKILL_TO_CATEGORY, SKILL_CATEGORIES


def extract_jd_skills(text: str, sections: Dict = None) -> Dict[str, Any]:
    """
    Extract and classify skills from JD text.
    
    Args:
        text: Full JD text or section content
        sections: Optional parsed sections dict
        
    Returns:
        Dict with hard_skills, soft_skills, all_skills, and mentions
    """
    hard_skills = set()
    soft_skills = set()
    mentions = []
    
    text_lower = text.lower()
    
    # Extract all known skills
    for skill in ALL_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        for match in re.finditer(pattern, text_lower):
            # Get context
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            context = text[start:end]
            
            # Determine if hard or soft based on context
            is_hard = _is_hard_requirement(context)
            
            normalized = _normalize_skill(skill)
            
            if is_hard:
                hard_skills.add(normalized)
            else:
                soft_skills.add(normalized)
            
            mentions.append({
                'skill': normalized,
                'context': ' '.join(context.split()),
                'is_hard': is_hard
            })
    
    # If sections provided, use section classification
    if sections:
        for section_name, section_data in sections.items():
            section_text = section_data.get('content', '')
            is_section_hard = section_data.get('is_hard_requirement', True)
            
            for skill in ALL_SKILLS:
                if _skill_in_text(skill, section_text.lower()):
                    normalized = _normalize_skill(skill)
                    if is_section_hard:
                        hard_skills.add(normalized)
                    else:
                        soft_skills.add(normalized)
    
    # Categorize skills
    categorized = _categorize_skills(hard_skills | soft_skills)
    
    return {
        'hard': list(hard_skills),
        'soft': list(soft_skills),
        'all': list(hard_skills | soft_skills),
        'categories': categorized,
        'mentions': mentions
    }


def _is_hard_requirement(context: str) -> bool:
    """Determine if context suggests a hard requirement."""
    context_lower = context.lower()
    
    hard_signals = ['required', 'must', 'need', 'essential', 'mandatory', 'minimum']
    soft_signals = ['preferred', 'nice to have', 'bonus', 'plus', 'ideal']
    
    for signal in soft_signals:
        if signal in context_lower:
            return False
    
    for signal in hard_signals:
        if signal in context_lower:
            return True
    
    # Default to hard if no signal found
    return True


def _skill_in_text(skill: str, text: str) -> bool:
    """Check if skill appears in text as a word."""
    pattern = r'\b' + re.escape(skill) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _normalize_skill(skill: str) -> str:
    """Normalize skill name to proper case."""
    special_cases = {
        'aws': 'AWS', 'gcp': 'GCP', 'sql': 'SQL', 'html': 'HTML',
        'css': 'CSS', 'javascript': 'JavaScript', 'typescript': 'TypeScript',
        'node.js': 'Node.js', 'react': 'React', 'vue.js': 'Vue.js',
        'mongodb': 'MongoDB', 'postgresql': 'PostgreSQL', 'mysql': 'MySQL',
        'docker': 'Docker', 'kubernetes': 'Kubernetes', 'python': 'Python',
        'java': 'Java', 'c++': 'C++', 'golang': 'Go', 'rest': 'REST',
        'graphql': 'GraphQL', 'ci/cd': 'CI/CD', 'nosql': 'NoSQL',
    }
    return special_cases.get(skill.lower(), skill)


def _categorize_skills(skills: Set[str]) -> List[Dict]:
    """Organize skills into categories."""
    categorized = {}
    
    for skill in skills:
        skill_lower = skill.lower()
        category = SKILL_TO_CATEGORY.get(skill_lower, 'Other')
        
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(skill)
    
    return [{'name': k, 'items': v} for k, v in categorized.items()]


def extract_responsibilities(sections: Dict) -> List[str]:
    """Extract responsibility statements from parsed sections."""
    responsibilities = []
    
    resp_section = sections.get('responsibilities', {})
    items = resp_section.get('items', [])
    
    if items:
        responsibilities.extend(items)
    
    # Also check requirements section for action-oriented items
    req_section = sections.get('requirements', {})
    for item in req_section.get('items', []):
        # Responsibility typically starts with action verb
        if _starts_with_action_verb(item):
            responsibilities.append(item)
    
    return responsibilities


def _starts_with_action_verb(text: str) -> bool:
    """Check if text starts with an action verb (responsibility pattern)."""
    action_verbs = [
        'develop', 'design', 'build', 'create', 'implement', 'maintain',
        'manage', 'lead', 'collaborate', 'work', 'write', 'test', 'deploy',
        'optimize', 'architect', 'analyze', 'troubleshoot', 'support',
        'ensure', 'drive', 'deliver', 'coordinate', 'mentor', 'review'
    ]
    
    first_word = text.split()[0].lower() if text.split() else ''
    return first_word in action_verbs
