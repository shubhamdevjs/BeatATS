"""
BeatATS Resume Analyzer

Complete pipeline: Resume parsing → JD parsing → Knockout → Matching → Score

Usage:
    python analyze.py <resume_file> <jd_file> [--output result.json]
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from parseResume import parse_resume
from parseJD import parse_jd
from knockout import evaluate_knockout
from matcher import match_keywords_v2 as match_keywords
from recommendations import generate_detailed_recommendations


def analyze(resume_path: str, jd_path: str) -> Dict[str, Any]:
    """
    Full ATS analysis pipeline.
    
    Args:
        resume_path: Path to resume file (PDF/DOCX)
        jd_path: Path to JD text file
        
    Returns:
        Complete analysis result
    """
    # Step 1: Parse resume
    resume = parse_resume(resume_path)
    
    # Step 2: Parse JD
    jd_text = Path(jd_path).read_text(encoding='utf-8')
    jd = parse_jd(jd_text)
    
    # Step 3: Knockout evaluation
    knockout_result = evaluate_knockout(resume, jd)
    
    # Step 4: Keyword matching (ALWAYS run, regardless of knockout)
    match_result = match_keywords(resume, jd)
    
    # Step 5: Generate detailed recommendations
    detailed_recs = generate_detailed_recommendations(resume, jd, match_result, knockout_result)
    
    # Build final report
    result = {
        'schema_version': '1.0',
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'resume': {
            'file': Path(resume_path).name,
            'name': resume.get('profile', {}).get('name'),
            'parse_quality': resume.get('parse_quality', {}).get('score')
        },
        'jd': {
            'file': Path(jd_path).name,
            'title': jd.get('role', {}).get('title'),
            'hard_skills_count': len(jd.get('requirements', {}).get('hard', {}).get('skills', [])),
            'soft_skills_count': len(jd.get('requirements', {}).get('preferred', {}).get('skills', []))
        },
        'knockout': knockout_result['knockout'],
        'matching': match_result,
        'overall': _calculate_overall(knockout_result, match_result),
        'recommendations': detailed_recs
    }
    
    return result


def _calculate_overall(knockout: Dict, matching: Dict) -> Dict:
    """Calculate overall ATS analysis result."""
    ko = knockout['knockout']
    match_score = matching.get('match_summary', {}).get('overall_score', 0)
    
    # Always calculate skill-based score
    if ko['overall_status'] == 'risk':
        risk_penalty = len(ko.get('risks', [])) * 2
        adjusted_score = max(0, match_score - risk_penalty)
    else:
        adjusted_score = match_score
    
    # Determine verdict based on score
    if adjusted_score >= 80:
        verdict = 'STRONG MATCH'
    elif adjusted_score >= 60:
        verdict = 'GOOD MATCH'
    elif adjusted_score >= 40:
        verdict = 'PARTIAL MATCH'
    else:
        verdict = 'WEAK MATCH'
    
    # If knockout failed, add warning but still show score
    if not ko['passed']:
        return {
            'verdict': f'BLOCKED ({verdict})',
            'ats_score': round(adjusted_score, 1),
            'effective_score': 0,
            'knockout_failed': True,
            'message': f'⚠️ KNOCKOUT FILTER FAILED - ATS will likely auto-reject. Skill match is {adjusted_score}% but blocked by: {", ".join(ko["failed_rules"])}',
            'failed_filters': ko['failed_rules'],
            'top_missing_skills': [m['skill'] for m in matching.get('missing', {}).get('hard', [])[:3]]
        }
    
    return {
        'verdict': verdict,
        'ats_score': round(adjusted_score, 1),
        'effective_score': round(adjusted_score, 1),
        'knockout_failed': False,
        'message': _get_verdict_message(verdict, ko, matching),
        'top_missing_skills': [m['skill'] for m in matching.get('missing', {}).get('hard', [])[:3]]
    }


def _get_verdict_message(verdict: str, knockout: Dict, matching: Dict) -> str:
    """Generate human-readable verdict message."""
    missing_hard = matching.get('missing', {}).get('hard', [])
    
    if verdict == 'STRONG MATCH':
        return 'Resume is well-aligned with job requirements. High chance of passing ATS.'
    elif verdict == 'GOOD MATCH':
        if missing_hard:
            return f'Good match but consider adding: {", ".join(m["skill"] for m in missing_hard[:2])}'
        return 'Good match with job requirements.'
    elif verdict == 'PARTIAL MATCH':
        return f'Missing {len(missing_hard)} required skills. Resume may rank lower in ATS.'
    else:
        return 'Significant skill gaps. Consider tailoring resume or different role.'


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Complete ATS resume analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python analyze.py resume.pdf job.txt
    python analyze.py resume.pdf job.txt --output report.json --pretty
        """
    )
    
    parser.add_argument('resume', help='Path to resume (PDF/DOCX)')
    parser.add_argument('jd', help='Path to job description (TXT)')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--pretty', '-p', action='store_true', help='Pretty print')
    
    args = parser.parse_args()
    
    try:
        result = analyze(args.resume, args.jd)
        
        indent = 2 if args.pretty else None
        json_output = json.dumps(result, indent=indent, ensure_ascii=False)
        
        if args.output:
            Path(args.output).write_text(json_output, encoding='utf-8')
            print(f"Analysis saved to: {args.output}")
        
        # Print summary
        overall = result['overall']
        ko = result['knockout']
        
        print("\n" + "="*50)
        print("🎯 BEATATS ANALYSIS REPORT")
        print("="*50)
        print(f"\n📄 Resume: {result['resume']['name'] or result['resume']['file']}")
        print(f"📋 Job: {result['jd']['title'] or result['jd']['file']}")
        
        print(f"\n{'✅' if ko['passed'] else '❌'} Knockout: {ko['overall_status'].upper()}")
        if ko['failed_rules']:
            print(f"   Failed: {', '.join(ko['failed_rules'])}")
        
        # Always show skill match results
        match = result['matching']['match_summary']
        print(f"\n📊 Skill Match: {match.get('overall_score', 0)}%")
        print(f"   Hard: {match.get('hard_skill_match', 'N/A')}")
        print(f"   Soft: {match.get('soft_skill_match', 'N/A')}")
        if match.get('evidence_avg') is not None:
            print(f"   Evidence: {match.get('evidence_avg')}")
        
        print(f"\n🏆 VERDICT: {overall['verdict']}")
        if overall.get('knockout_failed'):
            print(f"   Skill Score: {overall['ats_score']}% (blocked by knockout)")
            print(f"   Effective Score: 0% (auto-rejected)")
        else:
            print(f"   ATS Score: {overall['ats_score']}%")
        print(f"   {overall['message']}")
        
        if overall.get('top_missing_skills'):
            print(f"\n⚠️  Missing: {', '.join(overall['top_missing_skills'])}")
        
        # Print detailed recommendations
        recs = result.get('recommendations', {})
        if recs:
            print("\n" + "="*50)
            print("📋 DETAILED RECOMMENDATIONS")
            print("="*50)
            
            # Summary
            if recs.get('summary'):
                print(f"\n💡 {recs['summary']}")
                print(f"   Potential Score: {recs.get('score_potential', 0)}%")
            
            # Must Add - Critical skills
            if recs.get('must_add'):
                print("\n🔴 MUST ADD (Critical - Missing Required Skills):")
                for i, item in enumerate(recs['must_add'][:5], 1):
                    print(f"   {i}. {item['skill']} ({item['impact']})")
                    print(f"      → {item['how_to_add']}")
                    print(f"      Example: \"{item['example'][:70]}...\"")
            
            # Should Strengthen
            if recs.get('should_strengthen'):
                print("\n🟡 STRENGTHEN (Move from Skills section to Experience):")
                for item in recs['should_strengthen'][:3]:
                    print(f"   • {item['skill']}: {item['action']}")
            
            # Quick Wins
            if recs.get('quick_wins'):
                print("\n⚡ QUICK WINS (Easy Improvements):")
                for item in recs['quick_wins'][:3]:
                    print(f"   • {item['action']} ({item['effort']} effort, {item['impact']} impact)")
            
            # Section Advice
            if recs.get('section_advice'):
                print("\n📝 SECTION-BY-SECTION ADVICE:")
                for section, advice in recs['section_advice'].items():
                    print(f"   {section.upper()}: {advice}")
        
        print("\n" + "="*50)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
