"""
Centralized configuration for document processing scripts.

This file contains shared configuration settings that are used across
multiple scripts in the docs directory. Update these values in one place
instead of modifying each script individually.
"""

# Folder source configuration
# Set to "local" or "cloud" to switch between folder locations
# - "local": uses folders relative to the script directory
# - "cloud": uses cloud folder paths (constructed from CLOUD_BASE_PATH)
FOLDER_SOURCE = "cloud"

# Cloud base path (only used when FOLDER_SOURCE = "cloud")
# This is the base path for cloud folders. Scripts will construct
# specific paths from this base (e.g., {CLOUD_BASE_PATH}/project docs)
CLOUD_BASE_PATH = r"C:\Users\hez\OneDrive - UNIDO\TCS\1. Expertise\research"

# OCR configuration (used by extract_pdf.py)
# If True, use OCR to extract text from scanned PDFs
# If False, move scanned PDFs to scanned folder without OCR
USE_OCR_FOR_SCANNED = True

