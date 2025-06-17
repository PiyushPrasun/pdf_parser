# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    ghostscript \
    libxrender1 \
    libfontconfig1 \
    libxext6 \
    tesseract-ocr \
    tesseract-ocr-eng \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads exports notebook_exports

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=5000
ENV SECRET_KEY=default-secret-key

# Expose port
EXPOSE 5000

# Start command
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "600", "app:app"]
