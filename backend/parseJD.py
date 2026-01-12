"""
JD (Job Description) Parser

Parse job descriptions into structured JSON for ATS matching.

Usage:
    python parseJD.py <jd_text_file> [--output <output.json>]
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from jd_parsers.section_extractor import extract_sections, extract_role_info
from jd_parsers.skill_extractor import extract_jd_skills, extract_responsibilities
from jd_parsers.filter_extractor import extract_filters


SCHEMA_VERSION = "1.0"


def parse_jd(jd_text: str) -> Dict[str, Any]:
    """
    Parse job description text into structured JSON.
    
    Args:
        jd_text: Raw job description text
        
    Returns:
        Structured JD JSON dict
    """
    # Extract sections
    sections = extract_sections(jd_text)
    
    # Extract role metadata
    role = extract_role_info(jd_text)
    
    # Extract skills (hard vs soft)
    skills = extract_jd_skills(jd_text, sections)
    
    # Extract responsibilities
    responsibilities = extract_responsibilities(sections)
    
    # Extract knockout filters
    filters = extract_filters(jd_text)
    
    # Build requirements structure
    requirements = {
        'hard': {
            'skills': skills['hard'],
            'responsibilities': responsibilities,
            'filters': filters
        },
        'preferred': {
            'skills': skills['soft']
        }
    }
    
    # Build keywords for matching
    keywords = {
        'must_have': skills['hard'],
        'nice_to_have': skills['soft']
    }
    
    # Build final output
    result = {
        'schema_version': SCHEMA_VERSION,
        'parsed_at': datetime.now(timezone.utc).isoformat(),
        'role': role,
        'requirements': requirements,
        'keywords': keywords,
        'sections': {name: data['content'] for name, data in sections.items()},
        'skills_detail': skills
    }
    
    return result


def parse_jd_file(file_path: str) -> Dict[str, Any]:
    """
    Parse job description from a text file.
    
    Args:
        file_path: Path to JD text file
        
    Returns:
        Structured JD JSON dict
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"JD file not found: {file_path}")
    
    jd_text = path.read_text(encoding='utf-8')
    
    return parse_jd(jd_text)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Parse a job description into structured JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python parseJD.py job_description.txt
    python parseJD.py jd.txt --output parsed_jd.json
    python parseJD.py jd.txt --pretty
        """
    )
    
    parser.add_argument(
        'jd_file',
        help='Path to the job description text file'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output JSON file path (default: stdout)',
        default=None
    )
    
    parser.add_argument(
        '--pretty', '-p',
        action='store_true',
        help='Pretty print JSON output'
    )
    
    args = parser.parse_args()
    
    try:
        result = parse_jd_file(args.jd_file)
        
        # Format JSON
        indent = 2 if args.pretty else None
        json_output = json.dumps(result, indent=indent, ensure_ascii=False)
        
        # Output
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(json_output, encoding='utf-8')
            print(f"Parsed JD saved to: {args.output}")
            print(f"Hard skills found: {len(result['requirements']['hard']['skills'])}")
            print(f"Soft skills found: {len(result['requirements']['preferred']['skills'])}")
        else:
            print(json_output)
            
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing JD: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
