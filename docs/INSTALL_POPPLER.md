# Installing Poppler for PDF OCR

Poppler is required to convert PDF pages to images for OCR processing.

## Windows Installation

### Option 1: Download Pre-built Binary (Recommended)

1. Download poppler from: https://github.com/oschwartz10612/poppler-windows/releases/
   - Download the latest `Release-XX.XX.X-X.zip` file

2. Extract the zip file to a location like `C:\poppler`

3. Add to PATH (choose one method):

   **Method A: Add to System PATH**
   - Open System Properties → Environment Variables
   - Add `C:\poppler\Library\bin` to your PATH
   - Restart your terminal/IDE

   **Method B: Place in Standard Location**
   - Extract to `C:\poppler\bin` (the script will auto-detect this)
   - No PATH changes needed

### Option 2: Using Chocolatey

```powershell
choco install poppler
```

### Option 3: Using Conda

```bash
conda install -c conda-forge poppler
```

## macOS Installation

```bash
brew install poppler
```

## Linux Installation

```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# Fedora
sudo dnf install poppler-utils

# Arch Linux
sudo pacman -S poppler
```

## Verify Installation

After installation, verify poppler is working:

```bash
pdftoppm -h
```

If you see help text, poppler is installed correctly.

## Troubleshooting

If the script still can't find poppler:

1. **Check if poppler is in PATH:**
   ```bash
   where pdftoppm  # Windows
   which pdftoppm  # macOS/Linux
   ```

2. **Manually specify poppler path in the script:**
   Edit `extract_pdf.py` and modify the `poppler_path` variable in the `extract_text_with_ocr` function.

3. **For Windows, ensure you're using the correct path:**
   - The `bin` folder should contain `pdftoppm.exe`
   - Common locations: `C:\poppler\Library\bin` or `C:\poppler\bin`

