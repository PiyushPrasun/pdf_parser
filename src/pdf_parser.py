#!/usr/bin/env python3
"""
PDF Parser Module - Extract and process text content from PDF files
"""

import os
import re
from typing import List, Dict, Optional, Any, Union
from pypdf import PdfReader
import nltk
from nltk.tokenize import sent_tokenize

# Download required NLTK data
try:
    nltk.data.find('punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# Import OCR processor - use try/except to handle cases where it's not installed
try:
    from src.ocr_processor import OCRProcessor
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Import table extractor - use try/except to handle cases where it's not installed
try:
    from src.table_extractor import TableExtractor
    TABLE_EXTRACTION_AVAILABLE = True
except ImportError:
    TABLE_EXTRACTION_AVAILABLE = False

# Import CSV exporter - use try/except to handle cases where it's not installed
try:
    from src.csv_exporter import CSVExporter
    CSV_EXPORT_AVAILABLE = True
except ImportError:
    CSV_EXPORT_AVAILABLE = False

class PDFParser:
    """
    A class for parsing PDF files and extracting structured content
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, 
                 use_ocr: bool = False, tesseract_path: Optional[str] = None,
                 extract_tables: bool = False, table_flavour: str = 'lattice'):
        """
        Initialize the PDF parser
        
        Args:
            chunk_size: Maximum size of text chunks
            chunk_overlap: Overlap between chunks to maintain context
            use_ocr: Whether to use OCR for text extraction from scanned documents
            tesseract_path: Path to Tesseract executable (if not in PATH)
            extract_tables: Whether to extract tables from the PDF
            table_flavour: Table extraction method ('lattice' or 'stream')
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_ocr = use_ocr
        self.extract_tables = extract_tables
        
        # Initialize OCR processor if requested and available
        self.ocr_processor = None
        if use_ocr:
            if not OCR_AVAILABLE:
                raise ImportError("OCR processing requested but OCR module is not available. "
                                 "Make sure pytesseract and pdf2image are installed.")
            self.ocr_processor = OCRProcessor(tesseract_path=tesseract_path)
            
            # Verify Tesseract is installed
            if not self.ocr_processor.is_tesseract_installed():
                raise RuntimeError("Tesseract OCR is not installed or not found in PATH")
        
        # Initialize table extractor if requested
        self.table_extractor = None
        if extract_tables:
            if not TABLE_EXTRACTION_AVAILABLE:
                raise ImportError("Table extraction requested but table extraction module is not available. "
                                 "Make sure camelot-py or tabula-py is installed.")
            self.table_extractor = TableExtractor(flavour=table_flavour)
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract all text content from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            The extracted text as a string
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        reader = PdfReader(pdf_path)
        text = ""
        
        # First, try standard PDF text extraction
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            
            # If page has no text and OCR is enabled, try OCR
            if (not page_text or page_text.isspace()) and self.use_ocr and self.ocr_processor:
                try:
                    ocr_result = self.ocr_processor.ocr_pdf_page(pdf_path, i)
                    text += ocr_result + "\n"
                except Exception as e:
                    # Log error and continue with empty text
                    print(f"OCR failed for page {i}: {str(e)}")
                    text += "\n"
            else:
                text += page_text + "\n"
        
        # Clean up the text (remove excessive whitespace, etc.)
        text = self._clean_text(text)
        
        return text
    
    def _clean_text(self, text: str) -> str:
        """
        Clean the extracted text by removing unnecessary whitespace and characters
        
        Args:
            text: Raw text from PDF
            
        Returns:
            Cleaned text
        """
        # Replace multiple newlines with a single one
        text = re.sub(r'\n+', '\n', text)
        
        # Replace multiple spaces with a single one
        text = re.sub(r' +', ' ', text)
        
        # Remove any weird characters or control characters
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        
        return text.strip()
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing metadata
        """
        reader = PdfReader(pdf_path)
        metadata = {}
        
        # Extract standard metadata fields
        if reader.metadata:
            for key, value in reader.metadata.items():
                if key.startswith('/'):
                    key = key[1:]  # Remove the leading slash
                metadata[key] = value
        
        # Add number of pages
        metadata['num_pages'] = len(reader.pages)
        
        return metadata
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into smaller chunks for processing
        
        Args:
            text: The text to be chunked
            
        Returns:
            A list of text chunks
        """
        # Simple chunking by paragraph or newlines
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # If adding this paragraph would exceed the chunk size, 
            # save the current chunk and start a new one
            if len(current_chunk) + len(para) > self.chunk_size:
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap from the previous chunk
                if len(current_chunk) > self.chunk_overlap:
                    # Take the last portion of the previous chunk as overlap
                    current_chunk = current_chunk[-self.chunk_overlap:] + "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
    
    def extract_text_with_ocr(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text using OCR from all pages of a PDF
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary mapping page numbers to OCR text results
        """
        if not self.use_ocr or not self.ocr_processor:
            raise ValueError("OCR is not enabled or OCR processor is not available")
            
        ocr_results = self.ocr_processor.ocr_pdf(pdf_path)
        return ocr_results
    
    def extract_tables_from_pdf(self, pdf_path: str, pages: str = 'all') -> List[Dict[str, Any]]:
        """
        Extract tables from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            pages: Pages to extract tables from ('all' or page numbers e.g., '1,3-5')
            
        Returns:
            List of dictionaries containing table data
        """
        if not self.extract_tables or not self.table_extractor:
            raise ValueError("Table extraction is not enabled")
            
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        return self.table_extractor.extract_tables(pdf_path, pages)
    
    def save_tables_to_csv(self, tables: List[Dict[str, Any]], output_dir: str, base_filename: str) -> List[str]:
        """
        Save extracted tables to CSV files
        
        Args:
            tables: List of table dictionaries from extract_tables_from_pdf
            output_dir: Directory to save CSV files
            base_filename: Base filename for CSV files
            
        Returns:
            List of paths to saved CSV files
        """
        if not self.extract_tables:
            raise ValueError("Table extraction is not enabled")
            
        # Use the CSV Exporter if available (more robust)
        if CSV_EXPORT_AVAILABLE:
            return CSVExporter.export_tables_to_csv(tables, output_dir, base_filename)
        elif self.table_extractor:
            # Fallback to the table extractor's method
            return self.table_extractor.save_tables_to_csv(tables, output_dir, base_filename)
        else:
            raise ValueError("No table extractor or CSV exporter available")
    
    def export_text_as_csv(self, text: str, output_dir: str, base_filename: str) -> str:
        """
        Export raw text as CSV, attempting to detect tabular structure
        
        Args:
            text: Raw text to export
            output_dir: Directory to save the CSV file
            base_filename: Base filename for the CSV file
            
        Returns:
            Path to the saved CSV file
        """
        if CSV_EXPORT_AVAILABLE:
            return CSVExporter.export_text_as_csv(text, output_dir, base_filename)
        else:
            # Create a simple CSV if the CSV exporter is not available
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            csv_path = os.path.join(output_dir, f"{base_filename}_text.csv")
            with open(csv_path, 'w', newline='') as f:
                f.write(text)
                
            return csv_path
    
    def parse_pdf(self, pdf_path: str, force_ocr: bool = False, 
                 extract_tables: bool = None, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse a PDF file and return its content and metadata
        
        Args:
            pdf_path: Path to the PDF file
            force_ocr: Force OCR processing on all pages, even if they already have text
            extract_tables: Override the class setting for table extraction
            output_dir: Directory to save extracted tables as CSV files
            
        Returns:
            Dictionary containing text content, chunks, metadata, and tables if extracted
        """
        # Extract text - standard extraction with OCR fallback if enabled
        text = self.extract_text_from_pdf(pdf_path)
        chunks = self.chunk_text(text)
        metadata = self.extract_metadata(pdf_path)
        
        result = {
            "text": text,
            "chunks": chunks,
            "metadata": metadata,
            "num_chunks": len(chunks),
            "ocr_used": self.use_ocr
        }
        
        # If OCR is enabled and force_ocr is True, process all pages with OCR regardless
        if self.use_ocr and force_ocr and self.ocr_processor:
            try:
                ocr_results = self.extract_text_with_ocr(pdf_path)
                
                # Combine all OCR text
                ocr_text = "\n".join([text for _, text in sorted(ocr_results.items())])
                ocr_text = self._clean_text(ocr_text)
                
                # Add OCR-specific results
                result["ocr_text"] = ocr_text
                result["ocr_chunks"] = self.chunk_text(ocr_text)
                result["ocr_by_page"] = ocr_results
            except Exception as e:
                result["ocr_error"] = str(e)
        
        # Extract tables if requested
        should_extract_tables = extract_tables if extract_tables is not None else self.extract_tables
        
        if should_extract_tables:
            try:
                tables = []
                csv_paths = []
                base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
                
                # Try table extraction if available
                if TABLE_EXTRACTION_AVAILABLE:
                    # Ensure we have a table extractor
                    if not self.table_extractor:
                        self.table_extractor = TableExtractor()
                    
                    # Extract tables
                    tables = self.table_extractor.extract_tables(pdf_path)
                    result["tables"] = tables
                    result["num_tables"] = len(tables)
                    
                    # Save tables to CSV if output directory is provided
                    if output_dir and tables:
                        csv_table_paths = self.save_tables_to_csv(tables, output_dir, base_filename)
                        csv_paths.extend(csv_table_paths)
                
                # If no tables found or table extraction failed, try exporting text as CSV
                if not tables and output_dir:
                    # Export raw text as CSV
                    text_csv_path = self.export_text_as_csv(text, output_dir, base_filename)
                    csv_paths.append(text_csv_path)
                    result["text_csv_path"] = text_csv_path
                
                if csv_paths:
                    result["table_csv_paths"] = csv_paths
                
            except Exception as e:
                result["table_extraction_error"] = str(e)
        
        return result


if __name__ == "__main__":
    # Simple demo
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Parse PDF files with optional OCR")
    parser.add_argument("pdf_path", help="Path to the PDF file to parse")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR for text extraction")
    parser.add_argument("--force-ocr", action="store_true", help="Force OCR on all pages")
    parser.add_argument("--tesseract-path", help="Path to Tesseract executable")
    parser.add_argument("--extract-tables", action="store_true", help="Extract tables from PDF")
    parser.add_argument("--table-flavour", choices=["lattice", "stream"], default="lattice", help="Table extraction method")
    parser.add_argument("--export-csv", action="store_true", help="Export tables to CSV")
    parser.add_argument("--output-dir", default=".", help="Directory to save files")
    
    args = parser.parse_args()
    
    try:
        # Initialize parser with OCR if requested
        pdf_parser = PDFParser(
            use_ocr=args.ocr,
            tesseract_path=args.tesseract_path,
            extract_tables=args.extract_tables,
            table_flavour=args.table_flavour
        )
        
        # Parse the PDF
        result = pdf_parser.parse_pdf(
            args.pdf_path, 
            force_ocr=args.force_ocr,
            output_dir=args.output_dir if args.export_csv else None
        )
        
        # Display results
        print(f"\nPDF Parsing Results:")
        print(f"{'=' * 40}")
        print(f"File: {args.pdf_path}")
        print(f"Pages: {result['metadata'].get('num_pages', 'Unknown')}")
        print(f"OCR Enabled: {result['ocr_used']}")
        print(f"Total text length: {len(result['text'])}")
        print(f"Number of chunks: {result['num_chunks']}")
        
        if 'tables' in result:
            print(f"Tables extracted: {result['num_tables']}")
            
            if result['tables']:
                print("\nTable details:")
                for i, table in enumerate(result['tables']):
                    page = table.get('page', 'unknown')
                    shape = table.get('shape', (0, 0))
                    accuracy = table.get('accuracy')
                    method = table.get('extraction_method', 'unknown')
                    
                    print(f"  Table {i+1}: Page {page}, Rows x Cols: {shape[0]}x{shape[1]}, Method: {method}")
                    if accuracy is not None:
                        print(f"    Accuracy: {accuracy:.2f}%")
            
            if 'table_csv_paths' in result:
                print("\nTables exported to CSV:")
                for csv_path in result['table_csv_paths']:
                    print(f"  {csv_path}")
        
        if result['text']:
            print(f"\nText Preview:")
            print(f"{'=' * 40}")
            preview_length = min(300, len(result['text']))
            print(f"{result['text'][:preview_length]}...")
            
        # Show OCR-specific results if available
        if 'ocr_text' in result:
            print(f"\nOCR Text Preview:")
            print(f"{'=' * 40}")
            preview_length = min(300, len(result['ocr_text']))
            print(f"{result['ocr_text'][:preview_length]}...")
            
    except Exception as e:
        print(f"Error parsing PDF: {e}")
