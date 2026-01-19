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
    - "cloud": uses {CLOUD_BASE_PATH}/text
"""

import os
import re
import json
from pathlib import Path
import sys

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import FOLDER_SOURCE, CLOUD_BASE_PATH


def extract_project_id(filename):
    """
    Extract project ID from filename.
    Files are typically named: {project_id}_{rest_of_name}.txt
    
    This matches the convention used in other scripts (download.py, check_missing_docs.py, etc.)
    """
    basename = os.path.basename(filename)
    # Try to extract project ID from the beginning of filename (format: {project_id}_{rest})
    match = re.match(r'^(\d+)_', basename)
    if match:
        return match.group(1)
    # Fallback: try to extract numeric ID at the beginning
    match = re.match(r'^(\d+)', basename)
    if match:
        return match.group(1)
    # Try to find any numeric sequence in the filename
    match = re.search(r'(\d{5,})', basename)
    if match:
        return match.group(1)
    # Last resort: use filename without extension
    return os.path.splitext(basename)[0]


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
    # Fix common OCR artifacts: spaces in the middle of short words (2-4 chars)
    # This catches cases like "T his" -> "This", "t o" -> "to", but avoids breaking longer phrases
    # Only fix if both parts are 1-2 characters (common OCR errors)
    text = re.sub(r'\b([A-Za-z])\s+([a-z]{1,2})\b', r'\1\2', text)
    # Remove multiple consecutive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text if text else None


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
        # Handle OCR artifacts: spaces in words (e.g., "T his" instead of "This")
        r'((?:T\s*hi\s*s|Th\s*e)\s+project\s+(?:aims|seeks|is\s+designed|is\s+expected|will)\s+to[^.]+\.(?:[^.]+\.){0,5})',
        # Standard version (without OCR artifacts)
        r'((?:This|The)\s+project\s+(?:aims|seeks|is\s+designed|is\s+expected|will)\s+to[^.]+\.(?:[^.]+\.){0,5})',
        # After "Implementing Agency:" look for project description paragraph
        r'Implementing\s+(?:Agency|Partner)\s*:\s*[^\n]+\n\s*([A-Z][^.]+(?:project|programme|initiative)[^.]*\.(?:[^.]+\.){0,5})',
        # After "Executing Entity:" or "Implementing Agency:" - next paragraph
        r'(?:Executing\s+Entity|Implementing\s+Agency)\s*:\s*[^\n]+\n\s*([A-Z][^.]*(?:project|programme|initiative|aims|seeks|will|is\s+designed)[^.]*\.(?:[^.]+\.){0,5})',
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
    
    return None


def extract_challenges(content):
    """
    Extract the 'Challenges/Problems' section from the document.
    Handles multiple document structures and formats including GEF CEO Endorsement docs.
    NO CHARACTER LIMITS applied.
    """
    
    results = []
    
    # ==========================================================================
    # PATTERN GROUP 0: GEF CEO Endorsement specific sections (highest priority for GEF docs)
    # ==========================================================================
    
    # A.4 baseline project and problem section (GEF format)
    gef_problem_patterns = [
        r'A\.?\s*4\.?\s*(?:The\s+)?baseline\s+project\s+and\s+(?:the\s+)?problem(?:\s+that\s+it\s+seeks\s+to\s+address)?',
        r'A\.?\s*\d+\.?\s*(?:The\s+)?problem(?:\s+that\s+it\s+seeks)?\s+to\s+(?:be\s+)?address',
    ]
    
    for pattern in gef_problem_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            start = match.end()
            # Find end (next A.5 or A.6 section, or B section)
            end_match = re.search(r'\n\s*(?:A\.?\s*[5-9]|B\.?\s+[A-Z]|C\.?\s+)', content[start:], re.IGNORECASE)
            if end_match:
                section_text = content[start:start + end_match.start()]
            else:
                section_text = content[start:start + 30000]
            
            if len(section_text) > 200:
                cleaned = clean_text(section_text)
                if cleaned and len(cleaned) > 100:
                    results.append(cleaned)
    
    # Barrier Analysis section (GEF format)
    barrier_patterns = [
        r'\n\s*Barrier\s+Analysis\s*\n',
        r'\n\s*(?:Key\s+)?Barriers?\s+(?:to\s+)?(?:the\s+)?(?:Development|Achievement|Implementation)',
        r'(?:main|key|significant)\s+barriers?\s+(?:to\s+achieving|include|are)',
    ]
    
    for pattern in barrier_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            start = match.start()
            # Find end of barrier section
            end_match = re.search(r'\n\s*(?:[A-Z]\.?\s*\d+\.?\s+[A-Z]|\d+\.\s+[A-Z][a-z]+\s+[A-Z]|The\s+project\s+(?:strategy|will|aims))', content[match.end():], re.IGNORECASE)
            if end_match:
                section_text = content[start:match.end() + end_match.start()]
            else:
                section_text = content[start:start + 15000]
            
            if len(section_text) > 100:
                cleaned = clean_text(section_text)
                if cleaned:
                    results.append(cleaned)
    
    # If we found GEF-specific sections, return them
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
            # Find end (next B.2 or C section)
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
    ]
    
    for pattern in a2_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            start = match.end()
            # Find end of section (A.3, B., or next major section)
            end_match = re.search(r'\n\s*(?:A\.?\s*3\s|B\.?\s+[A-Z]|C\.?\s+[A-Z]|PART\s+)', content[start:], re.IGNORECASE)
            if end_match:
                section_text = content[start:start + end_match.start()]
            else:
                section_text = content[start:start + 50000]
            
            # Verify it's actual content, not just TOC (has sentences with periods)
            if len(section_text) > 300 and re.search(r'\.\s+[A-Z]', section_text):
                cleaned = clean_text(section_text)
                if cleaned and len(cleaned) > 100:
                    results.append(cleaned)
    
    # If we found explicit A.2 CHALLENGES section, return it (don't add more)
    if results:
        if len(results) == 1:
            return results[0]
        else:
            return '\n\n---\n\n'.join(results)
    
    # ==========================================================================
    # PATTERN GROUP 1.5: SITUATION ANALYSIS with challenges (UNDP format)
    # ==========================================================================
    
    # First, try to find "I. SITUATION ANALYSIS" section and extract challenges from it
    situation_analysis_match = re.search(r'I\.\s*SITUATION\s+ANALYSIS\s*\n([\s\S]*?)(?=\n\s*(?:II\.|2\.|STRATEGY|PART\s+))', content, re.IGNORECASE)
    if situation_analysis_match:
        situation_section = situation_analysis_match.group(1)
        
        # Within situation analysis, look for challenge statements
        situation_challenge_patterns = [
            # "The main socio-economic challenges facing... include:"
            r'(?:main|major|key)\s+(?:socio-economic\s+)?challenges?\s+(?:facing|include|are)[:\s]*([\s\S]*?)(?=\n\s*(?:II\.|2\.|To\s+alleviate|In\s+response|The\s+project|Barriers?|Demand))',
            # "Barriers for..." section
            r'Barriers?\s+(?:for|to)\s+(?:effective\s+)?[^\n]+\n([\s\S]*?)(?=\n\s*(?:II\.|2\.|[A-Z]\.\s+|The\s+project|Demand))',
            # "The main reasons for..." (often followed by challenges)
            r'(?:main|major|key)\s+reasons?\s+(?:for|why)[^\n]+\n([\s\S]*?)(?=\n\s*(?:II\.|2\.|[A-Z]\.\s+|The\s+project|Demand))',
            # "constraints being:" or "constraints include:"
            r'(?:main|major|key)\s+constraints?\s+(?:being|include|are)[:\s]*([\s\S]*?)(?=\n\s*(?:II\.|2\.|In\s+agriculture|\([a-z]\)|The\s+project))',
        ]
        
        for pattern in situation_challenge_patterns:
            matches = list(re.finditer(pattern, situation_section, re.IGNORECASE))
            for match in matches:
                text = match.group(1) if match.groups() else match.group(0)
                cleaned = clean_text(text)
                if cleaned and len(cleaned) > 100:
                    results.append(cleaned)
    
    # Also try patterns that work anywhere in the document
    situation_patterns = [
        # Look for "socio-economic challenges" or similar anywhere
        r'(?:main|major|key)\s+(?:socio-economic\s+)?challenges?\s+(?:facing|include|are)[:\s]*([\s\S]*?)(?=\n\s*(?:II\.|2\.|To\s+alleviate|In\s+response|The\s+project))',
        # "Barriers for..." section
        r'Barriers?\s+(?:for|to)\s+(?:effective\s+)?[^\n]+\n([\s\S]*?)(?=\n\s*(?:II\.|2\.|[A-Z]\.\s+|The\s+project))',
    ]
    
    for pattern in situation_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            text = match.group(1) if match.groups() else match.group(0)
            cleaned = clean_text(text)
            if cleaned and len(cleaned) > 100:
                results.append(cleaned)
    
    if results:
        if len(results) == 1:
            return results[0]
        else:
            return '\n\n---\n\n'.join(results)
    
    # ==========================================================================
    # PATTERN GROUP 1.6: Numbered "Challenges to be addressed" section (Country Programme)
    # ==========================================================================
    
    numbered_challenges_patterns = [
        # 1.2. Challenges to be addressed
        r'\d+\.?\s*\d*\.?\s*Challenges?\s+to\s+be\s+addressed\s*\n([\s\S]*?)(?=\n\s*(?:\d+\.?\s*\d*\.?\s*[A-Z][a-z]+|[A-Z]\.\s+|\d+\.0\s+))',
        # Challenges to be addressed (standalone)
        r'Challenges?\s+to\s+be\s+addressed\s*\n([\s\S]*?)(?=\n\s*(?:\d+\.\s*[A-Z]|[A-Z]\.\s+|II\.|2\.))',
    ]
    
    for pattern in numbered_challenges_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            text = match.group(1)
            # Skip if it's just a TOC entry (too short)
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
        # Roman numeral Problem Statement (like "I. Problem Statement")
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
        # These patterns look for sentences that introduce challenge lists
        r'(?:challenges?\s+facing\s+the\s+(?:industrial|manufacturing|SME|country)|challenges?\s+include\s*[:\n])',
        r'(?:key|main|major)\s+(?:challenges?|problems?|constraints?|issues?)\s+(?:include|are|identified)\s*[:\n]',
        r'(?:industries?|sector|enterprises?|SMEs?)\s+face\s+(?:the\s+following\s+)?(?:major\s+)?(?:challenges?|problems?)',
    ]
    
    for pattern in context_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            # Get the paragraph containing this match and the following content
            para_start = max(0, content.rfind('\n\n', 0, match.start()) + 2)
            # Find end - look for next major section or double newline after content
            search_start = match.end()
            
            # Look for bullet points or numbered lists after the match
            bullet_content = re.search(r'((?:\s*[•\-\*\►\●]\s*[^\n]+\n?)+)', content[search_start:search_start + 5000])
            numbered_content = re.search(r'((?:\s*\d+[\.\)]\s*[^\n]+\n?)+)', content[search_start:search_start + 5000])
            
            if bullet_content:
                end = search_start + bullet_content.end()
            elif numbered_content:
                end = search_start + numbered_content.end()
            else:
                # Look for next section
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
        # Deduplicate
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
    # PATTERN GROUP 6: A. CONTEXT section with problem description (UNIDO project docs)
    # ==========================================================================
    
    context_section_patterns = [
        r'A\.?\s*CONTEXT\s*\n([\s\S]*?)(?=\n\s*(?:B\.?\s+|II\.|2\.\s+[A-Z]))',
    ]
    
    for pattern in context_section_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            text = match.group(1)
            # Only include if it mentions problems/challenges/risks
            if re.search(r'problem|challeng|threat|risk|pollut|contamin|danger|hazard', text, re.IGNORECASE):
                cleaned = clean_text(text)
                if cleaned and len(cleaned) > 200:
                    return cleaned
    
    # ==========================================================================
    # PATTERN GROUP 7: THE DEVELOPMENT CHALLENGE section (project reports/brochures)
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
    # PATTERN GROUP 8: Extract entire Situation Analysis section if it contains challenges
    # ==========================================================================
    
    # If we haven't found anything yet, try to extract the entire Situation Analysis section
    # and look for challenge-related content within it
    situation_full_match = re.search(r'I\.\s*SITUATION\s+ANALYSIS\s*\n([\s\S]*?)(?=\n\s*(?:II\.|2\.|STRATEGY|PART\s+))', content, re.IGNORECASE)
    if situation_full_match:
        situation_text = situation_full_match.group(1)
        # Check if it contains challenge-related keywords
        if re.search(r'challeng|problem|constraint|barrier|difficult|impediment|obstacle|issue|risk|threat', situation_text, re.IGNORECASE):
            # Extract the most relevant parts (first 5000 chars usually contain the main challenges)
            relevant_text = situation_text[:5000]
            # Try to find a natural break point
            break_match = re.search(r'(?:To\s+alleviate|In\s+response|The\s+project|Barriers?|Demand)', relevant_text, re.IGNORECASE)
            if break_match:
                relevant_text = relevant_text[:break_match.start()]
            
            cleaned = clean_text(relevant_text)
            if cleaned and len(cleaned) > 200:
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
        filepath: Path to the text file (str or Path)
    
    Returns:
        Dictionary with project_id, brief_description, challenges_problem_statements
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        return {
            'project_id': extract_project_id(str(filepath)),
            'brief_description': None,
            'challenges_problem_statements': None,
            'error': f"File not found: {filepath}"
        }
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return {
            'project_id': extract_project_id(str(filepath)),
            'brief_description': None,
            'challenges_problem_statements': None,
            'error': f"Failed to read file: {str(e)}"
        }
    
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    project_id = extract_project_id(str(filepath))
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
    """Main function to process all documents"""
    import argparse
    
    # Get script directory for default paths
    script_dir = Path(__file__).parent.absolute()
    
    # Determine default text folder based on FOLDER_SOURCE
    if FOLDER_SOURCE == "cloud":
        default_text_dir = Path(CLOUD_BASE_PATH) / "text"
        default_output_file = script_dir.parent / "project_info.json"
    else:  # local
        default_text_dir = script_dir
        default_output_file = script_dir.parent / "project_info.json"
    
    parser = argparse.ArgumentParser(
        description='Extract project info from UNIDO TC documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Process all txt files in default text folder ({default_text_dir})
  python extract_project_info.py
  
  # Process files from a specific directory
  python extract_project_info.py --input-dir /path/to/text/files
  
  # Specify custom output file
  python extract_project_info.py --output-file /path/to/output.json
  
  # Verbose mode (show details for each file)
  python extract_project_info.py --verbose
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
    txt_files = sorted(input_dir.glob('*.txt'))
    
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
    error_count = 0
    
    for i, filepath in enumerate(txt_files, 1):
        if verbose or i % 100 == 0:
            print(f"Processing [{i}/{len(txt_files)}]: {filepath.name}")
        
        try:
            result = process_document(filepath)
            results.append(result)
            
            if 'error' not in result:
                success_count += 1
                if result['brief_description']:
                    brief_found += 1
                if result['challenges_problem_statements']:
                    challenges_found += 1
            else:
                error_count += 1
            
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
            error_count += 1
            print(f"  ✗ Error processing {filepath.name}: {e}")
            results.append({
                'project_id': extract_project_id(str(filepath)),
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
    print(f"Errors: {error_count}")
    print(f"Brief descriptions found: {brief_found} ({brief_found/len(results)*100:.1f}%)")
    print(f"Challenges found: {challenges_found} ({challenges_found/len(results)*100:.1f}%)")
    print(f"{'='*70}")
    
    return results


if __name__ == '__main__':
    main()
