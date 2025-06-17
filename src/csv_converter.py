#!/usr/bin/env python3
"""
CSV Converter Module - Provides robust conversion of PDF data to CSV format
"""

import os
import re
import csv
import json
import itertools
import pandas as pd
import numpy as np
import re
import itertools
from typing import List, Dict, Any, Optional, Union, Tuple

class CSVConverter:
    """
    Class for converting PDF data to tabular CSV format
    """
    
    @staticmethod
    def convert_pdf_to_csv(pdf_data: Dict, output_dir: str, base_filename: str) -> str:
        """
        Convert PDF data to CSV format, handling both detected tables and raw text
        
        Args:
            pdf_data: Dictionary containing extracted PDF data
            output_dir: Directory to save the CSV file
            base_filename: Base filename for the CSV file
            
        Returns:
            Path to the saved CSV file
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        csv_filename = f"{base_filename}_data.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        # First try to extract tables if they exist
        if 'tables' in pdf_data and pdf_data['tables']:
            # Each table will be converted to its own DataFrame
            data_frames = []
            
            for table in pdf_data['tables']:
                # Skip very small tables that may be just noise
                rows = table.get('rows', [])
                if len(rows) < 2 or (len(rows) > 0 and len(rows[0]) < 2):
                    continue
                
                # Try to extract headers
                table_headers = table.get('headers', [])
                if not table_headers and rows:
                    table_headers = rows[0]
                    rows = rows[1:]
                    
                # Make sure we have valid headers
                if not table_headers:
                    table_headers = [f"Column_{i+1}" for i in range(max(len(row) for row in rows))]
                    
                # Create a DataFrame for this table
                df = pd.DataFrame(rows)
                
                # Only add tables that have actual data
                if not df.empty and df.size > 4:  # More than just a 2x2 table
                    # Set the column names
                    if len(df.columns) == len(table_headers):
                        df.columns = table_headers
                    else:
                        # Adjust headers if lengths don't match
                        df.columns = table_headers[:len(df.columns)] if len(table_headers) > len(df.columns) else (
                            table_headers + [f"Column_{i+1}" for i in range(len(df.columns) - len(table_headers))]
                        )
                    
                    # Clean the data - replace NaN with empty string
                    df = df.fillna('')
                    
                    # Add to our list of DataFrames
                    data_frames.append(df)
            
            # If we have DataFrames, combine them into one
            if data_frames:
                # Choose the best DataFrame (the one with the most cells) as the primary one
                best_df = max(data_frames, key=lambda df: df.size)
                
                # Write to CSV
                best_df.to_csv(csv_path, index=False)
                return csv_path
        
        # If no tables were found, try to convert the raw text to a table format
        if 'text' in pdf_data and pdf_data['text']:
            return CSVConverter.text_to_table(pdf_data['text'], output_dir, base_filename)
            
        # Fallback to empty CSV with just the metadata
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Metadata_Key", "Metadata_Value"])
            
            if 'metadata' in pdf_data and pdf_data['metadata']:
                for key, value in pdf_data['metadata'].items():
                    writer.writerow([key, value])
                    
        return csv_path
    
    @staticmethod
    def text_to_table(text: str, output_dir: str, base_filename: str) -> str:
        """
        Convert raw text to tabular format by detecting structure
        
        Args:
            text: Raw text from PDF
            output_dir: Directory to save the CSV file
            base_filename: Base filename for the CSV file
            
        Returns:
            Path to the saved CSV file
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        csv_filename = f"{base_filename}_data.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        # Split into lines and remove empty lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Try multiple approaches to find a good table structure
        approaches = [
            CSVConverter._try_fixed_width_columns,
            CSVConverter._try_delimiter_detection,
            CSVConverter._try_line_grouping,
            CSVConverter._try_consistent_patterns,
        ]
        
        best_data = None
        best_score = 0
        
        # Try each approach and score the results
        for approach_func in approaches:
            data = approach_func(lines)
            if data and len(data) > 1:
                # Score this approach based on consistency and structure
                score = CSVConverter._score_table_structure(data)
                if score > best_score:
                    best_score = score
                    best_data = data
        
        # Use the best approach found
        data = best_data if best_data else [[line] for line in lines]
        
        # If none of the approaches worked well, use simple line-based conversion
        if not data or len(data) <= 1 or all(len(row) <= 1 for row in data):
            data = [[line] for line in lines]
            
        # Determine the maximum number of columns
        max_cols = max(len(row) for row in data) if data else 0
            
        # Create column headers
        headers = [f"Column_{i+1}" for i in range(max_cols)]
            
        # Pad rows to the same length
        for i in range(len(data)):
            if len(data[i]) < max_cols:
                data[i].extend([''] * (max_cols - len(data[i])))
            
        # Convert to DataFrame and save as CSV
        df = pd.DataFrame(data, columns=headers)
        df.to_csv(csv_path, index=False)
        return csv_path
    
    @staticmethod
    def _try_fixed_width_columns(lines: List[str]) -> List[List[str]]:
        """Try to extract columns by analyzing character positions"""
        if not lines or len(lines) < 2:
            return []
            
        # Find potential column boundaries by analyzing spaces
        spaces = []
        for line in lines[:10]:  # Analyze first few lines
            line_spaces = [i for i, char in enumerate(line) if char.isspace()]
            spaces.append(set(line_spaces))
            
        # Find common spaces that might indicate column boundaries
        if spaces:
            common_spaces = spaces[0]
            for s in spaces[1:]:
                common_spaces = common_spaces.intersection(s)
                
            # Convert to sorted list
            common_spaces = sorted(list(common_spaces))
            
            # If we found potential boundaries
            if common_spaces:
                # Add start and end positions
                boundaries = [0] + common_spaces + [1000]
                
                # Extract columns using these boundaries
                data = []
                for line in lines:
                    if len(line) < boundaries[1]:
                        continue  # Skip short lines
                    
                    row = []
                    for i in range(len(boundaries) - 1):
                        start = boundaries[i]
                        end = boundaries[i+1]
                        if start >= len(line):
                            break
                        
                        cell = line[start:min(end, len(line))].strip()
                        if cell:  # Only add non-empty cells
                            row.append(cell)
                    
                    if row:  # Only add non-empty rows
                        data.append(row)
                        
                return data
                
        return []
    
    @staticmethod
    def _try_delimiter_detection(lines: List[str]) -> List[List[str]]:
        """Try to extract columns by detecting common delimiters"""
        if not lines:
            return []
            
        # Count potential delimiters
        delimiters = [',', '\t', '|', ':', ';', '  ']
        counts = {}
        
        for delimiter in delimiters:
            total = 0
            consistent = True
            prev_count = -1
            
            for line in lines[:20]:  # Check first few lines
                count = line.count(delimiter)
                total += count
                
                # Check if delimiter count is consistent across lines
                if prev_count >= 0 and count > 0 and count != prev_count:
                    consistent = False
                    
                if count > 0:
                    prev_count = count
            
            counts[delimiter] = {
                'total': total,
                'consistent': consistent
            }
        
        # Find the best delimiter
        best_delimiter = None
        best_score = 0
        
        for delimiter, info in counts.items():
            # Score based on total occurrences and consistency
            score = info['total']
            if info['consistent']:
                score *= 2
                
            if score > best_score:
                best_score = score
                best_delimiter = delimiter
        
        # If we found a good delimiter
        if best_delimiter and best_score > 10:
            data = []
            for line in lines:
                # Split by the delimiter
                if best_delimiter == '  ':  # Special case for multiple spaces
                    row = [col.strip() for col in line.split('  ') if col.strip()]
                else:
                    row = [col.strip() for col in line.split(best_delimiter) if col.strip()]
                    
                if row:  # Only add non-empty rows
                    data.append(row)
                
            return data
                
        return []
    
    @staticmethod
    def _try_line_grouping(lines: List[str]) -> List[List[str]]:
        """Try to group lines into logical rows"""
        if not lines:
            return []
            
        data = []
        current_row = []
        pattern_count = 0
        
        for line in lines:
            # Detect if this looks like a header/title (short line, capitalized, etc.)
            is_header = (
                len(line) < 40 or
                line.isupper() or
                line.endswith(':') or
                all(w[0].isupper() for w in line.split() if w)
            )
            
            # Detect if this looks like data (contains numbers, starts with indent, etc.)
            has_numbers = any(c.isdigit() for c in line)
            
            if is_header and current_row:
                # End previous row and start a new one
                if len(current_row) > 0:
                    data.append(current_row)
                current_row = [line]
                pattern_count = 0
            elif has_numbers and pattern_count > 0:
                # Continue the pattern of data lines
                current_row.append(line)
                pattern_count += 1
            else:
                # Start a new row
                if len(current_row) > 0:
                    data.append(current_row)
                current_row = [line]
                pattern_count = 1
                
        # Add the last row
        if current_row:
            data.append(current_row)
            
        return data
    
    @staticmethod
    def _score_table_structure(data: List[List[str]]) -> float:
        """
        Score the quality of a table structure
        
        Args:
            data: List of rows, where each row is a list of cell values
            
        Returns:
            Score from 0.0 to 10.0, higher is better
        """
        if not data:
            return 0.0
            
        # Calculate various metrics for scoring
        row_count = len(data)
        if row_count <= 1:
            return 1.0
            
        # Calculate column counts for each row
        col_counts = [len(row) for row in data]
        
        # Check consistency of column counts
        if all(c == col_counts[0] for c in col_counts):
            # Perfect consistency
            consistency_score = 3.0
        else:
            # Calculate variance in column counts
            avg_cols = sum(col_counts) / len(col_counts)
            variance = sum((c - avg_cols) ** 2 for c in col_counts) / len(col_counts)
            # Higher variance = lower score
            consistency_score = max(0.0, 3.0 - (variance / 5.0))
            
        # Average number of columns (more columns usually means better structure)
        avg_cols = sum(col_counts) / len(col_counts)
        cols_score = min(3.0, avg_cols / 2.0)
        
        # Content quality score
        content_score = 0.0
        cell_counts = 0
        numeric_cells = 0
        
        for row in data:
            for cell in row:
                cell_counts += 1
                # Check if cell contains numeric content
                if re.search(r'\d', cell):
                    numeric_cells += 1
        
        # Ratio of numeric cells (tables often contain numbers)
        if cell_counts > 0:
            numeric_ratio = numeric_cells / cell_counts
            content_score = numeric_ratio * 2.0
            
        # Row count score (more rows usually means better structure)
        row_score = min(2.0, row_count / 10.0)
            
        # Final score
        total_score = consistency_score + cols_score + content_score + row_score
        return total_score
        
    @staticmethod
    def _try_consistent_patterns(lines: List[str]) -> List[List[str]]:
        """
        Try to extract columns by finding consistent patterns in text
        
        This approach looks for repeating patterns of the same length across lines
        
        Args:
            lines: List of text lines
            
        Returns:
            List of rows, where each row is a list of cell values
        """
        if not lines or len(lines) < 3:
            return []
            
        # Find lines with similar structures based on character types
        def get_pattern(line):
            """Convert a line to a pattern of character types: d=digit, a=alpha, s=space, o=other"""
            pattern = ''
            for c in line:
                if c.isdigit(): pattern += 'd'
                elif c.isalpha(): pattern += 'a'
                elif c.isspace(): pattern += 's'
                else: pattern += 'o'
            return pattern
            
        # Get patterns for each line
        patterns = [get_pattern(line) for line in lines]
        
        # Find groups of lines with similar patterns
        groups = {}
        for i, pattern in enumerate(patterns):
            # Use a simplified version of the pattern (consecutive same chars compressed)
            simple_pattern = ''.join(a for a, _ in itertools.groupby(pattern))
            if simple_pattern not in groups:
                groups[simple_pattern] = []
            groups[simple_pattern].append(i)
            
        # Find the largest group
        largest_group = []
        for group in groups.values():
            if len(group) > len(largest_group):
                largest_group = group
                
        if len(largest_group) < 3:  # Need at least 3 rows with the same pattern
            return []
            
        # Now try to split these lines consistently
        sample_lines = [lines[i] for i in largest_group[:5]]  # Use first 5 lines as samples
        
        # Find common delimiters or patterns
        potential_delims = [',', '\t', '  ', '|', ';', ':']
        best_delim = None
        max_score = 0
        
        for delim in potential_delims:
            # Split each line by this delimiter
            split_lines = []
            for line in sample_lines:
                if delim == '  ':  # Special case for multiple spaces
                    parts = [p for p in re.split(r'\s{2,}', line) if p.strip()]
                else:
                    parts = [p.strip() for p in line.split(delim) if p.strip()]
                split_lines.append(parts)
                
            # Score this delimiter
            col_counts = [len(parts) for parts in split_lines]
            if all(c == col_counts[0] for c in col_counts) and col_counts[0] > 1:
                score = col_counts[0] * len(split_lines)
                if score > max_score:
                    max_score = score
                    best_delim = delim
        
        # If we found a good delimiter, use it to split all lines in the largest group
        if best_delim:
            result = []
            for i in largest_group:
                line = lines[i]
                if best_delim == '  ':  # Special case for multiple spaces
                    parts = [p for p in re.split(r'\s{2,}', line) if p.strip()]
                else:
                    parts = [p.strip() for p in line.split(best_delim) if p.strip()]
                result.append(parts)
            return result
            
        # If no good delimiter found, try fixed width columns for these lines
        space_patterns = []
        for line in sample_lines:
            spaces = [i for i, c in enumerate(line) if c.isspace()]
            space_patterns.append(spaces)
            
        # Find common spaces across lines
        common_spaces = set(space_patterns[0])
        for spaces in space_patterns[1:]:
            common_spaces = common_spaces.intersection(set(spaces))
            
        # If we found common spaces, use them as column separators
        if common_spaces and len(common_spaces) > 0:
            common_spaces = sorted(list(common_spaces))
            result = []
            for i in largest_group:
                line = lines[i]
                start_idx = 0
                parts = []
                for space_idx in common_spaces:
                    if space_idx > start_idx:
                        part = line[start_idx:space_idx].strip()
                        if part:
                            parts.append(part)
                    start_idx = space_idx + 1
                # Add the last part
                if start_idx < len(line):
                    part = line[start_idx:].strip()
                    if part:
                        parts.append(part)
                if parts:
                    result.append(parts)
            return result
            
        return []

def main():
    """
    Test function for the CSV converter
    """
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert PDF data to CSV format")
    parser.add_argument("json_path", help="Path to JSON file with PDF data")
    parser.add_argument("--output-dir", default="output", help="Directory to save the CSV file")
    
    args = parser.parse_args()
    
    try:
        # Load JSON data
        with open(args.json_path, 'r') as f:
            pdf_data = json.load(f)
            
        # Convert to CSV
        base_filename = os.path.splitext(os.path.basename(args.json_path))[0]
        csv_path = CSVConverter.convert_pdf_to_csv(pdf_data, args.output_dir, base_filename)
        
        print(f"Successfully converted to CSV: {csv_path}")
        
    except Exception as e:
        print(f"Error converting to CSV: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
