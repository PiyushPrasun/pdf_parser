# PDF Parser package
from src.pdf_parser import PDFParser
from src.langchain_parser import LangChainPDFParser

# Import OCR processor if available
try:
    from src.ocr_processor import OCRProcessor
    __all__ = ['PDFParser', 'LangChainPDFParser', 'OCRProcessor']
except ImportError:
    __all__ = ['PDFParser', 'LangChainPDFParser']
