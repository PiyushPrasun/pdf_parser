# PDF Parser

A custom PDF parser built with PyPDF and LangChain to extract and process text content from PDF files. Now with a professional web interface!

## Features

- Extract text and metadata from PDF files
- Process large documents by breaking them into manageable chunks
- Integrate with LangChain for enhanced document processing
- OCR support for scanned documents and images using Tesseract
- **Table detection and extraction from PDFs**
- **Export tables to CSV files for data analysis**
- Modern web interface for easy file uploads and processing
- Command-line interface for automation and scripting

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/pdf_parser.git
   cd pdf_parser
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Web Interface

The easiest way to use the PDF Parser is through the web interface:

```bash
# Start the web interface
python main.py --web

# Specify a custom port
python main.py --web --port 8080
```

Once started, open your browser and navigate to `http://localhost:5000` (or your custom port).

The web interface provides:
- Drag and drop file uploads
- Advanced configuration options
- Visual results display with statistics
- JSON viewer for examining extraction results
- Download options for parsed data

### Command Line Interface

For automation or batch processing, use the command-line interface:

```bash
# Basic usage
python main.py path/to/your/document.pdf

# Extract only metadata
python main.py path/to/your/document.pdf --metadata-only

# Use LangChain integration
python main.py path/to/your/document.pdf --use-langchain

# Customize chunk size and overlap
python main.py path/to/your/document.pdf --chunk-size 2000 --chunk-overlap 100

# Specify output file
python main.py path/to/your/document.pdf -o output.json

# Use OCR for scanned documents
python main.py path/to/your/document.pdf --ocr

# Force OCR on all pages (even if they have text)
python main.py path/to/your/document.pdf --ocr --force-ocr

# Extract tables from the PDF
python main.py path/to/your/document.pdf --extract-tables

# Extract tables and export to CSV
python main.py path/to/your/document.pdf --extract-tables --export-csv

# Use stream method for table extraction (for tables without clear borders)
python main.py path/to/your/document.pdf --extract-tables --table-flavour stream

# Specify a custom CSV output directory
python main.py path/to/your/document.pdf --extract-tables --export-csv --csv-output-dir /path/to/output

# Specify Tesseract path if not in system PATH
python main.py path/to/your/document.pdf --ocr --tesseract-path /path/to/tesseract

# Specify OCR language (default is English)
python main.py path/to/your/document.pdf --ocr --tesseract-lang deu  # German
```

### Python API

You can also use the PDF parser in your Python code:

```python
from src.pdf_parser import PDFParser

# Initialize the parser (without OCR or table extraction)
parser = PDFParser(chunk_size=1000, chunk_overlap=200)

# Or initialize with OCR support
parser = PDFParser(chunk_size=1000, chunk_overlap=200, use_ocr=True)

# Or initialize with table extraction
parser = PDFParser(chunk_size=1000, chunk_overlap=200, extract_tables=True)

# Or initialize with both OCR and table extraction
parser = PDFParser(chunk_size=1000, chunk_overlap=200, use_ocr=True, extract_tables=True, table_flavour='lattice')

# Parse a PDF file
result = parser.parse_pdf("path/to/your/document.pdf")

# Or parse with forced OCR processing on all pages
result = parser.parse_pdf("path/to/your/document.pdf", force_ocr=True)

# Access the extracted data
text = result["text"]
chunks = result["chunks"]
metadata = result["metadata"]

# Access OCR-specific data (if OCR was used)
if "ocr_text" in result:
    ocr_text = result["ocr_text"]
    ocr_chunks = result["ocr_chunks"]
    ocr_by_page = result["ocr_by_page"]
    
# Access table data (if table extraction was used)
if "tables" in result:
    tables = result["tables"]
    num_tables = result["num_tables"]
    
    # Export tables to CSV if needed
    csv_paths = parser.save_tables_to_csv(tables, "output_directory", "base_filename")
```

For LangChain integration:

```python
from src.langchain_parser import LangChainPDFParser

# Initialize the parser
parser = LangChainPDFParser(chunk_size=1000, chunk_overlap=200)

# Process a PDF file
result = parser.process_pdf("path/to/your/document.pdf")

# Access LangChain documents and chunks
langchain_docs = result["langchain_docs"]
langchain_chunks = result["langchain_chunks"]
```

## Requirements

- Python 3.7+
- pypdf
- langchain
- nltk
- python-dotenv

### OCR Support (Optional)
For OCR support, you'll need:
- Tesseract OCR installed on your system
- pytesseract
- pdf2image
- Pillow

#### Installing Tesseract OCR:

**On Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
# For additional languages:
sudo apt-get install -y tesseract-ocr-all
```

**On macOS:**
```bash
brew install tesseract
# For additional languages:
brew install tesseract-lang
```

**On Windows:**
1. Download the installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
2. Add the Tesseract installation directory to your system PATH

## License

This project is licensed under the MIT License - see the LICENSE file for details.