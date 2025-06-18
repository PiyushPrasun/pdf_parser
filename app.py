#!/usr/bin/env python3
"""
Flask web interface for the PDF Parser application
"""
import os
import uuid
import json
import csv
import tempfile
import shutil
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
from src.pdf_parser import PDFParser
from src.langchain_parser import LangChainPDFParser
from src.csv_converter import CSVConverter

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-session')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Configure file-based session for handling large session data
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'flask_session')
app.config['SESSION_PERMANENT'] = False

# Create the session directory if it doesn't exist
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

# Enable larger session size
try:
    from flask_session import Session
    Session(app)
except ImportError:
    print("Using default session storage. Install flask-session for better session handling.")
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'flask_session_pdf_parser')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_THRESHOLD'] = 100  # Number of sessions stored in memory
app.config['SESSION_PERMANENT'] = False

# Create session directory if it doesn't exist
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

# Setup Flask-Session
from flask_session import Session
Session(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_result_to_json(result, filename):
    """Save parsing results to a JSON file and return the path"""
    # Remove objects that can't be serialized to JSON
    if 'langchain_docs' in result:
        del result['langchain_docs']
    
    if 'langchain_chunks' in result:
        # Convert LangChain Document objects to dictionaries
        result['langchain_chunks'] = [
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in result['langchain_chunks']
        ]
    
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    return output_path

def filter_tables_for_display(tables):
    """Filter out low-quality tables for display
    
    Args:
        tables: List of table dictionaries
        
    Returns:
        Filtered list of tables
    """
    if not tables:
        return []
        
    filtered = []
    
    for table in tables:
        # Get basic metrics
        shape = table.get('shape', (0, 0))
        rows = table.get('rows', [])
        accuracy = table.get('accuracy', 1.0)
        
        # Must have reasonable dimensions (at least 2x2)
        if shape[0] < 2 or shape[1] < 2:
            continue
            
        # Must have adequate accuracy
        if accuracy is not None and accuracy < 0.4:
            continue
            
        # Must have actual data
        if not rows or len(rows) < 2:
            continue
            
        # Check for content quality
        non_empty_cells = 0
        total_cells = 0
        unique_content = set()
        
        for row in rows:
            for cell in row:
                total_cells += 1
                cell_str = str(cell).strip() if cell else ""
                if cell_str:
                    non_empty_cells += 1
                    unique_content.add(cell_str.lower())
        
        # Must have sufficient non-empty content (at least 40%)
        if total_cells == 0 or non_empty_cells / total_cells < 0.4:
            continue
            
        # Must have reasonable content diversity (at least 4 unique values)
        if len(unique_content) < 4:
            continue
            
        # Check that we don't have tables that are just repeated headers
        header_like_rows = 0
        for row in rows:
            row_content = [str(cell).strip().lower() for cell in row if str(cell).strip()]
            if any(word in content for content in row_content 
                   for word in ['column', 'header', 'title', 'name', 'field', 'table']):
                header_like_rows += 1
        
        # Skip if more than half the rows look like headers/metadata
        if header_like_rows > len(rows) / 2:
            continue
            
        filtered.append(table)
    
    # Sort by quality metrics (accuracy and content richness)
    filtered.sort(key=lambda t: (
        t.get('accuracy', 0), 
        t.get('shape', (0, 0))[0] * t.get('shape', (0, 0))[1],
        len(set(str(cell).strip().lower() for row in t.get('rows', []) for cell in row if str(cell).strip()))
    ), reverse=True)
    
    # Limit to top 3 tables to avoid UI clutter
    return filtered[:3]

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file. Please upload a PDF'}), 400
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    base_name = os.path.splitext(filename)[0]
    saved_filename = f"{base_name}_{unique_id}.pdf"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
    
    # Save the uploaded file
    file.save(file_path)
    
    # Get parsing options from form
    use_langchain = 'use_langchain' in request.form
    metadata_only = 'metadata_only' in request.form
    use_ocr = 'use_ocr' in request.form
    force_ocr = 'force_ocr' in request.form
    extract_tables = 'extract_tables' in request.form
    export_csv = 'export_csv' in request.form
    table_flavour = request.form.get('table_flavour', 'lattice')
    chunk_size = int(request.form.get('chunk_size', 1000))
    chunk_overlap = int(request.form.get('chunk_overlap', 200))
    
    try:
        # Process the PDF file
        if use_langchain:
            parser = LangChainPDFParser(chunk_size, chunk_overlap)
            result = parser.process_pdf(file_path)
        else:
            parser = PDFParser(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_ocr=use_ocr,
                extract_tables=extract_tables,
                table_flavour=table_flavour
            )
            
            # Set up CSV output directory if needed
            csv_output_dir = None
            if export_csv and extract_tables:
                csv_output_dir = app.config['UPLOAD_FOLDER']
            
            if metadata_only:
                result = {"metadata": parser.extract_metadata(file_path)}
            else:
                result = parser.parse_pdf(
                    pdf_path=file_path, 
                    force_ocr=force_ocr,
                    output_dir=csv_output_dir
                )
        
        # Save result to JSON
        json_filename = f"{base_name}_{unique_id}_parsed.json"
        json_path = save_result_to_json(result, json_filename)
        
        # Process tables for HTML display if present
        table_html = []
        csv_files = []
        
        if 'tables' in result and result['tables']:
            # Create HTML representation for each table
            if not hasattr(parser, 'table_extractor') or not parser.table_extractor:
                from src.table_extractor import TableExtractor
                table_extractor = TableExtractor()
            else:
                table_extractor = parser.table_extractor
                
            # Filter and process tables
            filtered_tables = filter_tables_for_display(result['tables'])
            
            # Replace the tables in the result with filtered tables
            result['tables'] = filtered_tables
            
            # Generate HTML for each table
            for table in filtered_tables:
                table['html'] = table_extractor.get_table_html(table)
                
        # Get any table CSV paths if available
        if 'table_csv_paths' in result:
            csv_files.extend(result['table_csv_paths'])
            
        # Get text CSV path if available
        text_csv_path = result.get('text_csv_path')
        if text_csv_path and text_csv_path not in csv_files:
            csv_files.append(text_csv_path)
            
        # Always generate a consolidated CSV file using our robust converter
        csv_filename = f"{base_name}_{unique_id}_data.csv"
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
        
        try:
            # Use our new CSV converter to create a robust CSV representation
            # This will work even if table extraction was disabled
            # It will convert raw text to tabular form if no tables were found
            csv_converter_path = CSVConverter.convert_pdf_to_csv(
                result, 
                app.config['UPLOAD_FOLDER'], 
                f"{base_name}_{unique_id}"
            )
            
            # Add this to our list of CSV files and make sure it's the first one
            # so it becomes the main CSV download
            if csv_converter_path not in csv_files:
                csv_files.insert(0, csv_converter_path)
        except Exception as e:
            print(f"CSV conversion error: {str(e)}")
            # Fallback - create a simple CSV with just the text if conversion fails
            try:
                with open(csv_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Content"])
                    writer.writerow([result.get('text', '')])
                csv_files.insert(0, csv_path)
            except Exception as inner_e:
                print(f"Simple CSV fallback error: {str(inner_e)}")
        
        # Store filenames in session for result page
        session['pdf_filename'] = saved_filename
        session['json_filename'] = json_filename
        session['result'] = {
            'filename': filename,
            'pdf_path': saved_filename,
            'json_path': json_filename,
            'metadata': result.get('metadata', {}),
            'text_length': len(result.get('text', '')),
            'chunk_count': result.get('custom_chunk_count', len(result.get('chunks', []))),
            'use_langchain': use_langchain,
            'langchain_chunk_count': result.get('langchain_chunk_count', 0) if use_langchain else 0,
            'ocr_used': result.get('ocr_used', False),
            'tables': result.get('tables', []),
            'csv_files': csv_files,
            'text_csv_path': result.get('text_csv_path')
        }
        
        return jsonify({
            'success': True, 
            'redirect': url_for('result')
        })
    
    except Exception as e:
        # If an error occurs, clean up the uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': str(e)}), 500

@app.route('/result')
def result():
    """Display parsing results"""
    try:
        if 'result' not in session:
            flash("No processing results found. Please upload a PDF file.", "warning")
            return redirect(url_for('index'))
        
        # Get the result from session
        result_data = session.get('result', {})
        
        # Make sure csv_files is available in the template
        if 'csv_files' in result_data:
            csv_files = result_data['csv_files']
        else:
            csv_files = []
    except Exception as e:
        print(f"Error retrieving session data: {str(e)}")
        flash("An error occurred while retrieving results. Please try uploading again.", "error")
        return redirect(url_for('index'))
    
    # Convert csv_files to just the filenames (not full paths) for the template
    # so they work with the download_file route
    csv_filenames = []
    main_csv = None
    for path in csv_files:
        filename = os.path.basename(path)
        if '_data.csv' in filename and not main_csv:
            main_csv = filename  # This is our primary CSV file
        csv_filenames.append(filename)
    
    # If no main CSV file was found but we have other CSV files, use the first one
    if not main_csv and csv_filenames:
        main_csv = csv_filenames[0]
        
    return render_template('result.html', result=result_data, csv_files=csv_filenames, main_csv=main_csv)

@app.route('/download/<filename>')
def download_file(filename):
    """Download the processed JSON file"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/pdf/<filename>')
def view_pdf(filename):
    """View the uploaded PDF file"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the PDF Parser Flask application")
    parser.add_argument('--port', type=int, default=5000, help='Port to run the application on')
    args = parser.parse_args()
    
    app.run(debug=True, host='0.0.0.0', port=args.port)
