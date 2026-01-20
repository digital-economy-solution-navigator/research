#!/usr/bin/env python3
"""
UNIDO Project Document Parser (Generalized Version)
Extracts 'Brief Description' and 'Challenges/Problem Statements' from UNIDO TC project documents.
Outputs the results to a JSON file.

Designed to handle ~1900 documents with varying structures.
NO CHARACTER LIMITS on extracted content.

Configuration:
    See config.py for FOLDER_SOURCE and CLOUD_BASE_PATH settings.
    - "local": uses "text" folder relative to script directory
    - "cloud": uses {CLOUD_BASE_PATH}/text folder
"""

import os
import re
import json
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import FOLDER_SOURCE, CLOUD_BASE_PATH


def extract_project_id(filename):
    """
    Extract project ID from filename.
    Files are typically named: {project_id}_{rest_of_name}.txt
    
    This matches the convention used in other scripts (download.py, check_missing_docs.py, etc.)
    """
    if isinstance(filename, Path):
        basename = filename.name
    else:
        basename = os.path.basename(filename)
    
    # Try to extract project ID from the beginning of filename (format: {project_id}_{rest})
    match = re.match(r'^(\d+)_', basename)
    if match:
        return match.group(1)
    
    # Fallback: try to extract numeric ID at the beginning (without underscore)
    match = re.match(r'^(\d+)', basename)
    if match:
        return match.group(1)
    
    # Last resort: try to find any numeric sequence in the filename
    match = re.search(r'(\d{5,})', basename)
    if match:
        return match.group(1)
    
    # Final fallback: use filename without extension
    return Path(basename).stem


def clean_text(text):
    """Clean extracted text by removing extra whitespace and page markers"""
    if not text:
        return None
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Remove page markers in various formats
    text = re.sub(r'\|\s*P\s*a\s*g\s*e\s*\d+', '', text)
    text = re.sub(r'\n\s*Page\s+\d+\s*\n', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'^\d{1,3}\s*$', '', text, flags=re.MULTILINE)
    # Remove form feed and other control characters
    text = re.sub(r'[\x0c]', '', text)
    # Remove multiple consecutive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text if text else None


def clean_double_letter_encoding(text):
    """
    Clean double-letter encoding artifacts from PDF extraction.
    E.g., "TThhee" -> "The", "pprroojjeecctt" -> "project", "mmmooonnnttthhhsss" -> "months"
    Also handles digits: "22000099" -> "2009" and punctuation: "(((NQP)))" -> "(NQP)"
    """
    if not text:
        return text
    
    # Pattern to detect double/triple-letter sequences
    # Check if text has significant repeated-letter encoding
    double_letter_count = len(re.findall(r'([A-Za-z])\1', text))
    triple_letter_count = len(re.findall(r'([A-Za-z])\1\1', text))
    total_letters = len(re.findall(r'[A-Za-z]', text))
    
    # If more than 20% of letter pairs are doubles/triples, likely encoded
    if total_letters > 20 and (double_letter_count + triple_letter_count * 2) / (total_letters / 2) > 0.2:
        # First handle triple characters (e.g., "mmm" -> "m", "(((" -> "(")
        result = re.sub(r'(.)\1\1', r'\1', text)
        # Then handle double characters (e.g., "TT" -> "T", "22" -> "2")
        result = re.sub(r'(.)\1', r'\1', result)
        return result
    
    return text


def extract_brief_description(content):
    """Extract the 'Brief description' section from the document - NO LENGTH LIMITS"""
    
    # ==========================================================================
    # PATTERN GROUP 1: Standard UNIDO "Brief description" format
    # ==========================================================================
    
    # List of end markers that indicate the end of brief description
    end_markers = [
        r'\n\s*Approved[:\s]',
        r'\n\s*TABLE\s+OF\s+CONTENTS',
        r'\n\s*INDEX\s*\n',
        r'\n\s*EXECUTIVE\s+SUMMARY',
        r'\n\s*On\s+behalf\s+of',
        r'\n\s*Signature[:\s]',
        r'\n\s*PART\s+[IV1-9]',
        r'\n\s*A\.\s+CONTEXT',
        r'\n\s*A\.1\s+',
        r'\n\s*B\.\s+',
        r'\n\s*1\.\s+[A-Z]',  # Numbered section start
        r'\n\s*ABBREVIATIONS',
        r'\n\s*LIST\s+OF\s+ABBREVIATIONS',
        r'\n\s*ACRONYMS',
        r'\n\s*Contents\s*\n',
    ]
    
    # Build combined end pattern
    end_pattern = '|'.join(end_markers)
    
    # Try to find "Brief description" section
    brief_patterns = [
        # Standard format with colon
        rf'Brief\s+description\s*[:\-]?\s*\n([\s\S]*?)(?={end_pattern})',
        # Without explicit markers, look for paragraph after "Brief description"
        rf'Brief\s+description\s*[:\-]?\s*\n([\s\S]+?)(?=\n\n\s*[A-Z][a-z]+[:\s]|\n\n\s*\d+\.\s)',
    ]
    
    for pattern in brief_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 50:  # Minimum sanity check only
                return cleaned
    
    # Fallback: get content after "Brief description" until a clear section break
    match = re.search(r'Brief\s+description\s*[:\-]?\s*\n([\s\S]+)', content, re.IGNORECASE)
    if match:
        text = match.group(1)
        # Try to find a natural break point
        break_patterns = [
            r'\n\s*Approved',
            r'\n\s*TABLE\s+OF',
            r'\n\s*INDEX\s*\n',
            r'\n\s*A\.\s',
            r'\n\s*PART\s+I',
            r'\n\s*_{5,}',  # Underline separators
            r'\n\s*-{5,}',  # Dash separators
        ]
        earliest_break = len(text)
        for bp in break_patterns:
            m = re.search(bp, text, re.IGNORECASE)
            if m and m.start() < earliest_break:
                earliest_break = m.start()
        
        if earliest_break > 50:
            return clean_text(text[:earliest_break])
    
    # ==========================================================================
    # PATTERN GROUP 2: GEF CEO Endorsement "Project Objective" format
    # ==========================================================================
    
    gef_patterns = [
        # "Project Objective:" followed by description
        r'Project\s+Objective\s*[:\-]\s*([\s\S]*?)(?=\n\s*(?:Trust|Grant|Project\s+Component|Expected|Type|\(select\)|[A-Z]\.\s+))',
        # Alternative: Project Objective in a table cell
        r'Project\s+Objective\s*[:\-]\s*([^\n]+(?:\n(?![A-Z\d]\.)[^\n]+)*)',
    ]
    
    for pattern in gef_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 20:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 3: Executive Summary as fallback
    # ==========================================================================
    
    exec_patterns = [
        r'EXECUTIVE\s+SUMMARY\s*\n([\s\S]*?)(?=\n\s*(?:PART\s+|[A-Z]\.\s+|\d+\.\s+[A-Z]|TABLE\s+OF\s+CONTENTS))',
        r'Executive\s+Summary\s*[:\n]([\s\S]*?)(?=\n\s*(?:\d+\.\s+|[A-Z]\.\s+|Introduction|Background))',
    ]
    
    for pattern in exec_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 4: Project Summary / Project Description
    # ==========================================================================
    
    summary_patterns = [
        r'Project\s+Summary\s*[:\-]?\s*\n([\s\S]*?)(?=\n\s*(?:[A-Z]\.\s+|\d+\.\s+[A-Z]|PART\s+))',
        r'Project\s+Description\s*[:\-]?\s*\n([\s\S]*?)(?=\n\s*(?:[A-Z]\.\s+|\d+\.\s+[A-Z]|PART\s+))',
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 50:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 5: UNDP Project Document format - "This project aims..."
    # ==========================================================================
    
    # Look for project summary paragraph starting with common phrases
    # Must be near the beginning of the document (within first 5000 chars)
    first_5000 = content[:5000]
    undp_patterns = [
        # "This project aims/seeks/is designed to..." - capture the paragraph
        r'((?:This|The)\s+project\s+(?:aims|seeks|is\s+designed|is\s+expected|will)\s+to[^.]+\.(?:[^.]+\.){0,5})',
        # After "Implementing Agency:" look for project description paragraph
        r'Implementing\s+(?:Agency|Partner)\s*:\s*[^\n]+\n\s*([A-Z][^.]+(?:project|programme|initiative)[^.]*\.(?:[^.]+\.){0,5})',
    ]
    
    for pattern in undp_patterns:
        match = re.search(pattern, first_5000, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 50 and len(cleaned) < 3000:  # Reasonable length
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 6: GEF PPG "Describe the PPG activities" format
    # ==========================================================================
    
    ppg_patterns = [
        # PPG activities and justifications
        r'Describe\s+the\s+PPG\s+activities\s+and\s+justifications\s*[:\-]?\s*([\s\S]*?)(?=\n\s*(?:List\s+of\s+Proposed|The\s+following\s+provides|Component\s+\d|[A-Z]\.\s+[A-Z]))',
        # Project title description in PPG
        r'PROJECT\s+TITLE\s*[:\-]\s*([^\n]+)',
    ]
    
    for pattern in ppg_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 50:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 7: Situation Analysis intro (fallback for UNDP docs)
    # ==========================================================================
    
    situation_intro = r'(?:I\.|1\.)\s*SITUATION\s+ANALYSIS\s*\n([\s\S]*?)(?=\n\s*(?:II\.|2\.|Economy|Energy|Agriculture|[A-Z][a-z]+\s*:))'
    match = re.search(situation_intro, content, re.IGNORECASE)
    if match:
        text = match.group(1)
        cleaned = clean_text(text)
        if cleaned and len(cleaned) > 100:
            return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 8: Abstract section (for project reports/brochures)
    # ==========================================================================
    
    abstract_patterns = [
        r'\n\s*Abstract\s*\n([\s\S]*?)(?=\n\s*(?:Content|Table\s+of\s+Contents|Introduction|\d+\s+[A-Z]|[A-Z]+\s+[A-Z]+:))',
        r'\n\s*ABSTRACT\s*\n([\s\S]*?)(?=\n\s*(?:CONTENT|TABLE\s+OF|INTRODUCTION|\d+\s+[A-Z]))',
    ]
    
    for pattern in abstract_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 9: Program Vision and Mission / Program Objectives
    # ==========================================================================
    
    program_patterns = [
        # Program Vision and Mission section
        r'Program\s+Vision\s+and\s+Mission\s*\n([\s\S]*?)(?=\n\s*(?:Program\s+Objectives|The\s+\dADI|[A-Z][a-z]+\s+Objectives|\d+\s*\n))',
        # Program Objectives section
        r'Program\s+Objectives(?:\s+and\s+Expected\s+Impact)?\s*\n([\s\S]*?)(?=\n\s*(?:For\s+the\s+|Support\s+to|I\.\s+Problem|Table\s+\d))',
    ]
    
    for pattern in program_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 10: Country Programme Framework intro paragraph
    # ==========================================================================
    
    cpf_patterns = [
        # Country Programme Framework intro - typically right after title, before signatures
        r'COUNTRY\s+PROGRAMME\s+(?:FRAMEWORK|FOR)\s+[^\n]+\n(?:for\s+[^\n]+\n)?(?:INCLUSIVE[^\n]+\n)?(?:\d{4}[^\n]*\n)?([\s\S]*?)(?=\n\s*_{5,}|\n\s*[A-Z][a-z]+\s+[A-Z][a-z]+\s*\n\s*Director)',
        # Alternative: The [Country] Country Programme Framework... paragraph
        r'(The\s+[A-Z][a-z]+\s+Country\s+Programme\s+Framework[^.]+\.(?:[^.]+\.){1,10})',
    ]
    
    for pattern in cpf_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100 and len(cleaned) < 5000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 11: Value Chain / Support Program description
    # ==========================================================================
    
    vc_patterns = [
        # Value Chain Support Program intro
        r'(?:Value\s+Chain|Support\s+Program)[^\n]*\n(?:Prospective[^\n]*\n)?([\s\S]*?)(?=\n\s*(?:Contents|Table\s+of\s+Contents|Acronyms|\d+\s*\n))',
        # Country Context as description
        r'Country\s+Context\s*\n([\s\S]*?)(?=\n\s*(?:The\s+\dADI|Contents|Acronyms|Tables\s+and))',
    ]
    
    for pattern in vc_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100 and len(cleaned) < 5000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 12: One Programme / UN Programme Objective
    # ==========================================================================
    
    one_programme_patterns = [
        # "1 Objective of the One Programme" or similar numbered objective
        r'\d+\s+Objective\s+of\s+the\s+(?:One\s+)?Programme\s*\n([\s\S]*?)(?=\n\s*\d+\s+(?:One\s+)?Programme\s+Structure|\n\s*\d+\.\d+|\n\s*2\s+[A-Z])',
        # "Objective of the Programme" without number
        r'Objective\s+of\s+the\s+(?:One\s+)?Programme\s*\n([\s\S]*?)(?=\n\s*(?:Programme\s+Structure|\d+\.\d+|\d+\s+[A-Z]))',
        # Generic "Programme Objective" section
        r'Programme\s+Objective[s]?\s*\n([\s\S]*?)(?=\n\s*(?:\d+\s+[A-Z]|\d+\.\d+|Programme\s+Structure))',
    ]
    
    for pattern in one_programme_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 50 and len(cleaned) < 5000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 13: Meeting Report / Committee Report Introduction
    # ==========================================================================
    
    meeting_report_patterns = [
        # "Introduction" section with numbered paragraphs (like ExCom reports)
        r'\n\s*Introduction\s*\n((?:\d+\.\s+[\s\S]*?)(?=\n\s*AGENDA\s+ITEM|\n\s*[A-Z]+\s+ITEM|\n\s*\d+\.\s+[A-Z][a-z]+\s+of))',
        # "REPORT OF THE..." followed by Introduction
        r'REPORT\s+OF\s+THE\s+[^\n]+\n\s*Introduction\s*\n([\s\S]*?)(?=\n\s*AGENDA\s+ITEM)',
        # Generic Introduction for reports
        r'\n\s*Introduction\s*\n([\s\S]*?)(?=\n\s*(?:AGENDA|Contents|Table\s+of|I\.\s+|1\.\s+[A-Z][a-z]+\s+[a-z]))',
    ]
    
    for pattern in meeting_report_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100 and len(cleaned) < 10000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 14: Short description field (PRODOC format)
    # ==========================================================================
    
    short_desc_patterns = [
        # "The overall objective" paragraph (common in PRODOC header tables)
        r'Total\s+budget[^\n]*\n(The\s+overall\s+objective[\s\S]*?)(?=\n\s*(?:\d+\s*\n\s*Project|\n\s*Contents|[A-Z]\.\s+[A-Z]))',
        # "Short description" field in project header
        r'Short\s+description\s*\n?([\s\S]*?)(?=\n\s*(?:Contents|Table\s+of|[A-Z]\.\s+[A-Z]|\d+\s*\n\s*Project))',
        # Alternative: Short description followed by section
        r'Short\s+description\s*[:\n]\s*([\s\S]*?)(?=\n\s*(?:[A-Z]\.\s+[A-Z]|Contents|Background))',
    ]
    
    for pattern in short_desc_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            # Clean up table formatting artifacts like "Short description" in the middle
            text = re.sub(r'\n\s*Short\s+description\s*\n', '\n', text, flags=re.IGNORECASE)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 50 and len(cleaned) < 5000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 15: Project Purpose / A1. Project Purpose (PRODOC format)
    # ==========================================================================
    
    project_purpose_patterns = [
        # "A1. Project Purpose" or "A.1 Project Purpose"
        r'A\.?\s*1\.?\s*Project\s+Purpose\s*\n([\s\S]*?)(?=\n\s*(?:A\.?\s*2|Figure\s+\d|The\s+project\s+will|The\s+main\s+rationale))',
        # "Project Purpose" standalone
        r'\n\s*Project\s+Purpose\s*\n([\s\S]*?)(?=\n\s*(?:[A-Z]\.?\s*\d|Figure|Table|The\s+project))',
    ]
    
    for pattern in project_purpose_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100 and len(cleaned) < 10000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 16: PROJECT DESCRIPTION section (ExCom project proposals)
    # ==========================================================================
    
    project_desc_patterns = [
        # "PROJECT DESCRIPTION" followed by "Background"
        r'PROJECT\s+DESCRIPTION\s*\n\s*(?:Background\s*\n)?([\s\S]*?)(?=\n\s*(?:SECRETARIAT|PROJECT\s+EVALUATION|[A-Z]+\s+COSTS|\d+\.\s+On\s+behalf))',
        # Generic PROJECT DESCRIPTION
        r'PROJECT\s+DESCRIPTION\s*\n([\s\S]*?)(?=\n\s*(?:[A-Z]{2,}\s+[A-Z]|Table\s+\d|\d+\s*\n\s*[A-Z]))',
    ]
    
    for pattern in project_desc_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100 and len(cleaned) < 15000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 17: Work Programme / Work Plan intro (internal documents)
    # ==========================================================================
    
    work_plan_patterns = [
        # "A. Work Programme and Budget" section with intro paragraph
        r'A\.\s*Work\s+Programme\s+and\s+Budget[^\n]*\n([\s\S]*?)(?=\n\s*(?:This\s+work\s+plan|B\.\s+Planned|The\s+GS\s+inter))',
        # Work Programme intro paragraph after title - capture "Advancing gender equality..." type intros
        r'(?:2020\s*[-–]\s*2023|Implementation[^\n]*)\s*\n\s*A\.\s*Work\s+Programme[^\n]*\n(Advancing[\s\S]*?)(?=\n\s*(?:This\s+work\s+programme|The\s+GS))',
        # Generic work plan intro - paragraphs starting with organizational description
        r'Work\s+Programme\s+and\s+Budget[^\n]*\n(?:\d{4}[^\n]*\n)?(?:for[^\n]*\n)?([\s\S]*?)(?=\n\s*(?:This\s+work\s+programme|B\.\s+|Table\s+of|Contents))',
    ]
    
    for pattern in work_plan_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100 and len(cleaned) < 5000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 18: A. INTRODUCTION section (evaluation/audit work plans)
    # ==========================================================================
    
    intro_section_patterns = [
        # "A. INTRODUCTION" with numbered paragraphs
        r'A\.\s*INTRODUCTION\s*\n([\s\S]*?)(?=\n\s*B\.\s+[A-Z])',
        # Generic lettered Introduction section
        r'[A-Z]\.\s*INTRODUCTION\s*\n([\s\S]*?)(?=\n\s*[A-Z]\.\s+[A-Z])',
    ]
    
    for pattern in intro_section_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100 and len(cleaned) < 10000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 19: Objectives of the action (EU Grant format) - check BEFORE SUMMARY
    # ==========================================================================
    
    objectives_patterns = [
        # "Objectives of the action" in grant forms - capture until Target group
        r'Objectives?\s+of\s+the\s+action\s*\n([\s\S]*?)(?=\n\s*Target\s+group)',
    ]
    
    for pattern in objectives_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 50 and len(cleaned) < 3000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 20: SUMMARY section (standalone or numbered)
    # ==========================================================================
    
    summary_section_patterns = [
        # Standalone "SUMMARY" section (NOT "SUMMARY OF THE ACTION" which is a table format)
        r'\n\s*SUMMARY\s*\n([\s\S]*?)(?=\n\s*(?:The\s+proposed|More\s+precisely|Prior\s+to|\d+\.\s+[A-Z]|[A-Z]\.\s+[A-Z]|Table\s+of))',
        # Summary followed by project description
        r'\n\s*Summary\s*[:\n]\s*([\s\S]*?)(?=\n\s*(?:\d+\.\s+|[A-Z]\.\s+|Table\s+of|Contents))',
    ]
    
    for pattern in summary_section_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100 and len(cleaned) < 10000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 20: "The application relates to:" pattern
    # ==========================================================================
    
    application_patterns = [
        r'The\s+application\s+relates\s+to\s*[:\n]\s*([\s\S]*?)(?=\n\s*(?:Location|Total\s+calculated|Timeframe|Previous))',
    ]
    
    for pattern in application_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 50 and len(cleaned) < 3000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 21: Brief description field in header table (ONLY in first 6000 chars)
    # ==========================================================================
    
    # Only search in first 6000 chars to avoid matching "brief description" phrases elsewhere
    header_content = content[:6000]
    brief_field_patterns = [
        # "Brief description:" field - capture multiline content until "Approved" or page number
        r'Brief\s+description\s*:\s*([\s\S]*?)(?=\n\s*(?:\d+\s*\n\s*\n|Approved\s*:|Page\s+\d))',
    ]
    
    for pattern in brief_field_patterns:
        match = re.search(pattern, header_content, re.IGNORECASE)
        if match:
            text = match.group(1)
            # Clean double-letter encoding (e.g., "TThhee" -> "The")
            text = clean_double_letter_encoding(text)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100 and len(cleaned) < 10000:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 22: Preamble before Table of Contents (UNIDO project docs)
    # ==========================================================================
    
    preamble_patterns = [
        # Content between "In-kind" and "Approved:" - common UNIDO PRODOC format
        r'(?:In-kind|Counterpart\s+inputs\s+In-kind)[^\n]*\n(Since[\s\S]*?)(?=\n\s*Approved\s*:)',
        # Content starting with "Since the signing" before Approved
        r'\n(Since\s+the\s+signing[\s\S]*?)(?=\n\s*Approved\s*:)',
        # Content between header info and Approved/Table of Contents
        r'(?:Executing\s+agency|UNIDO\s+inputs)[^\n]*\n([\s\S]*?)(?=\n\s*(?:Table\s+of\s+Contents|Contents\s*\n|Approved\s*:))',
    ]
    
    for pattern in preamble_patterns:
        match = re.search(pattern, content[:5000], re.IGNORECASE)  # Only search first 5000 chars
        if match:
            text = match.group(1)
            # Skip if it's just signature blocks or too short
            if len(text) > 200 and not re.search(r'^[\s\n]*Signature|^[\s\n]*On\s+behalf', text[:100]):
                cleaned = clean_text(text)
                if cleaned and len(cleaned) > 100 and len(cleaned) < 5000:
                    return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 23: Service Summary Sheet / Origin of proposal
    # ==========================================================================
    
    service_summary_patterns = [
        # "Origin of proposal:" section
        r'Origin\s+of\s+proposal\s*[:\n]\s*([\s\S]*?)(?=\n\s*(?:Problem|Research\s+issue|Objective|Expected))',
        # Service Summary Sheet intro after title
        r'Service\s+Summary\s+Sheet\s*\n(?:[^\n]*\n){1,5}([\s\S]*?)(?=\n\s*(?:Problem|SSS-|Page\s+\d))',
    ]
    
    for pattern in service_summary_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 50 and len(cleaned) < 5000:
                return cleaned
    
    return None


def extract_challenges(content):
    """
    Extract the 'Challenges/Problems' section from the document.
    UPDATED VERSION with additional patterns based on document analysis.
    NO CHARACTER LIMITS applied.
    """
    
    results = []
    
    # ==========================================================================
    # PATTERN GROUP 0: GEF CEO Endorsement specific sections (highest priority)
    # ==========================================================================
    
    gef_problem_patterns = [
        r'A\.?\s*4\.?\s*(?:The\s+)?baseline\s+project\s+and\s+(?:the\s+)?problem(?:\s+that\s+it\s+seeks\s+to\s+address)?',
        r'A\.?\s*\d+\.?\s*(?:The\s+)?problem(?:\s+that\s+it\s+seeks)?\s+to\s+(?:be\s+)?address',
    ]
    
    for pattern in gef_problem_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            start = match.end()
            end_match = re.search(r'\n\s*(?:A\.?\s*[5-9]|B\.?\s+[A-Z]|C\.?\s+)', content[start:], re.IGNORECASE)
            if end_match:
                section_text = content[start:start + end_match.start()]
            else:
                section_text = content[start:start + 30000]
            
            if len(section_text) > 200:
                cleaned = clean_text(section_text)
                if cleaned and len(cleaned) > 100:
                    results.append(cleaned)
    
    # ==========================================================================
    # NEW PATTERN: "Barriers" section with numbered barriers (GEF PIF format)
    # Example: "Barrier #1: Limited knowledge..."
    # ==========================================================================
    
    barriers_header_pattern = r'\n\s*Barriers?\s*\n'
    match = re.search(barriers_header_pattern, content, re.IGNORECASE)
    if match:
        start = match.start()
        # Find end - next major section like "2)", numbered section, or lettered section
        end_match = re.search(r'\n\s*(?:\d+\)\s+[A-Z]|[A-Z]\.\s+[A-Z]|Component\s+\d)', content[match.end():], re.IGNORECASE)
        if end_match:
            section_text = content[start:match.end() + end_match.start()]
        else:
            section_text = content[start:start + 20000]
        
        if len(section_text) > 100:
            cleaned = clean_text(section_text)
            if cleaned:
                results.append(cleaned)
    
    # Also look for inline "Barrier #N:" patterns
    barrier_numbered_pattern = r'(Barrier\s*#?\s*\d+\s*[:\-][^\n]+(?:\n(?!Barrier\s*#?\s*\d+)[^\n]+)*)'
    barrier_matches = re.findall(barrier_numbered_pattern, content, re.IGNORECASE)
    if barrier_matches and not results:
        combined_barriers = '\n\n'.join(barrier_matches)
        if len(combined_barriers) > 100:
            results.append(clean_text(combined_barriers))
    
    if results:
        seen = set()
        unique_results = []
        for r in results:
            if r:
                key = r[:100] if len(r) > 100 else r
                if key not in seen:
                    seen.add(key)
                    unique_results.append(r)
        if unique_results:
            return '\n\n---\n\n'.join(unique_results) if len(unique_results) > 1 else unique_results[0]
    
    results = []
    
    # ==========================================================================
    # NEW PATTERN: "Problem to be addressed:" (standalone, like in 140337)
    # ==========================================================================
    
    problem_standalone_patterns = [
        r'Problem(?:s)?\s+to\s+be\s+addressed\s*[:\-]\s*\n([\s\S]*?)(?=\n\s*(?:Background|Expected\s+target|Counterpart|Project\s+purpose|[A-Z]\.\s+[A-Z]))',
        r'Problem(?:s)?\s+to\s+be\s+addressed\s*[:\-]\s*\n([\s\S]*?)(?=\n\n[A-Z][a-z]+\s*\n)',
    ]
    
    for pattern in problem_standalone_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                return cleaned
    
    # ==========================================================================
    # NEW PATTERN: "THEREFORE, THE PROBLEMS TO BE ADDRESSED ARE:" (like 140016)
    # ==========================================================================
    
    therefore_pattern = r'THEREFORE,?\s+THE\s+PROBLEMS?\s+TO\s+BE\s+ADDRESSED\s+(?:ARE|IS)\s*[:\-]?\s*\n([\s\S]*?)(?=\n\s*(?:In\s+order\s+to|In\s+this\s+context|UNIDO|[A-Z]\.\s+[A-Z]))'
    match = re.search(therefore_pattern, content, re.IGNORECASE)
    if match:
        text = match.group(1)
        cleaned = clean_text(text)
        if cleaned and len(cleaned) > 100:
            return cleaned
    
    # ==========================================================================
    # NEW PATTERN: "B.1 Problems to be addressed" (like 101091)
    # ==========================================================================
    
    b1_problems_patterns = [
        r'B\.?\s*1\.?\s*Problems?\s+to\s+be\s+addressed\s*\n([\s\S]*?)(?=\n\s*(?:B\.?\s*2|B\.?\s*\d+\.?\s*Expected|C\.?\s+|There\s+is\s+an\s+urgent))',
        r'B\.?\s*1\.?\s*Problems?\s+to\s+be\s+addressed\s*\n([\s\S]*?)(?=\n\s*B\.?\s*\d+)',
    ]
    
    for pattern in b1_problems_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                return cleaned
    
    # ==========================================================================
    # NEW PATTERN: "A.1. Problems to be addressed" (like 140226)
    # ==========================================================================
    
    a1_problems_patterns = [
        r'A\.?\s*1\.?\s*Problems?\s+to\s+be\s+addressed\s*\n([\s\S]*?)(?=\n\s*(?:A\.?\s*2|Map\s+of|Damage\s+caused|[A-Z][a-z]+\s+of\s+[A-Z]))',
        r'A\.?\s*1\.?\s*Problems?\s+to\s+be\s+addressed\s*\n([\s\S]*?)(?=\n\s*A\.?\s*\d+)',
    ]
    
    for pattern in a1_problems_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 0.5: GEF PIF "B.1. Describe the baseline project and the problem"
    # ==========================================================================
    
    pif_problem_patterns = [
        r'B\.?\s*1\.?\s*(?:Describe\s+the\s+)?baseline\s+(?:project\s+and\s+(?:the\s+)?)?problem(?:\s+that\s+it\s+seeks\s+to\s+address)?',
        r'B\.?\s*1\.?\s*Describe\s+the\s+baseline\s+project',
    ]
    
    for pattern in pif_problem_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            start = match.end()
            end_match = re.search(r'\n\s*(?:B\.?\s*[2-9]|C\.?\s+|PART\s+)', content[start:], re.IGNORECASE)
            if end_match:
                section_text = content[start:start + end_match.start()]
            else:
                section_text = content[start:start + 30000]
            
            if len(section_text) > 200:
                cleaned = clean_text(section_text)
                if cleaned and len(cleaned) > 100:
                    results.append(cleaned)
    
    if results:
        if len(results) == 1:
            return results[0]
        else:
            return '\n\n---\n\n'.join(results)
    
    # ==========================================================================
    # PATTERN GROUP 1: Explicit "CHALLENGES TO BE ADDRESSED" sections (UNIDO format)
    # ==========================================================================
    
    a2_patterns = [
        r'A\.?\s*2\.?\s*(?:THEMATIC\s+CONTEXT[:\s]*)?CHALLENGES\s+TO\s+BE\s+ADDRESSED',
        r'A\.?\s*2\.?\s*(?:GLOBAL\s+)?(?:CURRENT\s+)?SITUATION\s+AND\s+PROBLEMS?/?CHALLENGES?',
        r'A\.?\s*2\.?\s*PROBLEMS?\s+(?:AND\s+)?CHALLENGES?',
        r'A\.?\s*2\.?\s*Problems?\s+to\s+be\s+addressed',
    ]
    
    for pattern in a2_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            start = match.end()
            end_match = re.search(r'\n\s*(?:A\.?\s*3\s|B\.?\s+[A-Z]|C\.?\s+[A-Z]|PART\s+)', content[start:], re.IGNORECASE)
            if end_match:
                section_text = content[start:start + end_match.start()]
            else:
                section_text = content[start:start + 50000]
            
            if len(section_text) > 300 and re.search(r'\.\s+[A-Z]', section_text):
                cleaned = clean_text(section_text)
                if cleaned and len(cleaned) > 100:
                    results.append(cleaned)
    
    if results:
        if len(results) == 1:
            return results[0]
        else:
            return '\n\n---\n\n'.join(results)
    
    # ==========================================================================
    # NEW PATTERN: Situation Analysis section with problem keywords
    # ==========================================================================
    
    situation_analysis_patterns = [
        # Look for "Situation Analysis" followed by problem-related content
        r'(?:\d+\.?\s*)?Situation\s+Analysis\s*\n([\s\S]*?)(?=\n\s*(?:\d+\.?\s*[A-Z][a-z]+\s+[A-Z]|NDS\s+and|Assessment\s+of|[A-Z]\.\s+[A-Z]))',
    ]
    
    for pattern in situation_analysis_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            # Only include if it contains problem-related keywords
            if re.search(r'unemploy|poverty|constraint|challenge|problem|crisis|lack\s+of|deficit|obstacle', text, re.IGNORECASE):
                cleaned = clean_text(text)
                if cleaned and len(cleaned) > 200:
                    return cleaned
    
    # ==========================================================================
    # NEW PATTERN: Background section describing crisis/problems (like 110031)
    # ==========================================================================
    
    background_crisis_patterns = [
        # Background sections that describe war/crisis/damage - capture if it has keywords
        r'(?:A\.?\s*)?Background\s*\n([\s\S]*?)(?=\n\s*(?:B\.?\s+|C\.?\s+|Objectives?\s*\n|\d+\.\s+[A-Z]))',
    ]
    
    for pattern in background_crisis_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            # Only include if it mentions crisis/problems/challenges/destruction
            if re.search(r'civil\s+war|crisis|destroy|devastat|lack\s+of|shortage|inadequate|insufficient|gap\s+in|problem|challenge|constrain', text, re.IGNORECASE):
                cleaned = clean_text(text)
                if cleaned and len(cleaned) > 200 and len(cleaned) < 10000:
                    return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 1.5: SITUATION ANALYSIS with challenges (UNDP format)
    # ==========================================================================
    
    situation_patterns = [
        r'(?:main|major|key)\s+(?:socio-economic\s+)?challenges\s+(?:facing|include|are)[:\s]*([\s\S]*?)(?=\n\s*(?:II\.|2\.|To\s+alleviate|In\s+response|The\s+project))',
        r'Barriers?\s+(?:for|to)\s+(?:effective\s+)?[^\n]+\n([\s\S]*?)(?=\n\s*(?:II\.|2\.|[A-Z]\.\s+|The\s+project))',
    ]
    
    for pattern in situation_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            text = match.group(0) if '(' not in pattern[:20] else match.group(0)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                results.append(cleaned)
    
    if results:
        if len(results) == 1:
            return results[0]
        else:
            return '\n\n---\n\n'.join(results)
    
    # ==========================================================================
    # PATTERN GROUP 1.6: Numbered "Challenges to be addressed" section
    # ==========================================================================
    
    numbered_challenges_patterns = [
        r'\d+\.?\s*\d*\.?\s*Challenges?\s+to\s+be\s+addressed\s*\n([\s\S]*?)(?=\n\s*(?:\d+\.?\s*\d*\.?\s*[A-Z][a-z]+|[A-Z]\.\s+|\d+\.0\s+))',
        r'Challenges?\s+to\s+be\s+addressed\s*\n([\s\S]*?)(?=\n\s*(?:\d+\.\s*[A-Z]|[A-Z]\.\s+|II\.|2\.))',
    ]
    
    for pattern in numbered_challenges_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            text = match.group(1)
            if len(text) > 200:
                cleaned = clean_text(text)
                if cleaned and len(cleaned) > 100:
                    results.append(cleaned)
    
    if results:
        if len(results) == 1:
            return results[0]
        else:
            return '\n\n---\n\n'.join(results)
    
    # ==========================================================================
    # NEW PATTERN: "Key constraints" or "Main constraints" sections
    # ==========================================================================
    
    constraints_patterns = [
        r'(?:key|main|major)\s+constraints?\s+(?:include|are|facing)[:\s]*([\s\S]*?)(?=\n\s*(?:In\s+the\s+case|The\s+lack|[A-Z]\.\s+[A-Z]))',
        r'constraints?\s+(?:that\s+)?(?:seriously\s+)?(?:inhibit|limit|hinder)[^\n]*\n([\s\S]*?)(?=\n\s*(?:In\s+the\s+case|[A-Z]\.\s+[A-Z]|\d+\.\s+[A-Z]))',
    ]
    
    for pattern in constraints_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(0)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 1.7: Numbered "Challenges to [Topic]"
    # ==========================================================================
    
    numbered_topic_challenges_patterns = [
        r'\d+\.?\s*Challenges?\s+to\s+[^\n]+\n([\s\S]*?)(?=\n\s*(?:\d+\.?\s*(?:Problem|Objective|Expected|Project)|[A-Z]\.\s+))',
        r'\d+\.?\s*Problem\s+Statement\s*\n([\s\S]*?)(?=\n\s*(?:\d+\.?\s*[A-Z]|[A-Z]\.\s+))',
    ]
    
    for pattern in numbered_topic_challenges_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            text = match.group(1)
            if len(text) > 100:
                cleaned = clean_text(text)
                if cleaned and len(cleaned) > 50:
                    results.append(cleaned)
    
    if results:
        if len(results) == 1:
            return results[0]
        else:
            return '\n\n---\n\n'.join(results)
    
    # ==========================================================================
    # PATTERN GROUP 2: Standalone "CHALLENGES TO BE ADDRESSED" header
    # ==========================================================================
    
    standalone_pattern = r'\n\s*CHALLENGES?\s+TO\s+BE\s+ADDRESSED\s*\n'
    matches = list(re.finditer(standalone_pattern, content, re.IGNORECASE))
    for match in matches:
        start = match.end()
        end_match = re.search(r'\n\s*(?:[A-Z]\.?\s*\d|\d+\.\s+[A-Z]|[IVX]+\.\s+|PART\s+)', content[start:], re.IGNORECASE)
        if end_match:
            section_text = content[start:start + end_match.start()]
        else:
            section_text = content[start:start + 30000]
        
        if len(section_text) > 200 and re.search(r'\.\s+[A-Z]', section_text):
            cleaned = clean_text(section_text)
            if cleaned and len(cleaned) > 100:
                results.append(cleaned)
    
    if results:
        if len(results) == 1:
            return results[0]
        else:
            return '\n\n---\n\n'.join(results)
    
    # ==========================================================================
    # PATTERN GROUP 3: Problem statement sections
    # ==========================================================================
    
    problem_patterns = [
        r'\n\s*(?:Problem|Issue)s?\s+(?:Statement|Analysis|Description|Identification)\s*\n',
        r'\n\s*(?:Key\s+)?(?:Problems?|Issues?)\s+(?:to\s+be\s+)?(?:Addressed|Identified|Tackled)\s*\n',
        r'\n\s*(?:Main|Major|Key)\s+(?:Problems?|Challenges?|Issues?|Constraints?)\s*\n',
        r'\n\s*(?:Development\s+)?(?:Problem|Challenge)\s+(?:Analysis|Statement)\s*\n',
        r'\n\s*[IVX]+\.?\s*Problem\s+Statement\s*\n',
    ]
    
    for pattern in problem_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            start = match.end()
            end_match = re.search(r'\n\s*(?:[A-Z]\.?\s*\d|\d+\.\s+[A-Z]|[IVX]+\.\s+|II\.\s+|III\.\s+)', content[start:], re.IGNORECASE)
            if end_match:
                section_text = content[start:start + end_match.start()]
            else:
                section_text = content[start:start + 20000]
            
            if len(section_text) > 100:
                cleaned = clean_text(section_text)
                if cleaned:
                    results.append(cleaned)
    
    if results:
        if len(results) == 1:
            return results[0]
        else:
            return '\n\n---\n\n'.join(results)
    
    # ==========================================================================
    # PATTERN GROUP 4: Context sections with explicit challenge lists
    # ==========================================================================
    
    context_patterns = [
        r'(?:challenges?\s+facing\s+the\s+(?:industrial|manufacturing|SME|country)|challenges?\s+include\s*[:\n])',
        r'(?:key|main|major)\s+(?:challenges?|problems?|constraints?|issues?)\s+(?:include|are|identified)\s*[:\n]',
        r'(?:industries?|sector|enterprises?|SMEs?)\s+face\s+(?:the\s+following\s+)?(?:major\s+)?(?:challenges?|problems?)',
    ]
    
    for pattern in context_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            para_start = max(0, content.rfind('\n\n', 0, match.start()) + 2)
            search_start = match.end()
            
            bullet_content = re.search(r'((?:\s*[•\-\*\►\●]\s*[^\n]+\n?)+)', content[search_start:search_start + 5000])
            numbered_content = re.search(r'((?:\s*\d+[\.\)]\s*[^\n]+\n?)+)', content[search_start:search_start + 5000])
            
            if bullet_content:
                end = search_start + bullet_content.end()
            elif numbered_content:
                end = search_start + numbered_content.end()
            else:
                end_match = re.search(r'\n\n\s*(?:\d+\.\s+[A-Z]|[A-Z][a-z]+\s+[A-Z])', content[search_start:])
                if end_match:
                    end = search_start + end_match.start()
                else:
                    end = min(len(content), search_start + 5000)
            
            section_text = content[para_start:end]
            if len(section_text) > 100:
                cleaned = clean_text(section_text)
                if cleaned:
                    results.append(cleaned)
    
    if results:
        seen = set()
        unique_results = []
        for r in results:
            key = r[:100] if len(r) > 100 else r
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        if len(unique_results) == 1:
            return unique_results[0]
        else:
            return '\n\n---\n\n'.join(unique_results)
    
    # ==========================================================================
    # PATTERN GROUP 5: Bullet-point challenges (anywhere in document)
    # ==========================================================================
    
    bullet_patterns = [
        r'(?:challenges?|problems?|constraints?|issues?)\s*(?:include|are|facing)?[:\s]*\n((?:\s*[•\-\*\►\●]\s*[^\n]+\n?){2,})',
        r'(?:the\s+following|these)\s+(?:challenges?|problems?|issues?)[:\s]*\n((?:\s*[•\-\*\►\●\d]+[\.\)]\s*[^\n]+\n?){2,})',
    ]
    
    for pattern in bullet_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            cleaned = clean_text(match.group(0))
            if cleaned and len(cleaned) > 50:
                results.append(cleaned)
    
    if results:
        seen = set()
        unique_results = []
        for r in results:
            key = r[:100] if len(r) > 100 else r
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        if len(unique_results) == 1:
            return unique_results[0]
        else:
            return '\n\n---\n\n'.join(unique_results)
    
    # ==========================================================================
    # PATTERN GROUP 6: A. CONTEXT section with problem description
    # ==========================================================================
    
    context_section_patterns = [
        r'A\.?\s*CONTEXT\s*\n([\s\S]*?)(?=\n\s*(?:B\.?\s+|II\.|2\.\s+[A-Z]))',
    ]
    
    for pattern in context_section_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            if re.search(r'problem|challeng|threat|risk|pollut|contamin|danger|hazard', text, re.IGNORECASE):
                cleaned = clean_text(text)
                if cleaned and len(cleaned) > 200:
                    return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 7: THE DEVELOPMENT CHALLENGE section
    # ==========================================================================
    
    dev_challenge_patterns = [
        r'\d+\s+(?:THE\s+)?DEVELOPMENT\s+CHALLENGE[:\s]*\n(?:[^\n]+\n)?([\s\S]*?)(?=\n\s*(?:\d+\s+[A-Z]|[A-Z]\.\s+|PART\s+))',
        r'DEVELOPMENT\s+CHALLENGE[:\s]*\n([\s\S]*?)(?=\n\s*(?:\d+\s+[A-Z]|[A-Z]\.\s+|Value\s+Chain))',
    ]
    
    for pattern in dev_challenge_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                return cleaned
    
    # ==========================================================================
    # NEW PATTERN: "REASONS FOR UNIDO ASSISTANCE" often contains problems
    # ==========================================================================
    
    reasons_patterns = [
        r'(?:B\.?\s*)?REASONS?\s+FOR\s+UNIDO\s+ASSISTANCE\s*\n([\s\S]*?)(?=\n\s*(?:C\.?\s+|D\.?\s+|[A-Z]\.\s+THE\s+PROJECT))',
    ]
    
    for pattern in reasons_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            # Only include if it contains problem-related keywords
            if re.search(r'lack\s+of|problem|challenge|constraint|need\s+to|urgent|limited|inadequate', text, re.IGNORECASE):
                cleaned = clean_text(text)
                if cleaned and len(cleaned) > 200:
                    return cleaned
    
    return None


def extract_all_challenges_sections(content):
    """
    Fallback: Extract any sections that might contain challenge information.
    NO CHARACTER LIMITS.
    """
    challenges = []
    
    # Look for numbered subsections under A.2
    subsection_pattern = r'(A\.?\s*2\.?\s*\d+[^\n]*\n[\s\S]*?)(?=\nA\.?\s*2\.?\s*\d+|\nA\.?\s*3|\nB\.)'
    matches = re.finditer(subsection_pattern, content, re.IGNORECASE)
    for match in matches:
        text = match.group(1)
        # Check if it contains challenge-related keywords
        if re.search(r'challeng|problem|constraint|difficult|impediment|obstacle|issue|barrier', text, re.IGNORECASE):
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                challenges.append(cleaned)
    
    # Also look for any paragraph containing challenge keywords
    if not challenges:
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if re.search(r'(?:key|main|major)\s+(?:challenges?|problems?|constraints?)', para, re.IGNORECASE):
                cleaned = clean_text(para)
                if cleaned and len(cleaned) > 100:
                    challenges.append(cleaned)
    
    if challenges:
        return '\n\n'.join(challenges)
    return None


def process_document(filepath):
    """
    Process a single document and extract required information.
    
    Args:
        filepath: Path object or string path to the text file
    
    Returns:
        Dictionary with project_id, brief_description, challenges_problem_statements, and optional error
    """
    # Convert to Path if needed
    if isinstance(filepath, str):
        filepath = Path(filepath)
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return {
            'project_id': extract_project_id(filepath),
            'brief_description': None,
            'challenges_problem_statements': None,
            'error': f"Failed to read file: {str(e)}"
        }
    
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    project_id = extract_project_id(filepath)
    brief_description = extract_brief_description(content)
    
    # Try multiple approaches for challenges
    challenges = extract_challenges(content)
    if not challenges:
        challenges = extract_all_challenges_sections(content)
    
    return {
        'project_id': project_id,
        'brief_description': brief_description,
        'challenges_problem_statements': challenges
    }


def main():
    """
    Main function to process all documents.
    
    Uses config.py settings for default paths:
    - FOLDER_SOURCE: "local" or "cloud"
    - CLOUD_BASE_PATH: base path for cloud folders (when FOLDER_SOURCE="cloud")
    """
    import argparse
    
    # Get script directory for default paths
    script_dir = Path(__file__).parent.absolute()
    
    # Determine default text folder based on FOLDER_SOURCE
    if FOLDER_SOURCE == "cloud":
        default_text_dir = Path(CLOUD_BASE_PATH) / "text"
    else:  # local
        default_text_dir = script_dir
    
    # Default output file is in the docs directory (parent of text)
    default_output_file = script_dir.parent / "project_info.json"
    
    parser = argparse.ArgumentParser(
        description='Extract project info from UNIDO TC documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Process all txt files in default text folder (uses config.py settings)
  python docs/text/extract_project_info.py
  
  # Process files from a specific directory
  python docs/text/extract_project_info.py --input-dir /path/to/text/files
  
  # Specify custom output file
  python docs/text/extract_project_info.py --output-file /path/to/output.json
  
  # Verbose mode (show details for each file)
  python docs/text/extract_project_info.py --verbose
        """
    )
    
    parser.add_argument('--input-dir', '-i', 
                        default=str(default_text_dir),
                        help=f'Input directory containing .txt files (default: {default_text_dir})')
    parser.add_argument('--output-file', '-o', 
                        default=str(default_output_file),
                        help=f'Output JSON file path (default: {default_output_file})')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print detailed progress for each file')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_file = Path(args.output_file)
    verbose = args.verbose
    
    # Validate input directory
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        return
    
    if not input_dir.is_dir():
        print(f"Error: Input path is not a directory: {input_dir}")
        return
    
    # Find all txt files
    txt_files = sorted(list(input_dir.glob('*.txt')))  # Sort for consistent processing
    
    if not txt_files:
        print(f"No .txt files found in {input_dir}")
        return
    
    print("=" * 70)
    print("UNIDO PROJECT DOCUMENT INFO EXTRACTION")
    print("=" * 70)
    print(f"\nInput directory: {input_dir}")
    print(f"Output file: {output_file}")
    print(f"Found {len(txt_files)} files to process...")
    print()
    
    results = []
    success_count = 0
    brief_found = 0
    challenges_found = 0
    error_count = 0  # Track errors
    
    for i, filepath in enumerate(txt_files, 1):
        if verbose or i % 100 == 0:
            print(f"Processing [{i}/{len(txt_files)}]: {filepath.name}")
        
        try:
            result = process_document(filepath)  # Pass Path object
            results.append(result)
            
            if 'error' not in result:
                success_count += 1
                if result['brief_description']:
                    brief_found += 1
                if result['challenges_problem_statements']:
                    challenges_found += 1
            else:
                error_count += 1  # Increment error count
            
            if verbose:
                print(f"  - Project ID: {result['project_id']}")
                if 'error' in result:
                    print(f"  - Error: {result['error']}")
                else:
                    brief_len = len(result['brief_description'] or '')
                    chall_len = len(result['challenges_problem_statements'] or '')
                    print(f"  - Brief Description: {'Found' if result['brief_description'] else 'Not found'} ({brief_len} chars)")
                    print(f"  - Challenges: {'Found' if result['challenges_problem_statements'] else 'Not found'} ({chall_len} chars)")
        
        except Exception as e:
            error_count += 1  # Increment error count for unexpected exceptions
            print(f"  ✗ Unexpected error processing {filepath.name}: {e}")
            results.append({
                'project_id': extract_project_id(filepath),
                'brief_description': None,
                'challenges_problem_statements': None,
                'error': str(e)
            })
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write results to JSON file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Results saved to: {output_file}")
    except Exception as e:
        print(f"\n✗ Error saving results: {e}")
        return
    
    # Print summary
    print(f"\n{'='*70}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*70}")
    print(f"Total files processed: {len(results)}")
    print(f"Successfully processed: {success_count}")
    print(f"Errors: {error_count}")  # Display error count
    print(f"Brief descriptions found: {brief_found} ({brief_found/len(results)*100:.1f}%)")
    print(f"Challenges found: {challenges_found} ({challenges_found/len(results)*100:.1f}%)")
    print(f"{'='*70}")
    
    return results


if __name__ == '__main__':
    main()
