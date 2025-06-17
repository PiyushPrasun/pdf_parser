#!/usr/bin/env python3
"""
Flask web interface for the PDF Parser application
"""
import os
import uuid
import json
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
from src.pdf_parser import PDFParser
from src.langchain_parser import LangChainPDFParser
from src.csv_converter import CSVConverter

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-session')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

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
                
            for table in result['tables']:
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
    if 'result' not in session:
        return redirect(url_for('index'))
    
    # Get the result from session
    result_data = session['result']
    
    # Make sure csv_files is available in the template
    if 'csv_files' in result_data:
        csv_files = result_data['csv_files']
    else:
        csv_files = []
    
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
