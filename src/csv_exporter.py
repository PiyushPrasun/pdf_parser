#!/usr/bin/env python3
"""
CSV Exporter Module - Export PDF content to CSV files
"""

import os
import csv
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple

class CSVExporter:
    """
    A class for exporting data from PDFs to CSV files
    """
    
    @staticmethod
    def export_tables_to_csv(tables: List[Dict], output_dir: str, base_filename: str) -> List[str]:
        """
        Save extracted tables to CSV files with improved formatting
        
        Args:
            tables: List of table dictionaries from table extractor
            output_dir: Directory to save CSV files
            base_filename: Base filename for CSV files
            
        Returns:
            List of paths to saved CSV files
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        csv_paths = []
        
        # If only one meaningful table, don't add table number suffix
        if len(tables) == 1:
            csv_filename = f"{base_filename}.csv"
        else:
            # Multiple tables, use numbered approach
            for i, table in enumerate(tables):
                csv_filename = f"{base_filename}_table_{i+1}.csv"
                csv_path = os.path.join(output_dir, csv_filename)
                
                # Create DataFrame with proper formatting
                df = CSVExporter._create_formatted_dataframe(table)
                
                # Save to CSV with proper encoding and formatting
                df.to_csv(csv_path, index=False, encoding='utf-8-sig', 
                         quoting=csv.QUOTE_MINIMAL)
                csv_paths.append(csv_path)
            
            return csv_paths
        
        # Single table case
        csv_path = os.path.join(output_dir, csv_filename)
        df = CSVExporter._create_formatted_dataframe(tables[0])
        df.to_csv(csv_path, index=False, encoding='utf-8-sig', 
                 quoting=csv.QUOTE_MINIMAL)
        csv_paths.append(csv_path)
        
        return csv_paths
    
    @staticmethod
    def _create_formatted_dataframe(table: Dict) -> pd.DataFrame:
        """
        Create a well-formatted DataFrame from table data
        
        Args:
            table: Table dictionary
            
        Returns:
            Formatted pandas DataFrame
        """
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        if not rows:
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Set proper column names
        if headers and len(headers) == df.shape[1]:
            df.columns = headers
        else:
            df.columns = [f"Column_{i+1}" for i in range(df.shape[1])]
        
        # Clean up the data
        df = df.replace('', None)  # Convert empty strings to None
        df = df.dropna(how='all', axis=0)  # Drop completely empty rows
        df = df.dropna(how='all', axis=1)  # Drop completely empty columns
        
        # Clean individual cells
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            # Convert 'nan' strings back to empty
            df[col] = df[col].replace('nan', '')
        
        # Try to infer and convert data types
        for col in df.columns:
            # Try to convert to numeric if possible
            numeric_series = pd.to_numeric(df[col], errors='coerce')
            if not numeric_series.isna().all():
                # If more than 50% of values are numeric, convert the column
                numeric_ratio = numeric_series.notna().sum() / len(df)
                if numeric_ratio > 0.5:
                    df[col] = numeric_series
        
        return df
    
    @staticmethod
    def export_text_as_csv(text: str, output_dir: str, base_filename: str) -> str:
        """
        Convert raw text into a CSV file, trying to detect tabular structure
        
        Args:
            text: Raw text from PDF
            output_dir: Directory to save CSV file
            base_filename: Base filename for CSV file
            
        Returns:
            Path to saved CSV file
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        csv_filename = f"{base_filename}_text.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        # Try to detect delimiter and row structure
        lines = text.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        
        # Count potential delimiters
        delimiters = [',', '\t', '|', ';']
        delimiter_counts = {d: sum(line.count(d) for line in lines) for d in delimiters}
        
        # Find most common delimiter
        max_count = max(delimiter_counts.values())
        best_delimiter = next((d for d, c in delimiter_counts.items() if c == max_count), ',')
        
        # If no good delimiter found, try to detect fixed width columns
        if max_count == 0:
            # Try to detect consistent spacing that might indicate columns
            # This is a simple heuristic that won't work for all fixed-width formats
            data = []
            for line in lines:
                # Split by multiple spaces (2 or more)
                row = [col.strip() for col in line.split('  ') if col.strip()]
                if row:
                    data.append(row)
        else:
            # Parse using the detected delimiter
            data = []
            for line in lines:
                row = [col.strip() for col in line.split(best_delimiter)]
                data.append(row)
        
        # Determine the maximum number of columns
        if data:
            max_cols = max(len(row) for row in data)
            
            # Pad rows to have the same number of columns
            data = [row + [''] * (max_cols - len(row)) for row in data]
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Use first row as header if it looks like a header
            if df.shape[0] > 1:
                has_header = True
                for idx, val in enumerate(df.iloc[0]):
                    # If first row has numeric values, it's probably not a header
                    if pd.api.types.is_numeric_dtype(pd.Series([val])):
                        has_header = False
                        break
                
                if has_header:
                    df.columns = df.iloc[0]
                    df = df.iloc[1:].reset_index(drop=True)
            
            # Write to CSV
            df.to_csv(csv_path, index=False)
            return csv_path
        
        # Fallback if no data could be extracted
        with open(csv_path, 'w', newline='') as f:
            f.write(text)
        
        return csv_path
    
    @staticmethod
    def export_raw_json_as_csv(json_path: str, output_dir: str) -> List[str]:
        """
        Convert data from JSON to CSV files
        
        Args:
            json_path: Path to the JSON file
            output_dir: Directory to save CSV files
            
        Returns:
            List of paths to saved CSV files
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        csv_paths = []
        
        try:
            # Load JSON data
            with open(json_path, 'r') as f:
                data = json.load(f)
                
            base_filename = os.path.splitext(os.path.basename(json_path))[0]
            
            # Check for tables in the JSON
            if 'tables' in data and isinstance(data['tables'], list):
                csv_paths.extend(CSVExporter.export_tables_to_csv(
                    data['tables'], output_dir, base_filename
                ))
                
            # Export text content as CSV if available
            if 'text' in data and data['text']:
                text_csv = CSVExporter.export_text_as_csv(
                    data['text'], output_dir, base_filename
                )
                csv_paths.append(text_csv)
                
            # Export chunks as separate CSVs if available
            if 'chunks' in data and isinstance(data['chunks'], list):
                for i, chunk in enumerate(data['chunks']):
                    if isinstance(chunk, str) and chunk.strip():
                        chunk_csv = CSVExporter.export_text_as_csv(
                            chunk, output_dir, f"{base_filename}_chunk_{i+1}"
                        )
                        csv_paths.append(chunk_csv)
                        
        except Exception as e:
            print(f"Error exporting JSON to CSV: {str(e)}")
            
        return csv_paths


def main():
    """
    Main function for testing
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Export PDF content to CSV")
    parser.add_argument("json_path", help="Path to the JSON file with parsed PDF data")
    parser.add_argument("--output-dir", default="outputs", help="Directory to save CSV files")
    
    args = parser.parse_args()
    
    try:
        csv_paths = CSVExporter.export_raw_json_as_csv(args.json_path, args.output_dir)
        
        print(f"Exported {len(csv_paths)} CSV files:")
        for path in csv_paths:
            print(f"  {path}")
            
    except Exception as e:
        print(f"Error exporting to CSV: {str(e)}")


if __name__ == "__main__":
    main()
