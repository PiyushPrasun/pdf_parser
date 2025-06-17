#!/bin/bash

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads

# Install system dependencies for table extraction (if not already installed)
if ! command -v apt-get &> /dev/null; then
    echo "Warning: apt-get not found. Skipping system dependencies installation."
else
    echo "Installing system dependencies for table extraction..."
    apt-get update -y
    apt-get install -y ghostscript libxrender1 libfontconfig1 libxext6 
fi

echo "Starting PDF Parser web application..."
gunicorn --bind=0.0.0.0 --timeout 600 app:app
