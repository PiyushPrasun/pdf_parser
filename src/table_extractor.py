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
        Extract tables from PDF
        
        Args:
            pdf_path: Path to the PDF file
            pages: Pages to extract tables from
            
        Returns:
            List of dictionaries with table data
        """
        tables = []
        
        # Use camelot if available
        if CAMELOT_AVAILABLE:
            try:
                # Try lattice mode first (for tables with borders)
                lattice_tables = self._extract_with_camelot(pdf_path, pages, flavour='lattice')
                
                # Try stream mode if no tables found (for tables without borders)
                try:
                    stream_tables = self._extract_with_camelot(pdf_path, pages, flavour='stream')
                except Exception as e:
                    print(f"Camelot stream extraction failed: {str(e)}")
                
                # Combine tables, preferring lattice when there's overlap
                tables = self._merge_table_results(lattice_tables, stream_tables)
                
                # Filter out low-quality and tiny tables
                tables = self._filter_tables_by_quality(tables)
                
                # If no tables found with Camelot, try Tabula
                if not tables and TABULA_AVAILABLE:
                    try:
                        tables = self._extract_with_tabula(pdf_path, pages)
                        # Filter tabula tables too
                        tables = self._filter_tables_by_quality(tables)
                    except Exception as e:
                        print(f"Tabula extraction failed: {str(e)}")
            except Exception as e:
                print(f"Camelot lattice extraction failed: {str(e)}")
                
                # Fallback to tabula if available
                if TABULA_AVAILABLE:
                    try:
                        tables = self._extract_with_tabula(pdf_path, pages)
                        # Filter tabula tables too
                        tables = self._filter_tables_by_quality(tables)
                    except Exception as e:
                        print(f"Tabula extraction failed: {str(e)}")
        
        # Use tabula if camelot is not available
        elif TABULA_AVAILABLE:
            try:
                tables = self._extract_with_tabula(pdf_path, pages)
                # Filter tabula tables too
                tables = self._filter_tables_by_quality(tables)
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
    
    def _filter_tables_by_quality(self, tables: List[Dict]) -> List[Dict]:
        """
        Filter tables by quality metrics to remove useless tables
        
        Args:
            tables: List of extracted tables
            
        Returns:
            Filtered list of tables
        """
        if not tables:
            return []
            
        filtered_tables = []
        
        for table in tables:
            # Get table dimensions
            rows = len(table.get('rows', []))
            cols = table['shape'][1] if 'shape' in table else 0
            
            # Skip tiny tables (less than 2x2)
            if rows < 2 or cols < 2:
                print(f"Skipping tiny table: {rows}x{cols}")
                continue
                
            # Skip tables with very low accuracy
            accuracy = table.get('accuracy')
            if accuracy is not None and accuracy < 0.3:  # 30% accuracy threshold
                print(f"Skipping low accuracy table: {accuracy}")
                continue
                
            # Clean the table data first
            cleaned_rows = []
            for row in table.get('rows', []):
                cleaned_row = []
                for cell in row:
                    cell_str = str(cell).strip() if cell is not None else ""
                    cleaned_row.append(cell_str)
                
                # Only include rows that aren't completely empty
                if any(cell for cell in cleaned_row):
                    cleaned_rows.append(cleaned_row)
            
            # Skip if no meaningful rows after cleaning
            if len(cleaned_rows) < 2:
                print(f"Skipping table with insufficient data rows: {len(cleaned_rows)}")
                continue
                
            # Update table with cleaned data
            table['rows'] = cleaned_rows
            table['shape'] = (len(cleaned_rows), len(cleaned_rows[0]) if cleaned_rows else 0)
            
            # Check for mostly empty cells after cleaning
            empty_cells = 0
            total_cells = 0
            
            for row in cleaned_rows:
                for cell in row:
                    total_cells += 1
                    if not cell:
                        empty_cells += 1
                        
            if total_cells > 0 and empty_cells / total_cells > 0.6:  # More than 60% empty
                print(f"Skipping mostly empty table: {empty_cells}/{total_cells} empty cells")
                continue
                
            # Check for content diversity - avoid tables with too much repetition
            unique_values = set()
            for row in cleaned_rows:
                for cell in row:
                    if cell:
                        unique_values.add(cell.lower().strip())
            
            # Need reasonable content diversity
            if len(unique_values) < 3:
                print(f"Skipping table with low content diversity: {len(unique_values)} unique values")
                continue
            
            # Clean headers if they exist
            headers = table.get('headers', [])
            if headers:
                cleaned_headers = [str(h).strip() if h is not None else f"Column {i+1}" 
                                 for i, h in enumerate(headers)]
                table['headers'] = cleaned_headers
            else:
                # Generate default headers if none exist
                num_cols = table['shape'][1] if table['shape'][1] > 0 else len(cleaned_rows[0])
                table['headers'] = [f"Column {i+1}" for i in range(num_cols)]
            
            # This table passes quality checks
            filtered_tables.append(table)
            
        print(f"Filtered {len(tables)} tables down to {len(filtered_tables)} quality tables")
        return filtered_tables
    
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
        Convert a table to HTML for display with improved formatting
        
        Args:
            table: Table dictionary from extract_tables
            
        Returns:
            HTML representation of the table
        """
        html = ['<div class="table-responsive">']
        html.append('<table class="table table-bordered table-hover table-striped table-sm">')
        
        # Headers
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        if not rows:
            return '<div class="alert alert-warning">No data available for this table</div>'
        
        # Use first row as headers if no headers provided
        if not headers and rows:
            headers = [f"Column {i+1}" for i in range(len(rows[0]))]
        
        if headers:
            html.append('<thead class="table-dark">')
            html.append('<tr>')
            for header in headers:
                header_text = str(header).strip() or "Column"
                html.append(f'<th class="text-center fw-bold">{header_text}</th>')
            html.append('</tr>')
            html.append('</thead>')
        
        # Body
        if rows:
            html.append('<tbody>')
            for i, row in enumerate(rows):
                # Add alternating row colors
                row_class = 'table-light' if i % 2 == 0 else ''
                html.append(f'<tr class="{row_class}">')
                
                for j, cell in enumerate(row):
                    cell_text = str(cell).strip() if cell is not None else ""
                    
                    # Smart formatting based on content
                    cell_class = ""
                    
                    # Check if it's numeric
                    try:
                        # Try to parse as number
                        num_val = float(cell_text.replace(',', '').replace('$', '').replace('%', ''))
                        cell_class = "text-end fw-semibold"
                        
                        # Add currency/percentage formatting if detected
                        if '$' in str(cell):
                            cell_class += " text-success"
                        elif '%' in str(cell):
                            cell_class += " text-info"
                            
                    except (ValueError, TypeError):
                        # Text content
                        if cell_text.lower() in ['yes', 'true', 'active', 'enabled', 'pass']:
                            cell_class = "text-success fw-semibold"
                        elif cell_text.lower() in ['no', 'false', 'inactive', 'disabled', 'fail']:
                            cell_class = "text-danger fw-semibold"
                        elif len(cell_text) > 50:
                            cell_class = "text-wrap"
                        else:
                            cell_class = "text-start"
                    
                    # Escape HTML characters
                    cell_text = cell_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    
                    html.append(f'<td class="{cell_class}">{cell_text}</td>')
                    
                html.append('</tr>')
            html.append('</tbody>')
        
        html.append('</table>')
        html.append('</div>')
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
