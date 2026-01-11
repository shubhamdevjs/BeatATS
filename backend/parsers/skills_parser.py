"""Skills extraction and categorization from resumes."""
import re
from typing import Dict, List, Any, Optional, Tuple


# Common skill categories with keywords
SKILL_CATEGORIES = {
    'Programming Languages': [
        'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'go', 'golang',
        'rust', 'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl',
        'shell', 'bash', 'powershell', 'sql', 'html', 'css', 'sass', 'less'
    ],
    'Frontend': [
        'react', 'reactjs', 'react.js', 'angular', 'vue', 'vuejs', 'vue.js',
        'next.js', 'nextjs', 'nuxt', 'svelte', 'jquery', 'bootstrap', 'tailwind',
        'material-ui', 'chakra', 'redux', 'mobx', 'webpack', 'vite', 'babel'
    ],
    'Backend': [
        'node.js', 'nodejs', 'express', 'expressjs', 'fastapi', 'flask', 'django',
        'spring', 'spring boot', 'springboot', '.net', 'asp.net', 'rails',
        'ruby on rails', 'laravel', 'fastify', 'nestjs', 'hapi', 'koa'
    ],
    'Databases': [
        'postgresql', 'postgres', 'mysql', 'mongodb', 'redis', 'elasticsearch',
        'dynamodb', 'cassandra', 'sqlite', 'oracle', 'sql server', 'mariadb',
        'neo4j', 'couchdb', 'firebase', 'firestore', 'supabase'
    ],
    'Cloud & DevOps': [
        'aws', 'amazon web services', 'azure', 'gcp', 'google cloud', 'docker',
        'kubernetes', 'k8s', 'terraform', 'ansible', 'jenkins', 'gitlab ci',
        'github actions', 'circleci', 'travis', 'helm', 'argo', 'prometheus',
        'grafana', 'datadog', 'new relic', 'splunk', 'cloudformation'
    ],
    'Data & ML': [
        'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn', 'pandas',
        'numpy', 'scipy', 'matplotlib', 'seaborn', 'jupyter', 'spark', 'pyspark',
        'hadoop', 'airflow', 'mlflow', 'kubeflow', 'sagemaker', 'databricks',
        'huggingface', 'transformers', 'opencv', 'nltk', 'spacy', 'gensim'
    ],
    'Tools & Other': [
        'git', 'github', 'gitlab', 'bitbucket', 'jira', 'confluence', 'slack',
        'postman', 'swagger', 'openapi', 'figma', 'sketch', 'adobe xd',
        'linux', 'unix', 'nginx', 'apache', 'vim', 'vscode', 'intellij',
        'agile', 'scrum', 'kanban', 'rest', 'restful', 'graphql', 'grpc',
        'microservices', 'serverless', 'oauth', 'jwt', 'ssl', 'ci/cd'
    ]
}

# Flatten for quick lookup
ALL_SKILLS = set()
SKILL_TO_CATEGORY = {}
for category, skills in SKILL_CATEGORIES.items():
    for skill in skills:
        ALL_SKILLS.add(skill.lower())
        SKILL_TO_CATEGORY[skill.lower()] = category


def parse_skills(section_text: str, full_text: str = None) -> Dict[str, Any]:
    """
    Parse and categorize skills from resume.
    
    Args:
        section_text: Text from skills section
        full_text: Optional full resume text for additional mentions
        
    Returns:
        Skills dict with categories, all skills, and mentions
    """
    # Extract skills from skills section
    section_skills = _extract_skills_from_section(section_text)
    
    # Build categories
    categories = _categorize_skills(section_skills)
    
    # Find all skill mentions in full text
    mentions = []
    if full_text:
        mentions = _find_skill_mentions(section_skills, full_text)
    
    return {
        'categories': categories,
        'all': list(section_skills),
        'mentions': mentions
    }


def _extract_skills_from_section(text: str) -> List[str]:
    """
    Extract individual skills from skills section text.
    Handles various formats: comma-separated, pipe-separated, bullet lists.
    """
    if not text:
        return []
    
    skills = set()
    
    # Try to detect category headers (e.g., "Languages: Python, Java")
    category_pattern = r'([A-Za-z\s&]+)\s*[:\|]\s*(.+?)(?=\n[A-Za-z\s&]+\s*[:\|]|\n\n|$)'
    category_matches = re.findall(category_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if category_matches:
        for _, skill_list in category_matches:
            extracted = _split_skill_list(skill_list)
            skills.update(extracted)
    else:
        # No categories, just extract skills
        extracted = _split_skill_list(text)
        skills.update(extracted)
    
    # Also extract known skills even if not explicitly listed
    text_lower = text.lower()
    for skill in ALL_SKILLS:
        if _skill_in_text(skill, text_lower):
            skills.add(_normalize_skill_name(skill))
    
    return list(skills)


def _split_skill_list(text: str) -> List[str]:
    """Split a skill list string into individual skills."""
    skills = []
    
    # Clean text
    text = text.strip()
    
    # Determine separator
    if ',' in text:
        parts = text.split(',')
    elif '|' in text:
        parts = text.split('|')
    elif '•' in text:
        parts = text.split('•')
    elif '\n' in text:
        parts = text.split('\n')
    else:
        parts = text.split()
    
    for part in parts:
        skill = part.strip()
        skill = re.sub(r'^[\-\*\•\◦]\s*', '', skill)  # Remove bullets
        skill = skill.strip()
        
        if skill and len(skill) < 50:  # Reasonable skill name length
            skills.append(skill)
    
    return skills


def _normalize_skill_name(skill: str) -> str:
    """Normalize skill name to proper case."""
    skill = skill.strip()
    
    # Special cases for acronyms/proper names
    special_cases = {
        'aws': 'AWS',
        'gcp': 'GCP',
        'ci/cd': 'CI/CD',
        'sql': 'SQL',
        'nosql': 'NoSQL',
        'html': 'HTML',
        'css': 'CSS',
        'rest': 'REST',
        'graphql': 'GraphQL',
        'javascript': 'JavaScript',
        'typescript': 'TypeScript',
        'node.js': 'Node.js',
        'react.js': 'React',
        'vue.js': 'Vue.js',
        'next.js': 'Next.js',
        'mongodb': 'MongoDB',
        'postgresql': 'PostgreSQL',
        'mysql': 'MySQL',
        'kubernetes': 'Kubernetes',
        'docker': 'Docker',
        'python': 'Python',
        'java': 'Java',
        'golang': 'Go',
    }
    
    skill_lower = skill.lower()
    if skill_lower in special_cases:
        return special_cases[skill_lower]
    
    return skill


def _skill_in_text(skill: str, text: str) -> bool:
    """Check if skill appears in text as a word."""
    pattern = r'\b' + re.escape(skill) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _categorize_skills(skills: List[str]) -> List[Dict[str, Any]]:
    """Organize skills into categories."""
    categorized = {}
    uncategorized = []
    
    for skill in skills:
        skill_lower = skill.lower()
        category = SKILL_TO_CATEGORY.get(skill_lower)
        
        if category:
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(_normalize_skill_name(skill))
        else:
            uncategorized.append(skill)
    
    # Build result list
    result = []
    for category_name, items in categorized.items():
        result.append({
            'name': category_name,
            'items': list(set(items))  # Deduplicate
        })
    
    if uncategorized:
        result.append({
            'name': 'Other',
            'items': list(set(uncategorized))
        })
    
    return result


def _find_skill_mentions(skills: List[str], text: str) -> List[Dict]:
    """Find mentions of skills throughout the resume."""
    mentions = []
    
    for skill in skills:
        pattern = r'\b' + re.escape(skill) + r'\b'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Get context
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            context = text[start:end]
            
            # Determine section (simplified)
            section = _guess_section(text[:match.start()])
            
            mentions.append({
                'term': skill,
                'where': section,
                'context': ' '.join(context.split()),
                'page': 1,
                'confidence': 0.9
            })
    
    return mentions


def _guess_section(text_before: str) -> str:
    """Guess which section a position is in based on preceding text."""
    text_lower = text_before.lower()
    
    # Check for section keywords (look backwards)
    last_500 = text_lower[-500:] if len(text_lower) > 500 else text_lower
    
    if 'experience' in last_500 or 'work' in last_500:
        return 'experience'
    elif 'project' in last_500:
        return 'projects'
    elif 'education' in last_500:
        return 'education'
    elif 'skill' in last_500:
        return 'skills'
    
    return 'unknown'


def extract_skills_from_text(text: str) -> List[str]:
    """
    Extract known skills from any text (e.g., bullet points).
    
    Args:
        text: Text to search for skills
        
    Returns:
        List of found skills
    """
    found = []
    text_lower = text.lower()
    
    for skill in ALL_SKILLS:
        if _skill_in_text(skill, text_lower):
            found.append(_normalize_skill_name(skill))
    
    return list(set(found))
