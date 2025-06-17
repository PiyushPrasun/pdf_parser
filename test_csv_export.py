#!/usr/bin/env python3
"""
Test script for CSV export functionality
"""

import os
import sys
import json
from src.pdf_parser import PDFParser
from src.csv_exporter import CSVExporter

def main():
    """Test CSV export functionality"""
    if len(sys.argv) < 2:
        print("Usage: python test_csv_export.py <pdf_file>")
        pdf_path = "/workspaces/pdf_parser/Snack_planogram_12_05_2025.pdf"
        print(f"Using default PDF: {pdf_path}")
    else:
        pdf_path = sys.argv[1]
        
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Testing CSV export on: {pdf_path}")
    print("-" * 50)
    
    # Create output directory
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Initialize parser with table extraction enabled
    parser = PDFParser(extract_tables=True)
    
    # Parse the PDF
    result = parser.parse_pdf(pdf_path, output_dir=output_dir)
    
    # Save the parsed result as JSON
    json_path = os.path.join(output_dir, f"{base_filename}_parsed.json")
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Saved JSON to: {json_path}")
    
    # Check for extracted tables
    tables = result.get('tables', [])
    print(f"Extracted {len(tables)} tables")
    
    # Check for CSV files
    csv_paths = result.get('table_csv_paths', [])
    print(f"Generated {len(csv_paths)} CSV files:")
    for path in csv_paths:
        file_size = os.path.getsize(path)
        print(f"  - {path} ({file_size} bytes)")
    
    # If no tables were found, try using the CSV exporter directly
    if not tables:
        print("\nNo tables found. Trying direct text export...")
        text = result.get('text', '')
        if text:
            text_csv_path = CSVExporter.export_text_as_csv(text, output_dir, f"{base_filename}_text")
            print(f"Exported text to CSV: {text_csv_path}")
    
    print("\nTesting CSV export from JSON file...")
    csv_paths = CSVExporter.export_raw_json_as_csv(json_path, os.path.join(output_dir, "from_json"))
    print(f"Generated {len(csv_paths)} CSV files from JSON:")
    for path in csv_paths:
        print(f"  - {path}")

if __name__ == "__main__":
    main()
