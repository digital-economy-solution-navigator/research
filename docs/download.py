"""
Script to download a PDF file from a URL and save it to the current folder.
"""

import requests
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# Constants
CHUNK_SIZE = 8192
KB_SIZE = 1024


def extract_filename_from_url(url: str) -> str:
    """
    Extract filename from URL, removing query parameters.
    
    Args:
        url: URL to extract filename from
    
    Returns:
        Extracted filename or 'download' if not found
    """
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    if not filename or '.' not in filename:
        # Try to get from Content-Disposition header or use default
        filename = 'download.pdf'
    return filename


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string (KB or MB)
    """
    if size_bytes < KB_SIZE:
        return f"{size_bytes} B"
    elif size_bytes < KB_SIZE * KB_SIZE:
        return f"{size_bytes / KB_SIZE:.2f} KB"
    else:
        return f"{size_bytes / (KB_SIZE * KB_SIZE):.2f} MB"


def download_file(url: str, filename: Optional[str] = None, 
                  output_dir: Optional[str] = None) -> Optional[Path]:
    """
    Download a file from a URL and save it to the specified directory.
    
    Args:
        url: URL of the file to download
        filename: Optional filename. If not provided, extracts from URL.
        output_dir: Optional output directory. Defaults to current directory.
    
    Returns:
        Path to downloaded file if successful, None otherwise
    """
    try:
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            print(f"Error: Invalid URL format: {url}")
            return None
        
        print(f"Downloading from: {url}")
        
        # Get the filename from URL if not provided
        if filename is None:
            filename = extract_filename_from_url(url)
        
        # Determine output path
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            filepath = output_path / filename
        else:
            filepath = Path(filename)
        
        # Make the request
        response = requests.get(url, stream=True, verify=True, timeout=30)
        response.raise_for_status()
        
        # Get file size if available
        total_size = int(response.headers.get('content-length', 0))
        if total_size > 0:
            print(f"File size: {format_file_size(total_size)}")
        
        # Save the file
        print(f"Saving to: {filepath.absolute()}")
        
        downloaded = 0
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}%", end='', flush=True)
        
        print()  # New line after progress
        
        # Verify file was saved
        if not filepath.exists():
            print("Error: File was not saved successfully.")
            return None
        
        saved_size = filepath.stat().st_size
        print(f"✓ Download complete! File saved: {filename} ({format_file_size(saved_size)})")
        
        return filepath
        
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out while downloading from {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
        return None
    except Exception as e:
        print(f"Error saving file: {e}")
        return None

if __name__ == "__main__":
    url = "https://downloads.unido.org/ot/22/10/2210706/7150.pdf"
    result = download_file(url)
    if result is None:
        exit(1)


