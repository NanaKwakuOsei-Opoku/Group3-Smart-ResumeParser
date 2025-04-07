"""
PyMuPDF wrapper to handle different import methods
"""
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    import pymupdf
    logger.debug("Imported pymupdf")
    
    # Export the pymupdf module as fitz
    fitz = pymupdf
except ImportError:
    try:
        logger.debug("Trying to import PyMuPDF")
        import PyMuPDF
        fitz = PyMuPDF
    except ImportError:
        try:
            logger.debug("Trying to import direct fitz module")
            import fitz
        except ImportError:
            logger.error("Failed to import any version of PyMuPDF")
            raise ImportError("Could not import PyMuPDF. Please install it with 'pip install PyMuPDF'.")