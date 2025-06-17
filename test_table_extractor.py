#!/usr/bin/env python3
"""
Test script for table extraction from PDF files
"""

import os
import sys
from src.table_extractor import TableExtractor
from src.pdf_parser import PDFParser

def main():
    """Test table extraction on a PDF file"""
    if len(sys.argv) < 2:
        print("Usage: python test_table_extractor.py <pdf_file>")
        pdf_path = "/workspaces/pdf_parser/Snack_planogram_12_05_2025.pdf"
        print(f"Using default PDF: {pdf_path}")
    else:
        pdf_path = sys.argv[1]
        
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Testing table extraction on: {pdf_path}")
    print("-" * 50)
    
    # Test direct table extractor
    print("Method 1: Using TableExtractor directly")
    try:
        extractor = TableExtractor()
        tables = extractor.extract_tables(pdf_path)
        
        print(f"Found {len(tables)} tables")
        for i, table in enumerate(tables):
            print(f"Table {i+1}:")
            print(f"  Page: {table.get('page', 'unknown')}")
            print(f"  Rows x Cols: {table.get('shape', (0, 0))}")
            print(f"  Method: {table.get('extraction_method', 'unknown')}")
            print(f"  Headers: {table.get('headers', [])}")
            print(f"  First few rows:")
            rows = table.get('rows', [])
            for r in rows[:3]:  # Print first 3 rows
                print(f"    {r}")
            if len(rows) > 3:
                print("    ...")
                
            # Save to CSV
            output_dir = "outputs"
            os.makedirs(output_dir, exist_ok=True)
            csv_path = extractor.save_tables_to_csv([table], output_dir, f"table_{i+1}")[0]
            print(f"  Saved to: {csv_path}")
            print()
            
    except Exception as e:
        print(f"Error using TableExtractor: {str(e)}")
    
    print("-" * 50)
    
    # Test through PDFParser
    print("Method 2: Using PDFParser")
    try:
        parser = PDFParser(extract_tables=True)
        result = parser.parse_pdf(pdf_path, output_dir="outputs")
        
        tables = result.get('tables', [])
        print(f"Found {len(tables)} tables")
        
        if 'table_extraction_error' in result:
            print(f"Error: {result['table_extraction_error']}")
        
        if 'table_csv_paths' in result:
            print("CSV exports:")
            for path in result['table_csv_paths']:
                print(f"  {path}")
                
    except Exception as e:
        print(f"Error using PDFParser: {str(e)}")

if __name__ == "__main__":
    main()
