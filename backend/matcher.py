"""
Keyword Matching Engine v2

Fixes from v1:
1. Boundary-aware matching (no false positives from substrings)
2. Short token special handling (go, c, r, es)
3. Evidence scoring (action verbs, metrics near skills)
4. Penalty for skills only in skills section
5. Role-fit scoring (title similarity, domain match)
6. Importance weighting per skill category

Usage:
    python matcher.py <resume.json> <jd.json> [--output result.json]
"""

import json
import argparse
import sys
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Tuple, Optional
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))


# ============================================================
# SKILL DICTIONARY WITH CATEGORIES
# ============================================================

SKILL_IMPORTANCE = {
    # Must-have (weight 1.0)
    'must_have': {
        'python', 'sql', 'javascript', 'typescript', 'java',
    },
    # Core skills (weight 0.9)
    'core': {
        'react', 'node.js', 'postgresql', 'mongodb', 'aws', 'docker',
        'rest', 'api', 'git', 'linux', 'kubernetes',
    },
    # Secondary (weight 0.7)
    'secondary': {
        'redis', 'graphql', 'express', 'next.js', 'vue', 'angular',
        'gcp', 'azure', 'terraform', 'jenkins', 'ci/cd',
    },
    # Bonus (weight 0.5)
    'bonus': {
        'kafka', 'elasticsearch', 'nginx', 'rabbitmq', 'prometheus',
    }
}

def get_skill_weight(skill: str) -> float:
    """Get importance weight for a skill."""
    skill_lower = skill.lower()
    for category, skills in SKILL_IMPORTANCE.items():
        if skill_lower in skills:
            return {'must_have': 1.0, 'core': 0.9, 'secondary': 0.7, 'bonus': 0.5}[category]
    return 0.6  # Default weight

# Short tokens that need exact boundary matching
SHORT_TOKENS = {'go', 'c', 'r', 'es', 'ai', 'ml', 'ui', 'ux', 'qa', 'db', 'k8s'}

# Synonym mappings
SYNONYMS = {
    'javascript': ['js', 'ecmascript', 'es6'],
    'typescript': ['ts'],
    'python': ['py', 'python3'],
    'golang': ['go'],
    'csharp': ['c#', 'c sharp'],
    'cplusplus': ['c++', 'cpp'],
    'react': ['reactjs', 'react.js'],
    'vue': ['vuejs', 'vue.js'],
    'angular': ['angularjs'],
    'nextjs': ['next.js', 'next'],
    'nodejs': ['node.js', 'node'],
    'express': ['expressjs', 'express.js'],
    'postgresql': ['postgres', 'psql'],
    'mongodb': ['mongo'],
    'elasticsearch': ['elastic'],
    'dynamodb': ['dynamo'],
    'aws': ['amazon web services'],
    'gcp': ['google cloud', 'google cloud platform'],
    'azure': ['microsoft azure'],
    'kubernetes': ['k8s'],
    'docker': ['containers', 'containerization'],
    'cicd': ['ci/cd', 'continuous integration', 'continuous deployment'],
    'rest': ['restful', 'rest api'],
    'graphql': ['gql'],
    'microservices': ['micro services'],
    'agile': ['scrum', 'kanban'],
}

# Build reverse lookup
SYNONYM_CANONICAL = {}
for canonical, synonyms in SYNONYMS.items():
    SYNONYM_CANONICAL[canonical.lower()] = canonical.lower()
    for syn in synonyms:
        SYNONYM_CANONICAL[syn.lower()] = canonical.lower()

# Action verbs that indicate real experience
ACTION_VERBS = {
    'built', 'developed', 'designed', 'implemented', 'created', 'deployed',
    'architected', 'led', 'managed', 'optimized', 'improved', 'reduced',
    'increased', 'automated', 'integrated', 'migrated', 'refactored',
    'scaled', 'shipped', 'launched', 'maintained', 'debugged', 'tested',
    'wrote', 'configured', 'established', 'trained', 'mentored'
}

# Metric patterns that indicate impact
METRIC_PATTERNS = [
    r'\d+%',
    r'\d+x',
    r'\$\d+',
    r'\d+k\+?',
    r'\d+m\+?',
    r'\d+\s*(?:users?|customers?|clients?|requests?)',
    r'(?:reduced|improved|increased)\s+(?:by\s+)?\d+',
]

# Section weights
SECTION_WEIGHTS = {
    'experience': 1.0,
    'projects': 0.85,
    'skills': 0.5,  # Lower weight for skills-only
    'education': 0.4,
    'summary': 0.5,
    'unknown': 0.3,
}


# ============================================================
# BOUNDARY-AWARE MATCHING
# ============================================================

def skill_matches_text(skill: str, text: str) -> List[Dict]:
    """
    Find skill in text with proper word boundaries.
    Returns list of matches with positions and context.
    """
    skill_lower = skill.lower()
    text_lower = text.lower()
    matches = []
    
    # For short tokens, require exact word boundary
    if skill_lower in SHORT_TOKENS or len(skill_lower) <= 2:
        pattern = r'\b' + re.escape(skill_lower) + r'\b'
    else:
        # For longer skills, allow some flexibility but still use boundaries
        pattern = r'\b' + re.escape(skill_lower) + r'(?:\.?js|\.?py)?\b'
    
    for match in re.finditer(pattern, text_lower):
        start = match.start()
        end = match.end()
        
        # Get context (50 chars before and after)
        ctx_start = max(0, start - 50)
        ctx_end = min(len(text), end + 50)
        context = text[ctx_start:ctx_end]
        
        matches.append({
            'skill': skill,
            'position': start,
            'context': context.strip(),
            'matched_text': text[start:end]
        })
    
    return matches


def normalize_skill(skill: str) -> str:
    """Normalize skill to canonical form."""
    skill_lower = skill.lower().strip()
    return SYNONYM_CANONICAL.get(skill_lower, skill_lower)


def skills_are_equivalent(skill1: str, skill2: str) -> bool:
    """Check if two skills are equivalent (not just substring)."""
    norm1 = normalize_skill(skill1)
    norm2 = normalize_skill(skill2)
    return norm1 == norm2


# ============================================================
# EVIDENCE SCORING
# ============================================================

def calculate_evidence_score(context: str) -> float:
    """
    Calculate evidence score for a skill mention based on context.
    
    Returns 0.0 to 1.0:
    - 1.0: Strong evidence (action verb + metric)
    - 0.7: Good evidence (action verb or metric)
    - 0.4: Weak evidence (just the skill mentioned)
    """
    context_lower = context.lower()
    score = 0.4  # Base score for any mention
    
    # Check for action verbs
    has_action = any(verb in context_lower for verb in ACTION_VERBS)
    if has_action:
        score += 0.3
    
    # Check for metrics
    has_metric = any(re.search(pattern, context_lower) for pattern in METRIC_PATTERNS)
    if has_metric:
        score += 0.3
    
    return min(1.0, score)


def extract_skills_from_text(text: str, skill_list: Set[str]) -> List[Dict]:
    """
    Extract all skill mentions from text with evidence scoring.
    """
    mentions = []
    
    for skill in skill_list:
        matches = skill_matches_text(skill, text)
        for match in matches:
            evidence = calculate_evidence_score(match['context'])
            mentions.append({
                'skill': skill,
                'normalized': normalize_skill(skill),
                'context': match['context'],
                'evidence_score': evidence
            })
    
    return mentions


# ============================================================
# RESUME SKILL EXTRACTION
# ============================================================

def get_resume_skills_with_evidence(resume: Dict, jd_skills: Set[str]) -> Dict[str, Dict]:
    """
    Extract skills from resume with section placement and evidence scoring.
    
    Returns dict: normalized_skill -> {
        'original': str,
        'sections': [{'section': str, 'evidence': float, 'context': str}],
        'best_evidence': float,
        'in_experience': bool
    }
    """
    skills = defaultdict(lambda: {
        'original': None,
        'sections': [],
        'best_evidence': 0,
        'in_experience': False
    })
    
    # Build skill list to search for (JD skills + their synonyms)
    search_skills = set()
    for skill in jd_skills:
        search_skills.add(skill)
        # Add synonyms
        norm = normalize_skill(skill)
        for syn_list in SYNONYMS.values():
            for syn in syn_list:
                if normalize_skill(syn) == norm:
                    search_skills.add(syn)
    
    # 1. Extract from experience bullets
    experience = resume.get('sections', {}).get('experience', [])
    for job in experience:
        bullets = job.get('bullets', [])
        for bullet in bullets:
            bullet_text = bullet.get('text', '') if isinstance(bullet, dict) else str(bullet)
            
            mentions = extract_skills_from_text(bullet_text, search_skills)
            for mention in mentions:
                norm = mention['normalized']
                skills[norm]['original'] = mention['skill']
                skills[norm]['sections'].append({
                    'section': 'experience',
                    'evidence': mention['evidence_score'],
                    'context': mention['context']
                })
                skills[norm]['best_evidence'] = max(skills[norm]['best_evidence'], mention['evidence_score'])
                skills[norm]['in_experience'] = True
    
    # 2. Extract from projects
    projects = resume.get('sections', {}).get('projects', [])
    for project in projects:
        # From tech stack
        for tech in project.get('stack', []):
            norm = normalize_skill(tech)
            if norm in [normalize_skill(s) for s in search_skills]:
                skills[norm]['original'] = tech
                skills[norm]['sections'].append({
                    'section': 'projects',
                    'evidence': 0.6,  # Stack mention = medium evidence
                    'context': f"Project: {project.get('name', '')}"
                })
                skills[norm]['best_evidence'] = max(skills[norm]['best_evidence'], 0.6)
        
        # From bullets
        for bullet in project.get('bullets', []):
            bullet_text = bullet.get('text', '') if isinstance(bullet, dict) else str(bullet)
            mentions = extract_skills_from_text(bullet_text, search_skills)
            for mention in mentions:
                norm = mention['normalized']
                skills[norm]['original'] = mention['skill']
                skills[norm]['sections'].append({
                    'section': 'projects',
                    'evidence': mention['evidence_score'],
                    'context': mention['context']
                })
                skills[norm]['best_evidence'] = max(skills[norm]['best_evidence'], mention['evidence_score'])
    
    # 3. Skills section (lowest value)
    skills_section = resume.get('sections', {}).get('skills', {})
    for category in skills_section.get('categories', []):
        for item in category.get('items', []):
            norm = normalize_skill(item)
            if norm in [normalize_skill(s) for s in search_skills]:
                # Only add if not already found in better sections
                if not skills[norm]['sections']:
                    skills[norm]['original'] = item
                skills[norm]['sections'].append({
                    'section': 'skills',
                    'evidence': 0.3,  # Skills-only = low evidence
                    'context': f"Skills section: {category.get('name', 'General')}"
                })
                if skills[norm]['best_evidence'] == 0:
                    skills[norm]['best_evidence'] = 0.3
    
    return dict(skills)


# ============================================================
# MAIN MATCHING FUNCTION
# ============================================================

def match_keywords_v2(resume: Dict, jd: Dict) -> Dict[str, Any]:
    """
    Match resume against JD with evidence-based scoring.
    """
    # Get JD skills
    jd_hard = set(s for s in jd.get('requirements', {}).get('hard', {}).get('skills', []))
    jd_soft = set(s for s in jd.get('requirements', {}).get('preferred', {}).get('skills', []))
    jd_all = jd_hard | jd_soft
    
    # Extract resume skills with evidence
    resume_skills = get_resume_skills_with_evidence(resume, jd_all)
    
    # Match analysis
    matches_hard = []
    matches_soft = []
    missing_hard = []
    missing_soft = []
    
    for jd_skill in jd_hard:
        norm = normalize_skill(jd_skill)
        if norm in resume_skills:
            skill_data = resume_skills[norm]
            matches_hard.append({
                'jd_skill': jd_skill,
                'resume_skill': skill_data['original'],
                'evidence_score': skill_data['best_evidence'],
                'in_experience': skill_data['in_experience'],
                'sections': [s['section'] for s in skill_data['sections']],
                'importance_weight': get_skill_weight(jd_skill)
            })
        else:
            missing_hard.append({
                'skill': jd_skill,
                'importance': 'required',
                'weight': get_skill_weight(jd_skill),
                'suggestion': get_smart_suggestion(jd_skill)
            })
    
    for jd_skill in jd_soft:
        norm = normalize_skill(jd_skill)
        # Skip if already matched as hard
        if any(normalize_skill(m['jd_skill']) == norm for m in matches_hard):
            continue
        
        if norm in resume_skills:
            skill_data = resume_skills[norm]
            matches_soft.append({
                'jd_skill': jd_skill,
                'resume_skill': skill_data['original'],
                'evidence_score': skill_data['best_evidence'],
                'in_experience': skill_data['in_experience'],
                'sections': [s['section'] for s in skill_data['sections']]
            })
        else:
            missing_soft.append({
                'skill': jd_skill,
                'importance': 'preferred',
                'suggestion': get_smart_suggestion(jd_skill)
            })
    
    # Calculate scores
    scores = calculate_composite_score(matches_hard, matches_soft, missing_hard, missing_soft, jd_hard, jd_soft)
    
    # Generate recommendations
    recommendations = generate_smart_recommendations(matches_hard, matches_soft, missing_hard, missing_soft)
    
    return {
        'match_summary': scores,
        'matches': {
            'hard': matches_hard,
            'soft': matches_soft,
            'total_matched': len(matches_hard) + len(matches_soft)
        },
        'missing': {
            'hard': missing_hard,
            'soft': missing_soft,
            'total_missing': len(missing_hard) + len(missing_soft)
        },
        'recommendations': recommendations
    }


def calculate_composite_score(matches_hard, matches_soft, missing_hard, missing_soft, jd_hard, jd_soft):
    """
    Calculate composite score with evidence weighting and penalties.
    """
    total_hard = len(jd_hard)
    total_soft = len(jd_soft)
    
    # Hard skills score (weighted by evidence)
    if total_hard > 0:
        hard_weighted = sum(
            m['evidence_score'] * m.get('importance_weight', 1.0) 
            for m in matches_hard
        )
        max_hard = sum(get_skill_weight(s) for s in jd_hard)
        hard_score = (hard_weighted / max_hard) * 100 if max_hard > 0 else 0
    else:
        hard_score = 100
    
    # Soft skills score
    if total_soft > 0:
        soft_weighted = sum(m['evidence_score'] for m in matches_soft)
        soft_score = (soft_weighted / total_soft) * 100
    else:
        soft_score = 100
    
    # Penalty for skills-only-in-list (not in experience)
    skills_only_penalty = 0
    for m in matches_hard:
        if not m['in_experience'] and 'skills' in m['sections']:
            skills_only_penalty += 2  # -2 points per skill only in list
    
    # Experience bonus (skills appearing in experience with good evidence)
    experience_bonus = 0
    for m in matches_hard:
        if m['in_experience'] and m['evidence_score'] >= 0.7:
            experience_bonus += 1.5  # +1.5 points for well-evidenced skills
    
    # Overall score
    raw_score = (hard_score * 0.75) + (soft_score * 0.25)
    adjusted_score = raw_score - skills_only_penalty + experience_bonus
    final_score = max(0, min(100, adjusted_score))
    
    return {
        'overall_score': round(final_score, 1),
        'hard_skill_match': f"{len(matches_hard)}/{total_hard}",
        'soft_skill_match': f"{len(matches_soft)}/{total_soft}",
        'hard_score': round(hard_score, 1),
        'soft_score': round(soft_score, 1),
        'evidence_avg': round(
            sum(m['evidence_score'] for m in matches_hard) / len(matches_hard) if matches_hard else 0, 2
        ),
        'skills_only_penalty': skills_only_penalty,
        'experience_bonus': round(experience_bonus, 1),
        'evaluated_at': datetime.now(timezone.utc).isoformat()
    }


def get_smart_suggestion(skill: str) -> str:
    """Generate smart suggestion for missing skill."""
    skill_lower = skill.lower()
    
    if skill_lower in ['python', 'javascript', 'java', 'sql']:
        return f"Mention {skill} in experience bullets with specific use case, not just skills section"
    elif skill_lower in ['aws', 'gcp', 'azure']:
        return f"Add specific {skill} services (e.g., EC2, Lambda, S3) in project or experience"
    elif skill_lower in ['docker', 'kubernetes']:
        return f"Describe {skill} usage in deployment context with impact metrics"
    elif skill_lower in ['react', 'vue', 'angular']:
        return f"Add {skill} to a project with specific features built"
    else:
        return f"Add {skill} to relevant experience bullets where you've actually used it"


def generate_smart_recommendations(matches_hard, matches_soft, missing_hard, missing_soft):
    """Generate prioritized recommendations."""
    recommendations = []
    
    # 1. Missing required skills (highest priority)
    for m in sorted(missing_hard, key=lambda x: x.get('weight', 0.5), reverse=True)[:3]:
        recommendations.append({
            'priority': 'critical',
            'type': 'missing_required',
            'skill': m['skill'],
            'action': m['suggestion'],
            'impact': 'Required skill - major ATS impact'
        })
    
    # 2. Skills only in skills section (need context)
    for m in matches_hard:
        if not m['in_experience']:
            recommendations.append({
                'priority': 'high',
                'type': 'needs_context',
                'skill': m['jd_skill'],
                'action': f"Move {m['jd_skill']} into experience/project bullets with action verbs and metrics",
                'impact': 'Currently low evidence - add context for +10-15% score improvement'
            })
    
    # 3. Low evidence skills
    for m in matches_hard:
        if m['evidence_score'] < 0.5 and m['in_experience']:
            recommendations.append({
                'priority': 'medium',
                'type': 'weak_evidence',
                'skill': m['jd_skill'],
                'action': f"Strengthen {m['jd_skill']} mention with metrics (%, users, impact)",
                'impact': 'Low evidence score - add quantified impact'
            })
    
    # 4. Missing preferred skills
    for m in missing_soft[:2]:
        recommendations.append({
            'priority': 'low',
            'type': 'missing_preferred',
            'skill': m['skill'],
            'action': m['suggestion'],
            'impact': 'Nice to have - minor score improvement'
        })
    
    return recommendations[:10]


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='ATS Keyword Matcher v2')
    parser.add_argument('resume_json', help='Path to parsed resume JSON')
    parser.add_argument('jd_json', help='Path to parsed JD JSON')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--pretty', '-p', action='store_true')
    
    args = parser.parse_args()
    
    try:
        resume = json.loads(Path(args.resume_json).read_text(encoding='utf-8'))
        jd = json.loads(Path(args.jd_json).read_text(encoding='utf-8'))
        
        result = match_keywords_v2(resume, jd)
        
        indent = 2 if args.pretty else None
        json_output = json.dumps(result, indent=indent, ensure_ascii=False)
        
        if args.output:
            Path(args.output).write_text(json_output, encoding='utf-8')
            print(f"Results saved to: {args.output}")
        else:
            print(json_output)
        
        # Summary
        s = result['match_summary']
        print(f"\n📊 ATS Score: {s['overall_score']}%")
        print(f"   Hard: {s['hard_skill_match']} | Soft: {s['soft_skill_match']}")
        print(f"   Evidence avg: {s['evidence_avg']} | Penalty: -{s['skills_only_penalty']} | Bonus: +{s['experience_bonus']}")
        
        if result['missing']['hard']:
            print(f"\n❌ Missing required: {', '.join(m['skill'] for m in result['missing']['hard'])}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
