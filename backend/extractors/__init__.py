"""Resume text extraction modules."""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.pdf_extractor import extract_pdf
from extractors.docx_extractor import extract_docx

__all__ = ['extract_pdf', 'extract_docx']
