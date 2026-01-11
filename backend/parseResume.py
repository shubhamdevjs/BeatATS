"""
Resume to JSON Parser - ATS-Style

Main entry point for parsing resumes into structured JSON format.
Supports PDF and DOCX file formats.

Usage:
    python parseResume.py <resume_file> [--output <output.json>]
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Local imports
from extractors import extract_pdf, extract_docx
from parsers import (
    detect_sections,
    parse_profile,
    parse_skills,
    parse_experience,
    parse_education,
    parse_projects
)
from parsers.section_detector import get_header_portion
from parsers.projects_parser import parse_awards
from indexer import build_term_index, collect_evidence, calculate_parse_quality


SCHEMA_VERSION = "1.0"


def parse_resume(file_path: str) -> Dict[str, Any]:
    """
    Parse a resume file into structured JSON.
    
    Args:
        file_path: Path to the resume file (PDF or DOCX)
        
    Returns:
        Structured resume JSON dict
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is not supported
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {file_path}")
    
    file_type = path.suffix.lower().lstrip('.')
    
    if file_type not in ['pdf', 'docx', 'doc']:
        raise ValueError(f"Unsupported file format: {file_type}. Supported: pdf, docx")
    
    # Extract raw text
    if file_type == 'pdf':
        extraction = extract_pdf(file_path)
    else:
        extraction = extract_docx(file_path)
    
    raw_text = extraction['text']
    pages = extraction['pages']
    page_count = extraction['page_count']
    signals = extraction['signals']
    
    # Build document metadata
    document = {
        'file_name': path.name,
        'file_type': file_type,
        'page_count': page_count,
        'extracted_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Build raw layer
    raw = {
        'text': raw_text,
        'pages': pages
    }
    
    # Detect sections
    sections_detected = detect_sections(raw_text)
    
    # Parse profile - use full text since PDF layouts vary
    profile = parse_profile(raw_text, None)
    
    # Parse sections
    sections = {}
    
    # Skills
    skills_content = sections_detected.get('skills', {}).get('content', '')
    sections['skills'] = parse_skills(skills_content, raw_text)
    
    # Experience
    exp_content = sections_detected.get('experience', {}).get('content', '')
    sections['experience'] = parse_experience(exp_content)
    
    # Education
    edu_content = sections_detected.get('education', {}).get('content', '')
    sections['education'] = parse_education(edu_content)
    
    # Projects
    proj_content = sections_detected.get('projects', {}).get('content', '')
    sections['projects'] = parse_projects(proj_content)
    
    # Awards
    awards_content = sections_detected.get('awards', {}).get('content', '')
    sections['awards'] = parse_awards(awards_content)
    
    # Build parsed data for indexing
    parsed_data = {
        'profile': profile,
        'sections': sections
    }
    
    # Build term index
    index = {
        'terms': build_term_index(parsed_data, raw_text)
    }
    
    # Collect evidence
    evidence = collect_evidence(parsed_data, raw_text)
    
    # Calculate parse quality
    parse_quality = calculate_parse_quality(parsed_data, signals)
    
    # Assemble final JSON
    result = {
        'schema_version': SCHEMA_VERSION,
        'document': document,
        'raw': raw,
        'parse_quality': parse_quality,
        'profile': profile,
        'sections': sections,
        'index': index,
        'evidence': evidence
    }
    
    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Parse a resume into structured JSON format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python parseResume.py resume.pdf
    python parseResume.py resume.docx --output parsed.json
    python parseResume.py resume.pdf --pretty
        """
    )
    
    parser.add_argument(
        'resume_file',
        help='Path to the resume file (PDF or DOCX)'
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
        result = parse_resume(args.resume_file)
        
        # Format JSON
        indent = 2 if args.pretty else None
        json_output = json.dumps(result, indent=indent, ensure_ascii=False)
        
        # Output
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(json_output, encoding='utf-8')
            print(f"Parsed resume saved to: {args.output}")
            print(f"Parse quality score: {result['parse_quality']['score']}")
        else:
            print(json_output)
            
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing resume: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
