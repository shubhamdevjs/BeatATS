"""
Employment Type Classifier

Classifies each experience role as:
- full_time
- internship
- contract
- part_time
- research
- volunteer
- unknown

Uses scoring rules based on:
- Title keywords (strongest signal)
- Duration heuristics
- Organization patterns
- Bullet content signals
"""

import re
from typing import Dict, List, Any, Tuple
from datetime import datetime
from dateutil import parser as date_parser


# ============================================================
# CLASSIFICATION RULES
# ============================================================

# Title keyword patterns with scores
TITLE_PATTERNS = {
    'internship': [
        (r'\bintern\b', 90),
        (r'\binternship\b', 90),
        (r'\bco-?op\b', 85),
        (r'\btrainee\b', 80),
        (r'\bapprentice\b', 80),
        (r'\bstudent\s+(?:developer|engineer|analyst)\b', 75),
        (r'\bsummer\s+(?:intern|associate)\b', 90),
    ],
    'contract': [
        (r'\bcontract(?:or)?\b', 90),
        (r'\bconsultant\b', 85),
        (r'\bfreelance\b', 90),
        (r'\b1099\b', 95),
        (r'\bindependent\b', 70),
        (r'\bcontingent\b', 80),
    ],
    'part_time': [
        (r'\bpart[\s-]?time\b', 90),
        (r'\bpt\b', 60),
    ],
    'research': [
        (r'\bresearch\s+assistant\b', 90),
        (r'\bra\b', 50),  # Low score - ambiguous
        (r'\blab\s+assistant\b', 85),
        (r'\bfellow\b', 80),
        (r'\bphd\s+(?:student|candidate|researcher)\b', 90),
        (r'\bgraduate\s+assistant\b', 85),
        (r'\bpostdoc\b', 85),
    ],
    'volunteer': [
        (r'\bvolunteer\b', 90),
        (r'\bunpaid\b', 85),
        (r'\bpro\s+bono\b', 90),
    ],
}

# Organization patterns (weak signals)
ORG_PATTERNS = {
    'research': [
        (r'\buniversity\b', 30),
        (r'\bcollege\b', 25),
        (r'\blab(?:oratory)?\b', 35),
        (r'\bresearch\s+(?:center|institute)\b', 40),
        (r'\binstitute\b', 25),
    ],
}

# Experience weights for ATS calculation
DEFAULT_WEIGHTS = {
    'full_time': 1.0,
    'contract': 1.0,
    'part_time': 0.5,
    'internship': 0.35,
    'research': 0.35,
    'volunteer': 0.1,
    'unknown': 0.25,
}


# ============================================================
# CLASSIFIER
# ============================================================

def classify_employment_type(job: Dict) -> Dict[str, Any]:
    """
    Classify a single job's employment type.
    
    Args:
        job: Job dict with title, company, dates, bullets
        
    Returns:
        Classification result with type, confidence, and signals
    """
    title = (job.get('title') or '').lower()
    company = (job.get('company') or '').lower()
    bullets = job.get('bullets', [])
    dates = job.get('dates', {})
    
    # Collect signals
    signals = []
    type_scores = {
        'full_time': 0,
        'internship': 0,
        'contract': 0,
        'part_time': 0,
        'research': 0,
        'volunteer': 0,
    }
    
    # 1. Title keyword matching (strongest signal)
    for emp_type, patterns in TITLE_PATTERNS.items():
        for pattern, weight in patterns:
            if re.search(pattern, title, re.IGNORECASE):
                type_scores[emp_type] += weight
                signals.append({
                    'signal': 'title_keyword',
                    'pattern': pattern,
                    'matched': re.search(pattern, title, re.IGNORECASE).group(),
                    'weight': weight
                })
    
    # 2. Organization patterns (weak signal)
    for emp_type, patterns in ORG_PATTERNS.items():
        for pattern, weight in patterns:
            if re.search(pattern, company, re.IGNORECASE):
                type_scores[emp_type] += weight
                signals.append({
                    'signal': 'org_pattern',
                    'pattern': pattern,
                    'matched': company,
                    'weight': weight
                })
    
    # 3. Duration heuristics
    duration_months = _calculate_duration_months(dates)
    if duration_months:
        if 2 <= duration_months <= 5:
            # Short duration - more likely internship
            type_scores['internship'] += 20
            signals.append({
                'signal': 'duration_short',
                'value': f'{duration_months}_months',
                'weight': 20
            })
        elif duration_months < 2:
            # Very short - could be project/temp
            type_scores['internship'] += 10
            signals.append({
                'signal': 'duration_very_short',
                'value': f'{duration_months}_months',
                'weight': 10
            })
    
    # 4. Bullet content signals
    bullet_text = ' '.join(
        b.get('text', '') if isinstance(b, dict) else str(b) 
        for b in bullets
    ).lower()
    
    bullet_signals = [
        (r'summer\s+internship', 'internship', 30),
        (r'internship\s+program', 'internship', 25),
        (r'part[\s-]?time', 'part_time', 40),
        (r'contract\s+(?:position|role)', 'contract', 30),
        (r'research\s+project', 'research', 25),
    ]
    
    for pattern, emp_type, weight in bullet_signals:
        if re.search(pattern, bullet_text, re.IGNORECASE):
            type_scores[emp_type] += weight
            signals.append({
                'signal': 'bullet_content',
                'pattern': pattern,
                'weight': weight
            })
    
    # 5. Default to full-time if no non-fulltime signals found
    # Key insight: if there are NO internship/contract/volunteer signals, assume full-time
    non_fulltime_score = sum([
        type_scores['internship'],
        type_scores['contract'], 
        type_scores['part_time'],
        type_scores['research'],
        type_scores['volunteer']
    ])
    
    if non_fulltime_score == 0:
        # No intern/contract/etc keywords found - default to full-time
        # Stronger signal if duration > 5 months (not typical internship)
        if duration_months and duration_months > 5:
            type_scores['full_time'] += 60
            signals.append({
                'signal': 'duration_long_default_fulltime',
                'value': f'{duration_months}_months',
                'weight': 60
            })
        else:
            # Even short duration without intern keyword = likely full-time
            type_scores['full_time'] += 35
            signals.append({
                'signal': 'no_nonft_keywords_default_fulltime',
                'value': 'no intern/contract keywords',
                'weight': 35
            })
    
    # Also check for standard job titles as additional signal
    full_time_indicators = [
        r'\bengineer\b', r'\bdeveloper\b', r'\bmanager\b', r'\banalyst\b',
        r'\bdesigner\b', r'\barchitect\b', r'\blead\b', r'\bsenior\b',
        r'\bjunior\b', r'\bstaff\b', r'\bprincipal\b', r'\bsde\b', r'\bswe\b',
    ]
    for pattern in full_time_indicators:
        if re.search(pattern, title, re.IGNORECASE):
            type_scores['full_time'] += 25
            signals.append({
                'signal': 'title_fulltime_keyword',
                'pattern': pattern,
                'weight': 25
            })
            break
    
    # Determine final type
    max_score = max(type_scores.values())
    if max_score == 0:
        # Truly unknown - no signals at all, default to full_time anyway
        final_type = 'full_time'
        confidence = 0.5
        signals.append({
            'signal': 'fallback_default_fulltime',
            'value': 'no signals found',
            'weight': 0
        })
    else:
        final_type = max(type_scores, key=type_scores.get)
        # Confidence based on score magnitude and separation from others
        sorted_scores = sorted(type_scores.values(), reverse=True)
        gap = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0]
        confidence = min(0.99, (max_score / 100) * 0.6 + (gap / 100) * 0.4)
    
    return {
        'type': final_type,
        'confidence': round(confidence, 2),
        'signals': signals,
        'scores': type_scores,
        'needs_review': confidence < 0.75
    }


def _calculate_duration_months(dates: Dict) -> int:
    """Calculate duration in months from dates dict."""
    start = dates.get('start')
    end = dates.get('end')
    
    if not start:
        return 0
    
    try:
        start_dt = date_parser.parse(str(start))
        if end:
            end_dt = date_parser.parse(str(end))
        else:
            end_dt = datetime.now()
        
        months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)
        return max(0, months)
    except:
        return 0


# ============================================================
# EXPERIENCE CALCULATOR
# ============================================================

def calculate_experience_totals(experience: List[Dict], weights: Dict = None) -> Dict[str, Any]:
    """
    Calculate experience totals by type with weighted ATS score.
    
    Args:
        experience: List of job dicts with employment_classification
        weights: Optional custom weights per type
        
    Returns:
        Experience totals summary
    """
    weights = weights or DEFAULT_WEIGHTS
    
    # Initialize totals
    totals = {
        'full_time_months': 0,
        'internship_months': 0,
        'contract_months': 0,
        'part_time_months': 0,
        'research_months': 0,
        'volunteer_months': 0,
        'unknown_months': 0,
    }
    
    # Track months for overlap detection (simplified - by month)
    month_sets = {emp_type: set() for emp_type in totals.keys()}
    
    for job in experience:
        classification = job.get('employment_classification', {})
        emp_type = classification.get('type', 'unknown')
        key = f'{emp_type}_months'
        
        if key not in totals:
            key = 'unknown_months'
            emp_type = 'unknown'
        
        # Get date range
        dates = job.get('dates', {})
        months_list = _get_months_in_range(dates)
        
        # Add to month set (handles overlaps)
        month_sets[key].update(months_list)
    
    # Convert sets to counts
    for key, month_set in month_sets.items():
        totals[key] = len(month_set)
    
    # Calculate totals
    totals['total_months_all'] = sum(totals[f'{t}_months'] for t in weights.keys())
    
    # Calculate weighted months
    weighted_months = 0
    for emp_type, weight in weights.items():
        key = f'{emp_type}_months'
        if key in totals:
            weighted_months += totals[key] * weight
    
    totals['weighted_months'] = round(weighted_months, 1)
    totals['weighted_years'] = round(weighted_months / 12, 1)
    
    # Plain totals in years
    totals['full_time_years'] = round(totals['full_time_months'] / 12, 1)
    totals['internship_years'] = round(totals['internship_months'] / 12, 1)
    totals['total_years_all'] = round(totals['total_months_all'] / 12, 1)
    
    return totals


def _get_months_in_range(dates: Dict) -> List[str]:
    """Get list of YYYY-MM strings for each month in date range."""
    start = dates.get('start')
    end = dates.get('end')
    
    if not start:
        return []
    
    try:
        start_dt = date_parser.parse(str(start))
        if end:
            end_dt = date_parser.parse(str(end))
        else:
            end_dt = datetime.now()
        
        months = []
        current = start_dt
        while current <= end_dt:
            months.append(f'{current.year}-{current.month:02d}')
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return months
    except:
        return []


# ============================================================
# MAIN FUNCTION
# ============================================================

def classify_all_experience(experience: List[Dict]) -> Tuple[List[Dict], Dict]:
    """
    Classify all experience entries and compute totals.
    
    Args:
        experience: List of job dicts
        
    Returns:
        Tuple of (annotated experience list, experience totals)
    """
    annotated = []
    
    for job in experience:
        job_copy = dict(job)
        job_copy['employment_classification'] = classify_employment_type(job)
        annotated.append(job_copy)
    
    totals = calculate_experience_totals(annotated)
    
    return annotated, totals
