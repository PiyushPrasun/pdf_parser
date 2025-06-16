#!/usr/bin/env python3
"""
PDF Parser with LangChain Integration
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document

from src.pdf_parser import PDFParser

class LangChainPDFParser:
    """
    Enhanced PDF Parser with LangChain integration for advanced document processing
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, 
                 use_ocr: bool = False, tesseract_path: Optional[str] = None):
        """
        Initialize the LangChain PDF parser
        
        Args:
            chunk_size: Maximum size of text chunks
            chunk_overlap: Overlap between chunks to maintain context
            use_ocr: Whether to use OCR for text extraction from scanned documents
            tesseract_path: Path to Tesseract executable (if not in PATH)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_ocr = use_ocr
        self.pdf_parser = PDFParser(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap,
            use_ocr=use_ocr, 
            tesseract_path=tesseract_path
        )
        
    def load_pdf_with_langchain(self, pdf_path: str) -> List[Document]:
        """
        Load PDF using LangChain's PyPDFLoader
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of LangChain Document objects
        """
        loader = PyPDFLoader(pdf_path)
        return loader.load()
    
    def split_text_langchain(self, text: str) -> List[Document]:
        """
        Split text using LangChain's RecursiveCharacterTextSplitter
        
        Args:
            text: Text to split
            
        Returns:
            List of Document objects containing text chunks
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        
        return splitter.create_documents([text])
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a PDF file using both custom parser and LangChain
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with processing results
        """
        # Use our custom parser to extract text and metadata
        custom_results = self.pdf_parser.parse_pdf(pdf_path)
        
        # Use LangChain to load and process the document
        try:
            langchain_docs = self.load_pdf_with_langchain(pdf_path)
            langchain_chunks = self.split_text_langchain(custom_results["text"])
            
            return {
                "text": custom_results["text"],
                "metadata": custom_results["metadata"],
                "custom_chunks": custom_results["chunks"],
                "langchain_docs": langchain_docs,
                "langchain_chunks": langchain_chunks,
                "custom_chunk_count": len(custom_results["chunks"]),
                "langchain_chunk_count": len(langchain_chunks)
            }
        except Exception as e:
            # Fall back to just our custom parser results if LangChain has issues
            return {
                "text": custom_results["text"],
                "metadata": custom_results["metadata"],
                "custom_chunks": custom_results["chunks"],
                "error": f"LangChain processing failed: {str(e)}"
            }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python langchain_parser.py <pdf_file_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    parser = LangChainPDFParser()
    
    try:
        result = parser.process_pdf(pdf_path)
        
        print(f"Metadata: {result['metadata']}")
        print(f"Custom chunks: {result['custom_chunk_count']}")
        
        if 'langchain_chunk_count' in result:
            print(f"LangChain chunks: {result['langchain_chunk_count']}")
            print(f"First LangChain chunk: {result['langchain_chunks'][0].page_content[:100]}...")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error processing PDF: {e}")
