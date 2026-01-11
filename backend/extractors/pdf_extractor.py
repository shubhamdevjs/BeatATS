"""PDF text extraction using PyMuPDF."""
import fitz  # PyMuPDF
from typing import Dict, List, Any
from pathlib import Path


def extract_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extract text and metadata from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Dict containing:
            - text: Full extracted text
            - pages: List of per-page text
            - page_count: Number of pages
            - signals: Layout detection signals
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    doc = fitz.open(file_path)
    
    pages = []
    full_text_parts = []
    signals = {
        "likely_two_column": False,
        "contains_tables": False,
        "has_icons": False,
        "low_text_density": False
    }
    
    for page_num, page in enumerate(doc, start=1):
        # Extract text with layout preservation
        text = page.get_text("text")
        pages.append({
            "page": page_num,
            "text": text
        })
        full_text_parts.append(text)
        
        # Detect layout signals
        blocks = page.get_text("dict")["blocks"]
        _detect_layout_signals(blocks, page.rect.width, signals)
    
    doc.close()
    
    return {
        "text": "\n".join(full_text_parts),
        "pages": pages,
        "page_count": len(pages),
        "signals": signals
    }


def _detect_layout_signals(blocks: List[Dict], page_width: float, signals: Dict) -> None:
    """
    Analyze text blocks to detect layout patterns.
    
    Args:
        blocks: List of text block dictionaries from PyMuPDF
        page_width: Width of the page
        signals: Dictionary to update with detected signals
    """
    text_blocks = [b for b in blocks if b.get("type") == 0]  # type 0 = text
    
    if not text_blocks:
        signals["low_text_density"] = True
        return
    
    # Detect two-column layout
    # Check if significant text exists on both left and right halves
    mid_x = page_width / 2
    left_blocks = 0
    right_blocks = 0
    
    for block in text_blocks:
        bbox = block.get("bbox", [0, 0, 0, 0])
        block_center_x = (bbox[0] + bbox[2]) / 2
        
        if block_center_x < mid_x - 50:  # With margin
            left_blocks += 1
        elif block_center_x > mid_x + 50:
            right_blocks += 1
    
    if left_blocks > 2 and right_blocks > 2:
        signals["likely_two_column"] = True
    
    # Detect tables (multiple aligned blocks)
    if len(text_blocks) > 10:
        # Simple heuristic: many small blocks might indicate tables
        small_blocks = sum(1 for b in text_blocks 
                          if (b["bbox"][2] - b["bbox"][0]) < page_width * 0.3)
        if small_blocks > len(text_blocks) * 0.5:
            signals["contains_tables"] = True
    
    # Detect low text density
    total_text = "".join(
        span.get("text", "") 
        for block in text_blocks 
        for line in block.get("lines", [])
        for span in line.get("spans", [])
    )
    if len(total_text.strip()) < 200:
        signals["low_text_density"] = True
