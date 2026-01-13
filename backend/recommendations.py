"""
Resume Improvement Recommendations Generator

Generates detailed, actionable recommendations for improving resume-to-JD match.
"""

from typing import Dict, List, Any


def generate_detailed_recommendations(resume: Dict, jd: Dict, match_result: Dict, knockout_result: Dict) -> Dict[str, Any]:
    """
    Generate comprehensive, user-friendly recommendations.
    
    Returns structured recommendations:
    - must_add: Skills/keywords to add (highest impact)
    - should_strengthen: Skills to move to experience with context
    - consider_adding: Nice-to-have skills
    - remove_or_reduce: Irrelevant content taking space
    - rewrite_suggestions: Specific bullet rewrites
    """
    recommendations = {
        'summary': '',
        'score_potential': 0,
        'path_to_100': [],  # NEW: Step-by-step guide to 100%
        'must_add': [],
        'should_strengthen': [],
        'consider_adding': [],
        'remove_or_reduce': [],
        'rewrite_suggestions': [],
        'quick_wins': [],
        'section_advice': {}
    }
    
    # Get data
    missing_hard = match_result.get('missing', {}).get('hard', [])
    missing_soft = match_result.get('missing', {}).get('soft', [])
    matched_hard = match_result.get('matches', {}).get('hard', [])
    current_score = match_result.get('match_summary', {}).get('overall_score', 0)
    evidence_avg = match_result.get('match_summary', {}).get('evidence_avg', 0)
    
    # JD skills and responsibilities
    jd_hard_skills = set(s.lower() for s in jd.get('requirements', {}).get('hard', {}).get('skills', []))
    jd_soft_skills = set(s.lower() for s in jd.get('requirements', {}).get('preferred', {}).get('skills', []))
    jd_responsibilities = jd.get('requirements', {}).get('hard', {}).get('responsibilities', [])
    
    # Resume skills
    resume_skills = set()
    for cat in resume.get('sections', {}).get('skills', {}).get('categories', []):
        resume_skills.update(s.lower() for s in cat.get('items', []))
    
    # 1. MUST ADD - Missing required skills
    for missing in missing_hard:
        skill = missing['skill']
        recommendations['must_add'].append({
            'skill': skill,
            'priority': 'CRITICAL',
            'impact': '+5-10% score',
            'how_to_add': _get_add_skill_guidance(skill, jd_responsibilities),
            'example': _get_skill_bullet_example(skill)
        })
    
    # 2. SHOULD STRENGTHEN - Skills only in skills section
    for match in matched_hard:
        if not match.get('in_experience', True) and 'skills' in match.get('sections', []):
            skill = match['jd_skill']
            recommendations['should_strengthen'].append({
                'skill': skill,
                'current_location': 'Skills section only',
                'problem': 'Low evidence score - ATS sees it as keyword stuffing',
                'action': f'Add {skill} to 2-3 experience bullets with action verbs and metrics',
                'impact': '+3-5% score',
                'example': _get_skill_bullet_example(skill)
            })
    
    # 3. CONSIDER ADDING - Nice to have skills
    for missing in missing_soft[:3]:
        skill = missing['skill']
        recommendations['consider_adding'].append({
            'skill': skill,
            'priority': 'LOW',
            'impact': '+1-2% score',
            'suggestion': f'Add {skill} if you have experience, otherwise skip'
        })
    
    # 4. QUICK WINS - Easy improvements
    recommendations['quick_wins'] = _get_quick_wins(resume, jd, match_result)
    
    # 5. REWRITE SUGGESTIONS - Bullet improvements
    recommendations['rewrite_suggestions'] = _get_rewrite_suggestions(resume, jd_hard_skills, jd_responsibilities)
    
    # 6. SECTION ADVICE
    recommendations['section_advice'] = _get_section_advice(resume, jd)
    
    # 7. PATH TO 100% - Clear numbered steps
    recommendations['path_to_100'] = _generate_path_to_100(
        current_score=current_score,
        evidence_avg=evidence_avg,
        missing_hard=missing_hard,
        missing_soft=missing_soft,
        should_strengthen=recommendations['should_strengthen'],
        jd_hard_skills=jd_hard_skills,
        jd_soft_skills=jd_soft_skills,
        jd_responsibilities=jd_responsibilities
    )
    
    # Calculate potential score
    potential_gain = len(missing_hard) * 7 + len([m for m in matched_hard if not m.get('in_experience')]) * 3
    recommendations['score_potential'] = min(100, current_score + potential_gain)
    
    # Summary
    recommendations['summary'] = _generate_summary(current_score, recommendations)
    
    return recommendations


def _get_add_skill_guidance(skill: str, responsibilities: List[str]) -> str:
    """Get specific guidance on how to add a skill."""
    skill_lower = skill.lower()
    
    # Find related responsibility
    related_resp = None
    for resp in responsibilities:
        if skill_lower in resp.lower():
            related_resp = resp
            break
    
    if related_resp:
        return f"JD mentions: '{related_resp[:80]}...' - Add {skill} in a bullet that addresses this"
    
    # Generic guidance by skill type
    if skill_lower in ['python', 'sql', 'java', 'javascript', 'scala', 'go']:
        return f"Add {skill} to experience bullets showing: data processing, API development, or automation"
    elif skill_lower in ['aws', 'gcp', 'azure']:
        return f"Mention specific {skill} services you've used (EC2, S3, Lambda, BigQuery, etc.)"
    elif skill_lower in ['docker', 'kubernetes', 'k8s']:
        return f"Add {skill} in deployment/CI-CD context with scale metrics"
    elif skill_lower in ['machine learning', 'ml', 'deep learning']:
        return f"Describe models built, metrics improved, or predictions deployed"
    elif skill_lower in ['react', 'vue', 'angular']:
        return f"Mention {skill} with specific features: state management, API integration, performance"
    else:
        return f"Add {skill} to relevant experience bullets where you've applied it"


def _get_skill_bullet_example(skill: str) -> str:
    """Get example bullet point for a skill."""
    skill_lower = skill.lower()
    
    examples = {
        'python': "Developed Python ETL pipeline processing 10M+ records daily, reducing processing time by 40%",
        'sql': "Optimized SQL queries across 5 databases, improving query performance by 60%",
        'aws': "Deployed microservices on AWS (EC2, Lambda, S3), handling 100K+ daily requests",
        'docker': "Containerized 15 microservices with Docker, reducing deployment time from 2hrs to 15min",
        'kubernetes': "Managed Kubernetes cluster (20 nodes) with auto-scaling, achieving 99.9% uptime",
        'react': "Built React dashboard with Redux state management, serving 5K+ daily active users",
        'machine learning': "Developed ML model achieving 92% accuracy, deployed to production serving 1M predictions/day",
        'scala': "Built Scala data pipelines using Spark, processing 50TB+ data for analytics",
        'go': "Developed Go microservices handling 10K RPS with <10ms latency",
        'matlab': "Implemented statistical models in MATLAB for time-series forecasting with 85% accuracy",
        'java': "Built Java backend services using Spring Boot, handling 50K concurrent users",
        'node.js': "Developed Node.js REST APIs with Express, achieving 99.9% uptime",
        'postgresql': "Designed PostgreSQL schema for 100M+ records with optimized indexing",
    }
    
    return examples.get(skill_lower, f"Implemented {skill} solution that [achieved specific metric/impact]")


def _get_quick_wins(resume: Dict, jd: Dict, match_result: Dict) -> List[Dict]:
    """Get easy, high-impact improvements."""
    quick_wins = []
    
    # 1. Check if skills section is too short
    skills_section = resume.get('sections', {}).get('skills', {})
    total_skills = sum(len(cat.get('items', [])) for cat in skills_section.get('categories', []))
    
    if total_skills < 15:
        quick_wins.append({
            'type': 'expand_skills',
            'action': 'Add more relevant skills to Skills section',
            'detail': f'Currently {total_skills} skills. ATS expects 15-25 for tech roles.',
            'effort': 'Low',
            'impact': 'Medium'
        })
    
    # 2. Check experience bullets - only for jobs with identifiable company/title
    experience = resume.get('sections', {}).get('experience', [])
    jobs_with_low_bullets = []
    for job in experience:
        bullets = job.get('bullets', [])
        company = job.get('company') or job.get('title') or None
        
        # Only add if we have a meaningful identifier and low bullet count
        if company and len(bullets) < 3:
            jobs_with_low_bullets.append({
                'company': company,
                'bullet_count': len(bullets)
            })
    
    if jobs_with_low_bullets:
        # Summarize rather than listing each job
        quick_wins.append({
            'type': 'add_bullets',
            'action': f"Add more experience bullets ({len(jobs_with_low_bullets)} jobs have <3 bullets)",
            'detail': 'Each job should have 4-6 bullets with action verbs and metrics.',
            'effort': 'Medium',
            'impact': 'High'
        })
    
    # 3. Check for metrics in bullets
    has_metrics = False
    for job in experience:
        for bullet in job.get('bullets', []):
            text = bullet.get('text', '') if isinstance(bullet, dict) else str(bullet)
            if any(c.isdigit() for c in str(text)):
                has_metrics = True
                break
    
    if not has_metrics and experience:
        quick_wins.append({
            'type': 'add_metrics',
            'action': 'Add quantified metrics to experience bullets',
            'detail': 'No metrics found. Add: percentages, user counts, time saved, etc.',
            'effort': 'Medium',
            'impact': 'High - Evidence score boost'
        })
    
    # 4. Check for action verbs at start of bullets
    weak_bullet_count = 0
    action_verbs = {'developed', 'built', 'designed', 'implemented', 'created', 'led', 'managed', 'optimized', 'improved', 'reduced', 'increased'}
    for job in experience:
        for bullet in job.get('bullets', []):
            text = bullet.get('text', '') if isinstance(bullet, dict) else str(bullet)
            if text:
                first_word = str(text).split()[0].lower() if str(text).split() else ''
                if first_word not in action_verbs:
                    weak_bullet_count += 1
    
    if weak_bullet_count > 3:
        quick_wins.append({
            'type': 'use_action_verbs',
            'action': 'Start bullets with strong action verbs',
            'detail': f'{weak_bullet_count} bullets dont start with action verbs. Use: Built, Developed, Led, Optimized...',
            'effort': 'Low',
            'impact': 'Medium - ATS favors action-oriented language'
        })
    
    return quick_wins


def _get_rewrite_suggestions(resume: Dict, jd_skills: set, responsibilities: List[str]) -> List[Dict]:
    """Suggest specific bullet rewrites."""
    suggestions = []
    
    experience = resume.get('sections', {}).get('experience', [])
    
    for job in experience[:2]:  # Focus on recent jobs
        for bullet in job.get('bullets', [])[:3]:
            text = bullet.get('text', '') if isinstance(bullet, dict) else str(bullet)
            
            # Find opportunities to add JD keywords
            missing_in_bullet = []
            for skill in list(jd_skills)[:5]:
                if skill not in text.lower():
                    missing_in_bullet.append(skill)
            
            if missing_in_bullet and len(text) > 20:
                suggestions.append({
                    'original': text[:100] + '...' if len(text) > 100 else text,
                    'issue': f"Missing JD keywords: {', '.join(missing_in_bullet[:3])}",
                    'suggestion': f"Rewrite to naturally include: {missing_in_bullet[0]}",
                    'why': 'ATS scans experience bullets for keyword matches'
                })
    
    return suggestions[:5]  # Limit to 5 suggestions


def _get_section_advice(resume: Dict, jd: Dict) -> Dict[str, str]:
    """Get advice for each resume section."""
    advice = {}
    
    # Skills section
    jd_skills = set(s.lower() for s in jd.get('requirements', {}).get('hard', {}).get('skills', []))
    resume_skills = set()
    for cat in resume.get('sections', {}).get('skills', {}).get('categories', []):
        resume_skills.update(s.lower() for s in cat.get('items', []))
    
    overlap = jd_skills & resume_skills
    if len(overlap) < len(jd_skills) * 0.5:
        advice['skills'] = f"Skills section covers {len(overlap)}/{len(jd_skills)} JD requirements. Add missing: {', '.join(list(jd_skills - resume_skills)[:5])}"
    else:
        advice['skills'] = "Skills section has good coverage. Focus on strengthening evidence in experience."
    
    # Experience section
    experience = resume.get('sections', {}).get('experience', [])
    if experience:
        avg_bullets = sum(len(job.get('bullets', [])) for job in experience) / len(experience)
        if avg_bullets < 4:
            advice['experience'] = f"Average {avg_bullets:.1f} bullets per job. Increase to 4-6 bullets with metrics."
        else:
            advice['experience'] = "Good bullet count. Ensure each contains action verbs and metrics."
    
    # Projects section
    projects = resume.get('sections', {}).get('projects', [])
    if not projects:
        advice['projects'] = "No projects section. Add 2-3 relevant projects showing JD skills in action."
    elif len(projects) < 2:
        advice['projects'] = "Add more projects. Projects section is great for showing skills without job experience."
    
    return advice


def _generate_summary(current_score: float, recommendations: Dict) -> str:
    """Generate executive summary of recommendations."""
    must_add_count = len(recommendations['must_add'])
    strengthen_count = len(recommendations['should_strengthen'])
    potential = recommendations['score_potential']
    
    if current_score >= 80:
        return f"Strong match! Minor tweaks could push you to {potential}%. Focus on strengthening existing skill evidence."
    elif current_score >= 60:
        return f"Good foundation. Add {must_add_count} missing skills and strengthen {strengthen_count} weak ones to reach {potential}%."
    elif current_score >= 40:
        return f"Partial match. Missing {must_add_count} critical skills. Follow the must-add list to improve from {current_score}% to {potential}%."
    else:
        return f"Significant gaps. This role requires skills not prominent in your resume. Add {must_add_count} must-have skills or consider a different role."


def _generate_path_to_100(
    current_score: float,
    evidence_avg: float,
    missing_hard: List[Dict],
    missing_soft: List[Dict],
    should_strengthen: List[Dict],
    jd_hard_skills: set,
    jd_soft_skills: set,
    jd_responsibilities: List[str]
) -> List[Dict]:
    """
    Generate step-by-step path to achieve 100% match.
    
    Returns list of numbered steps with:
    - step_number
    - action: what to do
    - impact: expected score gain
    - details: specific instructions
    - example: concrete example if applicable
    """
    steps = []
    step_num = 1
    running_score = current_score
    
    # Step 1: Add missing required skills (biggest impact)
    if missing_hard:
        skill_list = [m['skill'] for m in missing_hard]
        per_skill_impact = round(50 / max(len(jd_hard_skills), 1), 1)  # Hard skills = 50% of score
        
        steps.append({
            'step_number': step_num,
            'action': f"Add {len(missing_hard)} missing required skill(s) to your resume",
            'skills': skill_list,
            'impact': f"+{round(per_skill_impact * len(missing_hard))}% score",
            'details': [
                f"Add to Skills section: {', '.join(skill_list)}",
                "Also add each skill to at least 1-2 experience bullets with context"
            ],
            'examples': [
                _get_skill_bullet_example(skill_list[0]) if skill_list else None
            ]
        })
        running_score += per_skill_impact * len(missing_hard)
        step_num += 1
    
    # Step 2: Strengthen skills that are only in Skills section
    if should_strengthen:
        weak_skills = [s['skill'] for s in should_strengthen]
        
        steps.append({
            'step_number': step_num,
            'action': f"Move {len(weak_skills)} skill(s) from Skills section to Experience bullets",
            'skills': weak_skills,
            'impact': f"+{len(weak_skills) * 3}% score",
            'details': [
                f"These skills are listed but not demonstrated: {', '.join(weak_skills)}",
                "Add each skill to 2-3 experience bullets with action verbs and metrics"
            ],
            'examples': [
                _get_skill_bullet_example(weak_skills[0]) if weak_skills else None
            ]
        })
        running_score += len(weak_skills) * 3
        step_num += 1
    
    # Step 3: Improve evidence score
    if evidence_avg < 0.7:
        steps.append({
            'step_number': step_num,
            'action': "Improve evidence quality in experience bullets",
            'current': f"Evidence score: {evidence_avg}",
            'target': "Target: 0.8+",
            'impact': f"+{round((0.8 - evidence_avg) * 20)}% score",
            'details': [
                "Add quantified metrics (percentages, numbers, scale)",
                "Start bullets with action verbs (Developed, Built, Optimized)",
                "Include specific technologies and tools used"
            ],
            'examples': [
                "Before: 'Worked on backend systems'",
                "After: 'Developed Python microservices handling 10K requests/sec, reducing latency by 40%'"
            ]
        })
        running_score += (0.8 - evidence_avg) * 20
        step_num += 1
    
    # Step 4: Add soft skills if missing
    if missing_soft:
        soft_skill_list = [m['skill'] for m in missing_soft[:3]]
        
        steps.append({
            'step_number': step_num,
            'action': f"Add preferred/soft skills to boost score further",
            'skills': soft_skill_list,
            'impact': f"+{len(soft_skill_list) * 2}% score",
            'details': [
                f"Nice-to-have skills: {', '.join(soft_skill_list)}",
                "Add if you have relevant experience, otherwise skip"
            ],
            'examples': []
        })
        running_score += len(soft_skill_list) * 2
        step_num += 1
    
    # Final step: Polish and verify
    if running_score < 100:
        remaining = round(100 - running_score)
        steps.append({
            'step_number': step_num,
            'action': "Final polish for remaining points",
            'impact': f"+{remaining}% to reach 100%",
            'details': [
                "Add more experience bullets (4-6 per job)",
                "Include relevant projects demonstrating JD skills",
                "Match JD terminology exactly (keywords matter)",
                "Ensure skills appear in multiple sections for reinforcement"
            ],
            'examples': []
        })
    
    return steps

