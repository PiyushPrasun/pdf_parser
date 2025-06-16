#!/usr/bin/env python3
"""
OCR Module - Extract text from scanned PDFs and images using Tesseract
"""

import os
import tempfile
from typing import List, Dict, Any, Optional
import pytesseract
from pdf2image import convert_from_path
from PIL import Image


class OCRProcessor:
    """
    A class for extracting text from images and scanned PDFs using Tesseract OCR
    """
    
    def __init__(self, tesseract_path: Optional[str] = None, 
                 tesseract_lang: str = "eng", dpi: int = 300):
        """
        Initialize OCR processor with Tesseract configuration
        
        Args:
            tesseract_path: Path to Tesseract executable (if not in PATH)
            tesseract_lang: Language for OCR (default: English)
            dpi: DPI for PDF to image conversion (higher = better quality but slower)
        """
        self.tesseract_lang = tesseract_lang
        self.dpi = dpi
        
        # Configure Tesseract path if provided
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def is_tesseract_installed(self) -> bool:
        """
        Check if Tesseract is properly installed and accessible
        
        Returns:
            True if Tesseract is installed, False otherwise
        """
        try:
            pytesseract.get_tesseract_version()
            return True
        except pytesseract.TesseractNotFoundError:
            return False
    
    def ocr_image(self, image: Image.Image) -> str:
        """
        Perform OCR on a single image
        
        Args:
            image: PIL Image to process
            
        Returns:
            Extracted text from the image
        """
        return pytesseract.image_to_string(image, lang=self.tesseract_lang)
    
    def _get_pdf_page_image(self, pdf_path: str, page_num: int) -> Image.Image:
        """
        Convert a specific page of a PDF to an image
        
        Args:
            pdf_path: Path to the PDF file
            page_num: Page number to convert (0-based)
            
        Returns:
            PIL Image object of the specified page
        """
        # Convert to list of PIL images with specified DPI
        images = convert_from_path(
            pdf_path, 
            first_page=page_num + 1,  # pdf2image uses 1-based indexing
            last_page=page_num + 1, 
            dpi=self.dpi
        )
        
        if not images:
            raise ValueError(f"Failed to convert page {page_num} to image")
            
        return images[0]
    
    def ocr_pdf_page(self, pdf_path: str, page_num: int) -> str:
        """
        Extract text from a specific PDF page using OCR
        
        Args:
            pdf_path: Path to the PDF file
            page_num: Page number to process (0-based)
            
        Returns:
            Extracted text from the page
        """
        image = self._get_pdf_page_image(pdf_path, page_num)
        return self.ocr_image(image)
    
    def ocr_pdf(self, pdf_path: str, pages: Optional[List[int]] = None) -> Dict[int, str]:
        """
        Extract text from multiple PDF pages using OCR
        
        Args:
            pdf_path: Path to the PDF file
            pages: List of page numbers to process (0-based), or None for all pages
            
        Returns:
            Dictionary mapping page numbers to extracted text
        """
        # Check if file exists
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Check if Tesseract is installed
        if not self.is_tesseract_installed():
            raise RuntimeError("Tesseract OCR is not installed or not found in PATH")
        
        # Get total page count if needed
        if pages is None:
            # Get page count from pdf2image
            images = convert_from_path(pdf_path, dpi=72)  # Low DPI just to get page count
            pages = list(range(len(images)))
        
        # Process each page
        results = {}
        
        for page_num in pages:
            try:
                text = self.ocr_pdf_page(pdf_path, page_num)
                results[page_num] = text
            except Exception as e:
                results[page_num] = f"Error processing page {page_num}: {str(e)}"
        
        return results
    
    def ocr_image_file(self, image_path: str) -> str:
        """
        Perform OCR on an image file
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text from the image
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        # Check if Tesseract is installed
        if not self.is_tesseract_installed():
            raise RuntimeError("Tesseract OCR is not installed or not found in PATH")
            
        # Open and process the image
        with Image.open(image_path) as img:
            return self.ocr_image(img)


if __name__ == "__main__":
    # Simple demo
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ocr_processor.py <pdf_or_image_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    ocr = OCRProcessor()
    
    # Check if Tesseract is installed
    if not ocr.is_tesseract_installed():
        print("Error: Tesseract OCR is not installed or not found in PATH")
        print("Please install Tesseract and make sure it's in your system PATH")
        sys.exit(1)
    
    try:
        # Determine if it's a PDF or image file based on extension
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".pdf":
            # Process first 3 pages for demo purposes
            result = ocr.ocr_pdf(file_path, pages=[0, 1, 2])
            
            print(f"OCR Results for PDF: {file_path}")
            print("-" * 40)
            
            for page_num, text in result.items():
                print(f"Page {page_num + 1}:")
                print(text[:200] + "..." if len(text) > 200 else text)
                print("-" * 40)
                
        else:
            # Assume it's an image file
            result = ocr.ocr_image_file(file_path)
            
            print(f"OCR Results for Image: {file_path}")
            print("-" * 40)
            print(result)
            
    except Exception as e:
        print(f"Error processing file: {str(e)}")
