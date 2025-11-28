"""
Script to download a PDF file from a URL and save it to the current folder.
"""

import requests
import os
from pathlib import Path

def download_file(url, filename=None):
    """
    Download a file from a URL and save it to the current folder.
    
    Args:
        url (str): URL of the file to download
        filename (str): Optional filename. If not provided, extracts from URL.
    """
    try:
        print(f"Downloading from: {url}")
        
        # Get the filename from URL if not provided
        if filename is None:
            filename = os.path.basename(url.split('?')[0])  # Remove query parameters if any
        
        # Make the request
        response = requests.get(url, stream=True, verify=True)
        response.raise_for_status()
        
        # Get file size if available
        total_size = int(response.headers.get('content-length', 0))
        if total_size > 0:
            print(f"File size: {total_size / 1024:.2f} KB")
        
        # Save the file
        filepath = Path(filename)
        print(f"Saving to: {filepath.absolute()}")
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Verify file was saved
        saved_size = filepath.stat().st_size
        print(f"Download complete! File saved: {filename} ({saved_size / 1024:.2f} KB)")
        
        return filepath
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
        return None
    except Exception as e:
        print(f"Error saving file: {e}")
        return None

if __name__ == "__main__":
    url = "https://downloads.unido.org/ot/22/10/2210706/7150.pdf"
    download_file(url)


