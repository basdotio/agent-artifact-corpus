---
name: pdf-compressor
description: Automatically compress PDF files when they are too large for processing. Use this skill when (1) a PDF file exceeds 10MB and needs compression for efficient processing, (2) user explicitly requests PDF compression, (3) reading a PDF fails with a file size error, or (4) a PDF exceeds the 32MB API limit. Compresses using Ghostscript while maintaining acceptable quality.
---

# PDF Compressor

Automatically compress large PDF files to enable processing or reduce file size.

## When This Skill Triggers

This skill automatically activates when:

1. **Large PDF detected** - PDF file exceeds 10MB
2. **User requests compression** - User says "compress this PDF", "this PDF is too large", etc.
3. **Read failure** - Attempting to read a PDF fails with file size error
4. **API limit** - PDF exceeds 32MB (Claude API hard limit)

## Compression Workflow

### Step 1: Check file size

```python
import os
file_size_mb = os.path.getsize('file.pdf') / (1024 * 1024)
if file_size_mb > 10:
    # Trigger compression
```

### Step 2: Run compression script

Use the bundled compression script:

```bash
python scripts/compress_pdf.py <input.pdf> -q ebook
```

**Quality levels:**
- `screen` - 72 dpi, smallest size (use for very large files >100MB)
- `ebook` - 150 dpi, balanced (default, recommended)
- `printer` - 300 dpi, high quality (minimal compression)
- `prepress` - 300 dpi, print-ready (minimal compression)

**Options:**
- `-o <output.pdf>` - Save to different file (default: overwrite original)
- `--no-backup` - Don't backup original file

### Step 3: Verify compression

The script outputs:
- Original file size
- Compressed file size
- Compression ratio (% reduction)
- Output file path

### Step 4: Proceed with compressed file

After compression, use the compressed PDF for the original task.

## Usage Examples

### Example 1: Automatic compression on large file

```
User: "Please analyze this PDF report.pdf"
[File is 25MB]

1. Check size: 25MB > 10MB threshold
2. Compress: python scripts/compress_pdf.py report.pdf -q ebook
3. Result: Compressed from 25MB to 8MB (68% reduction)
4. Proceed: Read and analyze the compressed report.pdf
```

### Example 2: User requests compression

```
User: "This PDF is too big, can you compress it?"

1. Run: python scripts/compress_pdf.py document.pdf -q ebook
2. Report results to user
```

### Example 3: API limit exceeded

```
User: "Extract text from this 40MB PDF"
[Exceeds 32MB API limit]

1. Compress aggressively: python scripts/compress_pdf.py file.pdf -q screen
2. If still too large, inform user and suggest manual compression
3. Otherwise proceed with compressed file
```

## Script Reference

### compress_pdf.py

Python script that uses Ghostscript for PDF compression.

**Requirements:**
- Ghostscript must be installed on the system
- Script automatically detects Ghostscript location

**Installation check:**

```python
from scripts.compress_pdf import PDFCompressor
compressor = PDFCompressor()
if not compressor.is_available():
    # Ghostscript not found
    # Provide installation instructions
```

**Programmatic usage:**

```python
from scripts.compress_pdf import PDFCompressor

compressor = PDFCompressor()
result = compressor.compress(
    input_path='large.pdf',
    output_path=None,  # None = overwrite
    quality='ebook',    # screen/ebook/printer/prepress
    backup=True         # Backup before overwrite
)

if result['success']:
    print(f"Compressed: {result['compression_ratio']}% reduction")
    print(f"New size: {result['compressed_size_mb']} MB")
else:
    print(f"Error: {result['error']}")
```

## Compression Guidelines

### When to compress

- **Always** - File > 32MB (API limit)
- **Recommended** - File > 10MB (performance optimization)
- **Optional** - File < 10MB (only if user requests)

### Quality selection

- **File > 100MB** → Use `screen` quality (aggressive compression)
- **File 10-100MB** → Use `ebook` quality (balanced, default)
- **File < 10MB** → Use `printer` or `prepress` (minimal compression)

### Compression expectations

Typical compression ratios:
- **Scanned documents** - 60-80% reduction
- **Image-heavy PDFs** - 50-70% reduction
- **Text-only PDFs** - 30-50% reduction
- **Already compressed** - 10-20% reduction (limited gains)

### Handling edge cases

**Ghostscript not installed:**
- Inform user and provide installation instructions
- Windows: https://ghostscript.com/releases/gsdnld.html
- Mac: `brew install ghostscript`
- Linux: `sudo apt-get install ghostscript`

**Compression fails:**
- Try lower quality level (ebook → screen)
- Check if PDF is corrupted
- Suggest manual compression tools

**File still too large after compression:**
- Inform user of the limitation
- Suggest splitting PDF or extracting specific pages
- Recommend external compression services

## Implementation Notes

- **Always backup** - Original file is backed up before overwriting (unless `--no-backup`)
- **Lossless for text** - Text content remains readable at all quality levels
- **Images affected** - Lower quality levels reduce image resolution
- **Speed** - Compression time ~1-2 seconds per MB (varies by complexity)
- **Path handling** - Script handles spaces and special characters in filenames
- **Error handling** - Script validates Ghostscript availability and file existence

## Troubleshooting

**Script fails to find Ghostscript on Windows:**
- Check if Ghostscript is installed
- Manually specify path if in non-standard location
- Ensure `gswin64c.exe` or `gswin32c.exe` is in PATH

**Compressed file is larger than original:**
- Original was already optimized
- Try different quality level
- PDF may have compression-resistant content

**Compression too aggressive:**
- Use higher quality level (screen → ebook → printer)
- Images will be sharper but file size larger
