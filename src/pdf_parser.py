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

class PDFParser:
    """
    A class for parsing PDF files and extracting structured content
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, 
                 use_ocr: bool = False, tesseract_path: Optional[str] = None):
        """
        Initialize the PDF parser
        
        Args:
            chunk_size: Maximum size of text chunks
            chunk_overlap: Overlap between chunks to maintain context
            use_ocr: Whether to use OCR for text extraction from scanned documents
            tesseract_path: Path to Tesseract executable (if not in PATH)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_ocr = use_ocr
        
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
    
    def parse_pdf(self, pdf_path: str, force_ocr: bool = False) -> Dict[str, Any]:
        """
        Parse a PDF file and return its content and metadata
        
        Args:
            pdf_path: Path to the PDF file
            force_ocr: Force OCR processing on all pages, even if they already have text
            
        Returns:
            Dictionary containing text content, chunks, and metadata
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
    
    args = parser.parse_args()
    
    try:
        # Initialize parser with OCR if requested
        pdf_parser = PDFParser(
            use_ocr=args.ocr,
            tesseract_path=args.tesseract_path
        )
        
        # Parse the PDF
        result = pdf_parser.parse_pdf(args.pdf_path, force_ocr=args.force_ocr)
        
        # Display results
        print(f"\nPDF Parsing Results:")
        print(f"{'=' * 40}")
        print(f"File: {args.pdf_path}")
        print(f"Pages: {result['metadata'].get('num_pages', 'Unknown')}")
        print(f"OCR Enabled: {result['ocr_used']}")
        print(f"Total text length: {len(result['text'])}")
        print(f"Number of chunks: {result['num_chunks']}")
        
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
