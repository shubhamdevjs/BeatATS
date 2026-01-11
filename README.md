# Resume Parser - ATS Style

A Python-based resume parser that extracts structured JSON from PDF/DOCX resumes, similar to ATS (Applicant Tracking System) parsers.

## Features

- **PDF & DOCX Support** - Extract text from both formats
- **Profile Extraction** - Name, email, phone, location, links (LinkedIn, GitHub)
- **Skills Parsing** - Categorized skills with mentions tracking
- **Experience Parsing** - Company, title, dates, bullets with skill detection
- **Education Parsing** - School, degree, major, GPA, courses
- **Projects & Awards** - Structured extraction with tech stack
- **Term Indexing** - Inverted index for fast skill/keyword lookup
- **Evidence Tracking** - Context snippets with confidence scores
- **Parse Quality Score** - Diagnostics for extraction reliability

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Usage

```bash
# Parse a resume and output to console
python parseResume.py resume.pdf

# Save to file with pretty formatting
python parseResume.py resume.pdf --pretty --output result.json

# Parse DOCX
python parseResume.py resume.docx -p -o output.json
```

## Output Schema

```json
{
  "schema_version": "1.0",
  "document": { "file_name", "file_type", "page_count", "extracted_at" },
  "parse_quality": { "score", "warnings", "errors", "signals" },
  "profile": { "name", "emails", "phones", "location", "links" },
  "sections": {
    "skills": { "categories", "all", "mentions" },
    "experience": [{ "company", "title", "dates", "bullets" }],
    "education": [{ "school", "degree", "major", "courses" }],
    "projects": [{ "name", "stack", "bullets" }],
    "awards": [{ "title", "raw" }]
  },
  "index": { "terms": { "<term>": [{ "section", "snippet" }] } },
  "evidence": [{ "field", "value", "context", "confidence" }]
}
```

## Project Structure

```
backend/
├── parseResume.py          # Main entry point
├── requirements.txt        # Dependencies
├── indexer.py              # Term indexing & evidence
├── extractors/
│   ├── pdf_extractor.py    # PyMuPDF extraction
│   └── docx_extractor.py   # python-docx extraction
├── parsers/
│   ├── section_detector.py # Section header detection
│   ├── profile_parser.py   # Name, contact info
│   ├── skills_parser.py    # Skill categorization
│   ├── experience_parser.py# Work history parsing
│   ├── education_parser.py # Education parsing
│   └── projects_parser.py  # Projects & awards
└── utils/
    ├── date_utils.py       # Date normalization
    └── text_utils.py       # Text processing
```

## Dependencies

- `pymupdf` - PDF text extraction
- `python-docx` - DOCX parsing
- `python-dateutil` - Date normalization
- `phonenumbers` - Phone parsing
- `email-validator` - Email validation
