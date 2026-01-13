"""
Knockout Filter Evaluation Engine

Compare resume JSON against JD JSON to determine ATS eligibility.
Knockout filters run BEFORE scoring - if failed, resume is auto-rejected.

Usage:
    python knockout.py <resume.json> <jd.json> [--output result.json]
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dateutil import parser as date_parser


def evaluate_knockout(resume: Dict, jd: Dict) -> Dict[str, Any]:
    """
    Evaluate resume against JD knockout filters.
    
    Args:
        resume: Parsed resume JSON
        jd: Parsed JD JSON
        
    Returns:
        Knockout evaluation result with pass/fail/risk status
    """
    checks = []
    failed = []
    risks = []
    
    filters = jd.get('requirements', {}).get('hard', {}).get('filters', {})
    
    # 1. Work Authorization Check
    work_auth_result = _check_work_authorization(resume, filters.get('work_authorization', {}))
    checks.append(work_auth_result)
    if work_auth_result['status'] == 'fail':
        failed.append(work_auth_result['rule'])
    elif work_auth_result['status'] == 'risk':
        risks.append(work_auth_result['message'])
    
    # 2. Location Check
    location_result = _check_location(resume, filters.get('location', {}))
    checks.append(location_result)
    if location_result['status'] == 'fail':
        failed.append(location_result['rule'])
    elif location_result['status'] == 'risk':
        risks.append(location_result['message'])
    
    # 3. Years of Experience Check
    experience_result = _check_experience(resume, filters.get('years_experience', {}))
    checks.append(experience_result)
    if experience_result['status'] == 'fail':
        failed.append(experience_result['rule'])
    elif experience_result['status'] == 'risk':
        risks.append(experience_result['message'])
    
    # 4. Degree Check
    degree_result = _check_degree(resume, filters.get('degree', {}))
    checks.append(degree_result)
    if degree_result['status'] == 'fail':
        failed.append(degree_result['rule'])
    elif degree_result['status'] == 'risk':
        risks.append(degree_result['message'])
    
    # 5. Certification Check
    cert_result = _check_certifications(resume, filters.get('certifications', {}))
    checks.append(cert_result)
    if cert_result['status'] == 'fail':
        failed.append(cert_result['rule'])
    elif cert_result['status'] == 'risk':
        risks.append(cert_result['message'])
    
    # 6. Security Clearance Check
    clearance_result = _check_clearance(resume, filters.get('clearance', {}))
    checks.append(clearance_result)
    if clearance_result['status'] == 'fail':
        failed.append(clearance_result['rule'])
    elif clearance_result['status'] == 'risk':
        risks.append(clearance_result['message'])
    
    # 7. Language Check
    language_result = _check_languages(resume, filters.get('languages', {}))
    checks.append(language_result)
    if language_result['status'] == 'fail':
        failed.append(language_result['rule'])
    elif language_result['status'] == 'risk':
        risks.append(language_result['message'])
    
    # Determine overall status
    if failed:
        overall_status = 'fail'
    elif risks:
        overall_status = 'risk'
    else:
        overall_status = 'pass'
    
    # Add warning if no filters found
    if not any(filters.values()):
        risks.append("No explicit hard filters found in JD")
    
    return {
        'knockout': {
            'overall_status': overall_status,
            'passed': overall_status != 'fail',
            'checks': checks,
            'failed_rules': failed,
            'risks': risks,
            'evaluated_at': datetime.now(timezone.utc).isoformat()
        }
    }


def _check_work_authorization(resume: Dict, filter_data: Dict) -> Dict:
    """Check work authorization requirement."""
    result = {
        'rule': 'work_authorization',
        'jd_value': None,
        'resume_value': 'not_specified',
        'status': 'pass',
        'message': None
    }
    
    if not filter_data or not filter_data.get('required'):
        result['message'] = 'No work authorization requirement in JD'
        return result
    
    result['jd_value'] = filter_data.get('raw', 'Required')
    
    # Check if sponsorship needed and not available
    if filter_data.get('sponsorship_available') is False:
        result['status'] = 'risk'
        result['message'] = 'JD states no sponsorship available - verify your authorization status'
    else:
        result['status'] = 'risk'
        result['message'] = 'Work authorization required but not explicitly stated in resume'
    
    return result


def _check_location(resume: Dict, filter_data: Dict) -> Dict:
    """Check location requirement."""
    result = {
        'rule': 'location',
        'jd_value': None,
        'resume_value': None,
        'status': 'pass',
        'message': None
    }
    
    if not filter_data or not filter_data.get('required'):
        result['message'] = 'No specific location requirement in JD'
        return result
    
    result['jd_value'] = filter_data.get('required')
    
    # Get resume location
    profile = resume.get('profile', {})
    location = profile.get('location', {})
    resume_location = location.get('raw') or location.get('state') or location.get('country')
    result['resume_value'] = resume_location or 'not_specified'
    
    if resume_location:
        # Simple check - does resume location match JD requirement
        jd_loc = str(filter_data.get('required', '')).lower()
        resume_loc = resume_location.lower()
        
        if 'us' in jd_loc or 'united states' in jd_loc:
            if any(x in resume_loc for x in ['us', 'usa', 'united states', 'sc', 'ca', 'ny', 'tx']):
                result['status'] = 'pass'
                result['message'] = 'Location matches US requirement'
            else:
                result['status'] = 'risk'
                result['message'] = 'Location may not match US requirement'
        else:
            result['status'] = 'pass'
            result['message'] = 'Location check passed'
    else:
        result['status'] = 'risk'
        result['message'] = 'Location not specified in resume'
    
    return result


def _check_experience(resume: Dict, filter_data: Dict) -> Dict:
    """Check years of experience requirement using classified experience totals."""
    result = {
        'rule': 'years_experience',
        'jd_value': None,
        'resume_value': None,
        'status': 'pass',
        'message': None,
        'breakdown': None
    }
    
    min_years = filter_data.get('min_years') if filter_data else None
    
    if not min_years:
        result['message'] = 'No years of experience requirement in JD'
        return result
    
    result['jd_value'] = f"{min_years}+ years"
    
    # Get experience totals from resume (computed by employment classifier)
    totals = resume.get('experience_totals', {})
    
    if not totals:
        # Fallback to old calculation if totals not available
        result['resume_value'] = '0 years'
        result['status'] = 'fail'
        result['message'] = 'No experience data found'
        return result
    
    # Get different experience measures
    full_time_years = totals.get('full_time_years', 0)
    internship_years = totals.get('internship_years', 0)
    total_years = totals.get('total_years_all', 0)
    weighted_years = totals.get('weighted_years', 0)
    
    # Add breakdown for transparency
    result['breakdown'] = {
        'full_time_years': full_time_years,
        'internship_years': internship_years,
        'total_years_all': total_years,
        'weighted_years_ats': weighted_years
    }
    
    # Primary check: use weighted years for ATS simulation
    result['resume_value'] = f"{weighted_years} years (weighted) / {full_time_years} full-time"
    
    # Check against requirement
    if weighted_years >= min_years:
        result['status'] = 'pass'
        result['message'] = f'Weighted experience ({weighted_years} years) meets requirement ({min_years}+ years)'
    elif weighted_years >= min_years * 0.8:  # Within 80%
        result['status'] = 'risk'
        result['message'] = f'Weighted experience ({weighted_years} years) is slightly below requirement ({min_years}+ years). Full-time only: {full_time_years} years'
    else:
        # Additional check: if JD likely wants full-time only
        if full_time_years >= min_years:
            result['status'] = 'risk'
            result['message'] = f'Full-time experience ({full_time_years} years) meets requirement, but weighted total ({weighted_years}) is low'
        else:
            result['status'] = 'fail'
            result['message'] = f'Experience does not meet requirement. Weighted: {weighted_years} years, Full-time: {full_time_years} years, Required: {min_years}+'
    
    return result


def _check_degree(resume: Dict, filter_data: Dict) -> Dict:
    """Check degree requirement."""
    result = {
        'rule': 'degree',
        'jd_value': None,
        'resume_value': None,
        'status': 'pass',
        'message': None
    }
    
    if not filter_data or not filter_data.get('required'):
        result['message'] = 'No degree requirement in JD'
        return result
    
    # Get accepted levels from JD (e.g., ['masters', 'doctorate'] for "PhD or MS")
    accepted_levels = filter_data.get('accepted_levels', [])
    result['jd_value'] = filter_data.get('level', 'Required')
    
    # Check resume education
    education = resume.get('sections', {}).get('education', [])
    
    if not education:
        if filter_data.get('required') == 'or_equivalent':
            result['status'] = 'risk'
            result['message'] = 'No degree found, but JD allows equivalent experience'
        else:
            result['status'] = 'fail'
            result['message'] = 'Degree required but not found in resume'
        return result
    
    # Get highest degree from resume
    degree_order = {'doctorate': 4, 'masters': 3, 'bachelors': 2, 'associate': 1}
    highest = None
    
    for edu in education:
        degree = edu.get('degree') or ''
        degree = degree.lower()
        
        if 'ph' in degree or 'doctor' in degree:
            highest = 'doctorate'
        elif 'm.s' in degree or 'master' in degree or 'm.a' in degree:
            highest = max(highest or '', 'masters', key=lambda x: degree_order.get(x, 0))
        elif 'b.s' in degree or 'b.a' in degree or 'bachelor' in degree:
            highest = max(highest or '', 'bachelors', key=lambda x: degree_order.get(x, 0))
    
    result['resume_value'] = highest or 'not_found'
    
    if highest:
        # If JD says "or equivalent experience", having ANY degree passes
        if filter_data.get('required') == 'or_equivalent':
            result['status'] = 'pass'
            result['message'] = f'Degree ({highest}) found - JD accepts degree or equivalent experience'
        # Check if resume degree is in accepted levels
        elif accepted_levels and highest in accepted_levels:
            result['status'] = 'pass'
            result['message'] = f'Degree ({highest}) is in accepted levels ({", ".join(accepted_levels)})'
        # Fallback: check if resume degree meets or exceeds minimum required
        elif degree_order.get(highest, 0) >= degree_order.get(filter_data.get('level', 'bachelors'), 2):
            result['status'] = 'pass'
            result['message'] = f'Degree ({highest}) meets requirement'
        else:
            result['status'] = 'fail'
            result['message'] = f'Degree ({highest}) does not meet requirement ({filter_data.get("level")})'
    else:
        # No degree found
        if filter_data.get('required') == 'or_equivalent':
            result['status'] = 'risk'
            result['message'] = 'No degree found, but JD allows equivalent experience'
        else:
            result['status'] = 'fail'
            result['message'] = 'No recognizable degree found'
    
    return result


def _check_certifications(resume: Dict, filter_data: Dict) -> Dict:
    """Check certification requirements."""
    result = {
        'rule': 'certification',
        'jd_value': None,
        'resume_value': [],
        'status': 'pass',
        'message': None
    }
    
    required_certs = filter_data.get('required', []) if filter_data else []
    
    if not required_certs:
        result['message'] = 'No certification requirement in JD'
        return result
    
    result['jd_value'] = required_certs
    
    # Check resume for certifications (in skills or certifications section)
    resume_text = json.dumps(resume).lower()
    found = []
    missing = []
    
    for cert in required_certs:
        cert_lower = cert.lower()
        if cert_lower in resume_text:
            found.append(cert)
        else:
            missing.append(cert)
    
    result['resume_value'] = found
    
    if not missing:
        result['status'] = 'pass'
        result['message'] = 'All required certifications found'
    else:
        result['status'] = 'fail'
        result['message'] = f'Missing certifications: {", ".join(missing)}'
    
    return result


def _check_clearance(resume: Dict, filter_data: Dict) -> Dict:
    """Check security clearance requirement."""
    result = {
        'rule': 'security_clearance',
        'jd_value': None,
        'resume_value': 'not_specified',
        'status': 'pass',
        'message': None
    }
    
    if not filter_data or not filter_data.get('required'):
        result['message'] = 'No security clearance requirement in JD'
        return result
    
    result['jd_value'] = filter_data.get('level', 'Required')
    
    # Check resume for clearance mention
    resume_text = json.dumps(resume).lower()
    
    clearance_keywords = ['clearance', 'secret', 'ts/sci', 'top secret']
    has_clearance = any(kw in resume_text for kw in clearance_keywords)
    
    if has_clearance:
        result['resume_value'] = 'mentioned'
        result['status'] = 'pass'
        result['message'] = 'Security clearance mentioned in resume'
    else:
        result['status'] = 'fail'
        result['message'] = 'Security clearance required but not found in resume'
    
    return result


def _check_languages(resume: Dict, filter_data: Dict) -> Dict:
    """Check language requirements."""
    result = {
        'rule': 'language',
        'jd_value': None,
        'resume_value': [],
        'status': 'pass',
        'message': None
    }
    
    required_langs = filter_data.get('required', []) if filter_data else []
    
    if not required_langs:
        result['message'] = 'No language requirement in JD'
        return result
    
    result['jd_value'] = required_langs
    
    # English is assumed for US jobs
    if required_langs == ['English']:
        result['status'] = 'pass'
        result['message'] = 'English fluency assumed'
        result['resume_value'] = ['English']
        return result
    
    # Check resume for language mentions
    resume_text = json.dumps(resume).lower()
    found = []
    
    for lang in required_langs:
        if lang.lower() in resume_text:
            found.append(lang)
    
    result['resume_value'] = found
    
    missing = [l for l in required_langs if l not in found]
    if not missing:
        result['status'] = 'pass'
        result['message'] = 'All required languages found'
    else:
        result['status'] = 'risk'
        result['message'] = f'Languages not explicitly stated: {", ".join(missing)}'
    
    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Evaluate resume against JD knockout filters',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python knockout.py resume.json jd.json
    python knockout.py resume.json jd.json --output result.json
        """
    )
    
    parser.add_argument('resume_json', help='Path to parsed resume JSON')
    parser.add_argument('jd_json', help='Path to parsed JD JSON')
    parser.add_argument('--output', '-o', help='Output file path', default=None)
    parser.add_argument('--pretty', '-p', action='store_true', help='Pretty print')
    
    args = parser.parse_args()
    
    try:
        # Load inputs
        resume = json.loads(Path(args.resume_json).read_text(encoding='utf-8'))
        jd = json.loads(Path(args.jd_json).read_text(encoding='utf-8'))
        
        # Evaluate
        result = evaluate_knockout(resume, jd)
        
        # Output
        indent = 2 if args.pretty else None
        json_output = json.dumps(result, indent=indent, ensure_ascii=False)
        
        if args.output:
            Path(args.output).write_text(json_output, encoding='utf-8')
            print(f"Knockout evaluation saved to: {args.output}")
        else:
            print(json_output)
        
        # Print summary
        ko = result['knockout']
        status_emoji = '✅' if ko['passed'] else '❌'
        print(f"\n{status_emoji} Overall Status: {ko['overall_status'].upper()}")
        
        if ko['failed_rules']:
            print(f"Failed: {', '.join(ko['failed_rules'])}")
        if ko['risks']:
            print(f"Risks: {len(ko['risks'])} warnings")
            
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
