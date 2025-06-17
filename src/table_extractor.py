#!/usr/bin/env python3
"""
Table Extractor Module - Extract tabular data from PDFs
"""

import os
import re
import csv
import json
import tempfile
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
from PIL import Image

# Import camelot-py in a try/except block as it's a new dependency
# We'll gracefully handle the case if it's not installed
try:
    import camelot
    import pandas as pd
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False

# Try to import tabula as a fallback option
try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False


class TableExtractor:
    """
    A class for extracting tabular data from PDF files
    """
    
    def __init__(self, 
                 flavour: str = 'lattice', 
                 line_scale: float = 15, 
                 strip_text: str = '\n', 
                 edge_tol: int = 50,
                 min_cell_confidence: float = 0.5):
        """
        Initialize the TableExtractor
        
        Args:
            flavour: Table parsing method, either 'lattice' or 'stream'
            line_scale: Line scale parameter for camelot, higher is more sensitive
            strip_text: String to strip from cell text
            edge_tol: Edge tolerance parameter for camelot
            min_cell_confidence: Minimum confidence score for a cell to be considered valid
            min_cell_confidence: Minimum confidence for a cell to be considered valid
        """
        self.flavour = flavour
        self.line_scale = line_scale
        self.strip_text = strip_text
        self.edge_tol = edge_tol
        self.min_cell_confidence = min_cell_confidence
        
        # Set default options based on flavour
        if self.flavour == 'lattice':
            # Lattice flavor uses lines for extraction
            self.line_scale = max(15, self.line_scale)  # Ensures we detect lines properly
        else:
            # Stream flavor uses whitespace for extraction
            self.edge_tol = min(500, self.edge_tol)  # Increased edge tolerance for more text capture
        
        if not CAMELOT_AVAILABLE and not TABULA_AVAILABLE:
            raise ImportError(
                "No table extraction library available. "
                "Please install either camelot-py with 'pip install camelot-py[cv]' "
                "or tabula-py with 'pip install tabula-py'."
            )
    
    def extract_tables(self, pdf_path: str, pages: Optional[Union[str, List[int]]] = 'all') -> List[Dict]:
        """
        Extract tables from a PDF file using multiple methods for maximum robustness
        
        Args:
            pdf_path: Path to the PDF file
            pages: Pages to extract tables from ('all' or list of page numbers)
            
        Returns:
            List of dictionaries with table data
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        tables = []
        
        # Try with camelot first using lattice method
        if CAMELOT_AVAILABLE:
            try:
                # Try lattice method first (better for tables with borders)
                lattice_tables = self._extract_with_camelot(pdf_path, pages, flavour='lattice')
                
                # Then try stream method (better for tables without borders)
                stream_tables = []
                try:
                    stream_tables = self._extract_with_camelot(pdf_path, pages, flavour='stream')
                except Exception as e:
                    print(f"Camelot stream extraction failed: {str(e)}")
                
                # Combine tables, preferring lattice when there's overlap
                tables = self._merge_table_results(lattice_tables, stream_tables)
                
                # If no tables found with Camelot, try Tabula
                if not tables and TABULA_AVAILABLE:
                    try:
                        tables = self._extract_with_tabula(pdf_path, pages)
                    except Exception as e:
                        print(f"Tabula extraction failed: {str(e)}")
            except Exception as e:
                print(f"Camelot lattice extraction failed: {str(e)}")
                
                # Fallback to tabula if available
                if TABULA_AVAILABLE:
                    try:
                        tables = self._extract_with_tabula(pdf_path, pages)
                    except Exception as e:
                        print(f"Tabula extraction failed: {str(e)}")
        
        # Use tabula if camelot is not available
        elif TABULA_AVAILABLE:
            try:
                tables = self._extract_with_tabula(pdf_path, pages)
            except Exception as e:
                print(f"Tabula extraction failed: {str(e)}")
                return []
        
        return tables
    
    def _extract_with_camelot(self, pdf_path: str, 
                             pages: Optional[Union[str, List[int]]] = 'all',
                             flavour: Optional[str] = None) -> List[Dict]:
        """
        Extract tables using camelot-py
        
        Args:
            pdf_path: Path to the PDF file
            pages: Pages to extract tables from
            flavour: Override the default flavour
            
        Returns:
            List of dictionaries with table data
        """
        if isinstance(pages, list) and all(isinstance(p, int) for p in pages):
            pages = ','.join(str(p) for p in pages)
        
        # Use provided flavor or default
        flavor = flavour if flavour else self.flavour
        
        # edge_tol only applies to stream flavor, not lattice
        kwargs = {
            'pages': pages,
            'flavor': flavor,
            'line_scale': self.line_scale,
            'strip_text': self.strip_text,
        }
        
        # Add edge_tol only for stream flavor
        if flavor == 'stream':
            kwargs['edge_tol'] = self.edge_tol
        else:
            # For lattice, ensure we detect lines properly
            kwargs['line_scale'] = max(15, self.line_scale)
        
        tables_list = camelot.read_pdf(pdf_path, **kwargs)
        
        result = []
        for i, table in enumerate(tables_list):
            # Convert to a pandas DataFrame
            df = table.df
            
            # Calculate table metrics
            accuracy = table.parsing_report['accuracy']
            whitespace = table.parsing_report['whitespace']
            
            # Convert table to a list of dictionaries
            table_dict = df.to_dict('records')
            
            # Add table information
            result.append({
                "table_id": i,
                "page": table.page,
                "data": table_dict,
                "headers": list(df.iloc[0]),  # Use first row as headers
                "rows": df.values.tolist(),
                "shape": df.shape,
                "accuracy": accuracy,
                "whitespace": whitespace,
                "extraction_method": f"camelot-{self.flavour}"
            })
        
        return result
    
    def _extract_with_tabula(self, pdf_path: str, 
                            pages: Optional[Union[str, List[int]]] = 'all') -> List[Dict]:
        """
        Extract tables using tabula-py
        
        Args:
            pdf_path: Path to the PDF file
            pages: Pages to extract tables from
            
        Returns:
            List of dictionaries with table data
        """
        # Convert pages format for tabula
        if pages == 'all':
            tabula_pages = 'all'
        elif isinstance(pages, list):
            tabula_pages = pages
        else:
            tabula_pages = [int(p) for p in pages.split(',')]
        
        # Read tables
        tables_list = tabula.read_pdf(
            pdf_path, 
            pages=tabula_pages,
            multiple_tables=True
        )
        
        result = []
        for i, df in enumerate(tables_list):
            # Clean up DataFrame (remove NaN values)
            df = df.fillna('')
            
            # Convert table to a list of dictionaries
            table_dict = df.to_dict('records')
            
            # Add table information
            result.append({
                "table_id": i,
                "page": -1,  # tabula doesn't provide page number
                "data": table_dict,
                "headers": list(df.columns),
                "rows": df.values.tolist(),
                "shape": df.shape,
                "accuracy": None,  # tabula doesn't provide accuracy metrics
                "whitespace": None,
                "extraction_method": "tabula"
            })
        
        return result
    
    def _merge_table_results(self, lattice_tables: List[Dict], stream_tables: List[Dict]) -> List[Dict]:
        """
        Merge results from different table extraction methods, handling overlaps
        
        Args:
            lattice_tables: Tables extracted using lattice method
            stream_tables: Tables extracted using stream method
            
        Returns:
            Combined list of tables
        """
        if not stream_tables:
            return lattice_tables
        if not lattice_tables:
            return stream_tables
            
        # Start with all lattice tables (they're usually more accurate for structured tables)
        merged_tables = lattice_tables.copy()
        
        # Track page numbers where we already have tables
        existing_pages = {table.get('page', -1) for table in lattice_tables}
        
        # Add stream tables only for pages that don't already have lattice tables
        # or if the stream table has significantly more cells
        for stream_table in stream_tables:
            page = stream_table.get('page', -1)
            
            # Check if this is a new page
            if page not in existing_pages:
                merged_tables.append(stream_table)
                existing_pages.add(page)
                continue
                
            # Check if this stream table is better than existing lattice tables
            # by comparing cell count and table size
            stream_shape = stream_table.get('shape', (0, 0))
            stream_cell_count = stream_shape[0] * stream_shape[1]
            
            # Get existing lattice tables for this page
            lattice_tables_for_page = [
                t for t in lattice_tables 
                if t.get('page', -1) == page
            ]
            
            add_stream_table = True
            for lt in lattice_tables_for_page:
                lt_shape = lt.get('shape', (0, 0))
                lt_cell_count = lt_shape[0] * lt_shape[1]
                
                # If lattice table is similar or better, skip this stream table
                if lt_cell_count >= stream_cell_count * 0.7:
                    add_stream_table = False
                    break
            
            if add_stream_table:
                merged_tables.append(stream_table)
        
        return merged_tables
    
    def save_tables_to_csv(self, tables: List[Dict], output_dir: str, base_filename: str) -> List[str]:
        """
        Save extracted tables to CSV files
        
        Args:
            tables: List of table dictionaries from extract_tables
            output_dir: Directory to save CSV files
            base_filename: Base filename for CSV files
            
        Returns:
            List of paths to saved CSV files
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        csv_paths = []
        for i, table in enumerate(tables):
            csv_filename = f"{base_filename}_table_{i+1}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            
            # Get headers and rows
            headers = table.get('headers', [])
            rows = table.get('rows', [])
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if headers:
                    writer.writerow(headers)
                for row in rows:
                    writer.writerow(row)
                    
            csv_paths.append(csv_path)
        
        return csv_paths
    
    def get_table_html(self, table: Dict) -> str:
        """
        Convert a table to HTML for display
        
        Args:
            table: Table dictionary from extract_tables
            
        Returns:
            HTML representation of the table
        """
        html = ['<table class="table table-bordered table-hover">']
        
        # Headers
        headers = table.get('headers', [])
        if headers:
            html.append('<thead><tr>')
            for header in headers:
                html.append(f'<th>{header}</th>')
            html.append('</tr></thead>')
        
        # Body
        rows = table.get('rows', [])
        if rows:
            html.append('<tbody>')
            for row in rows:
                html.append('<tr>')
                for cell in row:
                    html.append(f'<td>{cell}</td>')
                html.append('</tr>')
            html.append('</tbody>')
        
        html.append('</table>')
        return ''.join(html)


def main():
    """
    Main function for testing
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract tables from PDF files")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--output-dir", default=".", help="Directory to save CSV files")
    parser.add_argument("--pages", default="all", help="Pages to extract tables from (e.g., '1,3-5')")
    parser.add_argument("--flavour", choices=["lattice", "stream"], default="lattice", 
                        help="Table parsing method")
    
    args = parser.parse_args()
    
    try:
        # Extract tables
        extractor = TableExtractor(flavour=args.flavour)
        tables = extractor.extract_tables(args.pdf_path, pages=args.pages)
        
        if not tables:
            print("No tables found in the PDF.")
            return
        
        # Save tables to CSV
        base_filename = os.path.splitext(os.path.basename(args.pdf_path))[0]
        csv_paths = extractor.save_tables_to_csv(tables, args.output_dir, base_filename)
        
        print(f"Found {len(tables)} tables:")
        for i, (table, csv_path) in enumerate(zip(tables, csv_paths)):
            page = table.get('page', 'unknown')
            shape = table.get('shape', (0, 0))
            print(f"Table {i+1}: Page {page}, Shape: {shape[0]}x{shape[1]}")
            print(f"  Saved to: {csv_path}")
            
            accuracy = table.get('accuracy')
            method = table.get('extraction_method')
            if accuracy is not None:
                print(f"  Accuracy: {accuracy:.2f}%, Method: {method}")
            else:
                print(f"  Method: {method}")
            print()
            
    except Exception as e:
        print(f"Error extracting tables: {str(e)}")


if __name__ == "__main__":
    main()
