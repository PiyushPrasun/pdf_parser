#!/usr/bin/env python3
"""
Command Line Interface for PDF Parser
"""

import os
import sys
import argparse
import json
from typing import Dict, Any

from src.pdf_parser import PDFParser
from src.langchain_parser import LangChainPDFParser


def save_result_to_json(result: Dict[str, Any], output_path: str) -> None:
    """
    Save parsing results to a JSON file
    
    Args:
        result: Dictionary containing parsing results
        output_path: Path to save the JSON file
    """
    # Remove objects that can't be serialized to JSON
    if 'langchain_docs' in result:
        del result['langchain_docs']
    
    if 'langchain_chunks' in result:
        # Convert LangChain Document objects to dictionaries
        result['langchain_chunks'] = [
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in result['langchain_chunks']
        ]
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"Results saved to {output_path}")


def main():
    """
    Main entry point for the CLI
    """
    parser = argparse.ArgumentParser(description="Parse PDF files and extract content")
    
    parser.add_argument("pdf_path", help="Path to the PDF file to parse")
    parser.add_argument("--chunk-size", type=int, default=1000, 
                        help="Size of text chunks (default: 1000)")
    parser.add_argument("--chunk-overlap", type=int, default=200, 
                        help="Overlap between chunks (default: 200)")
    parser.add_argument("--use-langchain", action="store_true", 
                        help="Use LangChain for enhanced processing")
    parser.add_argument("--output", "-o", 
                        help="Output file path for JSON results (default: <pdf_name>_parsed.json)")
    parser.add_argument("--metadata-only", action="store_true",
                        help="Extract only metadata from the PDF")
                        
    # OCR related arguments
    parser.add_argument("--ocr", action="store_true",
                        help="Enable OCR for scanned documents and images in PDFs")
    parser.add_argument("--force-ocr", action="store_true",
                        help="Force OCR on all pages, even if they have text")
    parser.add_argument("--tesseract-path",
                        help="Path to Tesseract executable (if not in system PATH)")
    parser.add_argument("--tesseract-lang", default="eng",
                        help="Language for OCR (default: eng)")
    
    args = parser.parse_args()
    
    # Check if the PDF file exists
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Determine output path if not specified
    if not args.output:
        pdf_name = os.path.splitext(os.path.basename(args.pdf_path))[0]
        args.output = f"{pdf_name}_parsed.json"
    
    try:
        # Check for OCR dependencies if OCR is requested
        if args.ocr:
            try:
                # This will raise ImportError if the OCR dependencies are not available
                from src.ocr_processor import OCRProcessor
                
                # Check if Tesseract is installed
                ocr = OCRProcessor(tesseract_path=args.tesseract_path, 
                                 tesseract_lang=args.tesseract_lang)
                if not ocr.is_tesseract_installed():
                    print("Warning: Tesseract OCR is not installed or not found in PATH.")
                    print("OCR functionality will be disabled.")
                    args.ocr = False
            except ImportError:
                print("Warning: OCR dependencies (pytesseract, pdf2image) are not installed.")
                print("OCR functionality will be disabled.")
                args.ocr = False
        
        if args.use_langchain:
            # Use the LangChain parser
            # Note: Currently LangChain parser doesn't support OCR directly
            parser = LangChainPDFParser(args.chunk_size, args.chunk_overlap)
            result = parser.process_pdf(args.pdf_path)
        else:
            # Use the basic PDF parser with OCR if requested
            parser = PDFParser(
                chunk_size=args.chunk_size, 
                chunk_overlap=args.chunk_overlap,
                use_ocr=args.ocr,
                tesseract_path=args.tesseract_path
            )
            
            if args.metadata_only:
                # Extract only metadata
                result = {"metadata": parser.extract_metadata(args.pdf_path)}
            else:
                # Full parsing with optional OCR
                result = parser.parse_pdf(args.pdf_path, force_ocr=args.force_ocr)
        
        # Display summary information
        print(f"\nPDF Parsing Results for {os.path.basename(args.pdf_path)}:")
        print(f"{'=' * 40}")
        
        if "metadata" in result:
            print(f"Title: {result['metadata'].get('Title', 'Not available')}")
            print(f"Author: {result['metadata'].get('Author', 'Not available')}")
            print(f"Pages: {result['metadata'].get('num_pages', 'Not available')}")
        
        if not args.metadata_only:
            print(f"Text length: {len(result.get('text', ''))}")
            print(f"Chunks: {result.get('custom_chunk_count', len(result.get('chunks', [])))}")
            
            if args.use_langchain and 'langchain_chunk_count' in result:
                print(f"LangChain chunks: {result['langchain_chunk_count']}")
                
            # Display OCR information if available
            if 'ocr_used' in result and result['ocr_used']:
                print(f"OCR enabled: Yes")
                if 'ocr_text' in result:
                    print(f"OCR text length: {len(result['ocr_text'])}")
                if 'ocr_chunks' in result:
                    print(f"OCR chunks: {len(result['ocr_chunks'])}")
                if 'ocr_error' in result:
                    print(f"OCR error: {result['ocr_error']}")
        
        # Save results to JSON
        save_result_to_json(result, args.output)
        
    except Exception as e:
        print(f"Error parsing PDF: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
