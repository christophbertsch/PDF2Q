#!/usr/bin/env python3
"""
PDF Extraction Microservice
Dedicated service for reliable PDF text extraction using multiple methods
Supports PDF, text files, and OCR for images
Designed for deployment on Render.com
"""

import os
import base64
import json
import logging
import tempfile
import subprocess
import re
import unicodedata
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
from werkzeug.exceptions import BadRequest
import magic
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def clean_extracted_text(text):
    """
    Clean and normalize extracted text, especially for German characters
    
    Args:
        text: Raw extracted text
        
    Returns:
        str: Cleaned and normalized text
    """
    if not text:
        return ""
    
    # Normalize Unicode characters (especially important for German umlauts)
    text = unicodedata.normalize('NFKC', text)
    
    # Remove control characters but keep newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
    
    # Fix common encoding issues with German characters
    replacements = {
        'Ã¤': 'ä', 'Ã¶': 'ö', 'Ã¼': 'ü', 'ÃŸ': 'ß',
        'Ã„': 'Ä', 'Ã–': 'Ö', 'Ãœ': 'Ü',
        'â‚¬': '€', 'â€œ': '"', 'â€': '"', 'â€™': "'",
        'â€¦': '...', 'â€"': '–', 'â€"': '—'
    }
    
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    # Remove excessive whitespace while preserving paragraph structure
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 consecutive newlines
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
    text = re.sub(r' *\n *', '\n', text)  # Remove spaces around newlines
    
    return text.strip()

def is_text_readable(text, min_readable_ratio=0.7):
    """
    Check if extracted text is readable (not garbled)
    
    Args:
        text: Text to check
        min_readable_ratio: Minimum ratio of readable characters
        
    Returns:
        bool: True if text appears readable
    """
    if not text or len(text.strip()) < 10:
        return False
    
    # Count readable characters (letters, numbers, common punctuation, spaces)
    readable_chars = len(re.findall(r'[a-zA-ZäöüßÄÖÜ0-9\s.,;:!?()[\]{}"\'-]', text))
    total_chars = len(text)
    
    if total_chars == 0:
        return False
    
    readable_ratio = readable_chars / total_chars
    return readable_ratio >= min_readable_ratio

def extract_pdf_text_reliable(pdf_bytes):
    """
    Extract text from PDF bytes using multiple fallback methods
    
    Args:
        pdf_bytes: PDF file as bytes
        
    Returns:
        dict: Extraction result with success status, text, and metadata
    """
    try:
        # Method 1: PyPDF2 with enhanced German text handling
        try:
            pdf_stream = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            # Get number of pages
            num_pages = len(pdf_reader.pages)
            logger.info(f"PDF has {num_pages} pages")
            
            # Extract text from all pages
            extracted_text = ""
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
            
            # Clean and normalize the text for German characters
            extracted_text = clean_extracted_text(extracted_text)
            
            # Check if text is readable
            is_readable = is_text_readable(extracted_text)
            
            # Get metadata
            metadata = {}
            if pdf_reader.metadata:
                metadata = {
                    'title': pdf_reader.metadata.get('/Title', ''),
                    'author': pdf_reader.metadata.get('/Author', ''),
                    'subject': pdf_reader.metadata.get('/Subject', ''),
                    'creator': pdf_reader.metadata.get('/Creator', ''),
                    'producer': pdf_reader.metadata.get('/Producer', ''),
                    'creation_date': str(pdf_reader.metadata.get('/CreationDate', '')),
                    'modification_date': str(pdf_reader.metadata.get('/ModDate', ''))
                }
            
            if extracted_text and len(extracted_text.strip()) > 10 and is_readable:
                logger.info(f"PyPDF2 extracted {len(extracted_text)} characters from {num_pages} pages (readable: {is_readable})")
                return {
                    'success': True,
                    'text': extracted_text,
                    'text_length': len(extracted_text),
                    'pages': num_pages,
                    'metadata': metadata,
                    'method': 'PyPDF2-enhanced',
                    'error': None
                }
            else:
                logger.warning(f"PyPDF2 extracted text but quality insufficient (readable: {is_readable}), trying fallback methods")
                
        except Exception as e:
            logger.warning(f"PyPDF2 failed: {str(e)}, trying fallback methods")
        
        # Method 2: pdfplumber fallback with text cleaning
        try:
            import pdfplumber
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                extracted_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
                
                # Clean and normalize the text
                extracted_text = clean_extracted_text(extracted_text)
                is_readable = is_text_readable(extracted_text)
                
                if extracted_text and len(extracted_text.strip()) > 10 and is_readable:
                    logger.info(f"pdfplumber extracted {len(extracted_text)} characters (readable: {is_readable})")
                    return {
                        'success': True,
                        'text': extracted_text,
                        'text_length': len(extracted_text),
                        'pages': len(pdf.pages),
                        'metadata': {},
                        'method': 'pdfplumber-enhanced',
                        'error': None
                    }
        except ImportError:
            logger.info("pdfplumber not available")
        except Exception as e:
            logger.warning(f"pdfplumber failed: {str(e)}")
        
        # Method 3: pdfminer fallback with text cleaning
        try:
            from pdfminer.high_level import extract_text
            extracted_text = extract_text(BytesIO(pdf_bytes))
            
            # Clean and normalize the text
            extracted_text = clean_extracted_text(extracted_text)
            is_readable = is_text_readable(extracted_text)
            
            if extracted_text and len(extracted_text.strip()) > 10 and is_readable:
                logger.info(f"pdfminer extracted {len(extracted_text)} characters (readable: {is_readable})")
                return {
                    'success': True,
                    'text': extracted_text,
                    'text_length': len(extracted_text),
                    'pages': 1,  # pdfminer doesn't easily give page count
                    'metadata': {},
                    'method': 'pdfminer-enhanced',
                    'error': None
                }
        except ImportError:
            logger.info("pdfminer not available")
        except Exception as e:
            logger.warning(f"pdfminer failed: {str(e)}")
        
        # If all methods fail
        return {
            'success': False,
            'text': '',
            'text_length': 0,
            'pages': 0,
            'metadata': {},
            'method': 'none',
            'error': 'All PDF extraction methods failed'
        }
        
    except Exception as e:
        logger.error(f"PDF extraction completely failed: {str(e)}")
        return {
            'success': False,
            'text': '',
            'text_length': 0,
            'pages': 0,
            'metadata': {},
            'method': 'none',
            'error': str(e)
        }

def extract_text_from_image(image_bytes, filename):
    """
    Extract text from image using OCR (Tesseract)
    
    Args:
        image_bytes: Image file as bytes
        filename: Original filename
        
    Returns:
        dict: Extraction result with success status and text
    """
    try:
        # Try to use pytesseract for OCR
        try:
            import pytesseract
            from PIL import Image
            
            # Open image from bytes
            image = Image.open(BytesIO(image_bytes))
            
            # Perform OCR with German and English language support
            extracted_text = pytesseract.image_to_string(image, lang='deu+eng')
            
            if extracted_text and len(extracted_text.strip()) > 5:
                logger.info(f"OCR extracted {len(extracted_text)} characters from image")
                return {
                    'success': True,
                    'text': f"Image Document: {filename}\n\nOCR Extracted Content:\n{extracted_text.strip()}",
                    'text_length': len(extracted_text.strip()),
                    'pages': 1,
                    'metadata': {'ocr': True, 'image_format': image.format},
                    'method': 'OCR-pytesseract',
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'text': f"Image Document: {filename}\n\nOCR failed to extract readable text",
                    'text_length': 0,
                    'pages': 1,
                    'metadata': {'ocr': True},
                    'method': 'OCR-failed',
                    'error': 'OCR extracted insufficient text'
                }
                
        except ImportError:
            logger.warning("pytesseract not available for OCR")
            return {
                'success': False,
                'text': f"Image Document: {filename}\n\nOCR not available - pytesseract not installed",
                'text_length': 0,
                'pages': 1,
                'metadata': {'ocr': False},
                'method': 'OCR-unavailable',
                'error': 'OCR library not available'
            }
            
    except Exception as e:
        logger.error(f"Image OCR failed: {str(e)}")
        return {
            'success': False,
            'text': f"Image Document: {filename}\n\nOCR processing failed",
            'text_length': 0,
            'pages': 1,
            'metadata': {'ocr': False},
            'method': 'OCR-error',
            'error': str(e)
        }

def extract_text_from_file(file_bytes, filename, mime_type):
    """
    Extract text from various file types
    
    Args:
        file_bytes: File content as bytes
        filename: Original filename
        mime_type: MIME type of the file
        
    Returns:
        dict: Extraction result with success status and text
    """
    try:
        # Handle text files with enhanced encoding detection
        if mime_type.startswith('text/'):
            text_content = None
            encoding_used = 'unknown'
            
            # Try multiple encodings in order of preference for German text
            encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings_to_try:
                try:
                    text_content = file_bytes.decode(encoding)
                    encoding_used = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, use utf-8 with error handling
            if text_content is None:
                text_content = file_bytes.decode('utf-8', errors='replace')
                encoding_used = 'utf-8-replace'
            
            # Clean the text content
            text_content = clean_extracted_text(text_content)
            
            return {
                'success': True,
                'text': f"Text Document: {filename}\n\nContent:\n{text_content}",
                'text_length': len(text_content),
                'pages': 1,
                'metadata': {'encoding': encoding_used},
                'method': 'text-enhanced',
                'error': None
            }
        
        # Handle PDF files
        elif mime_type == 'application/pdf':
            return extract_pdf_text_reliable(file_bytes)
        
        # Handle image files
        elif mime_type.startswith('image/'):
            return extract_text_from_image(file_bytes, filename)
        
        # Unsupported file type
        else:
            return {
                'success': False,
                'text': f"Unsupported file type: {mime_type}",
                'text_length': 0,
                'pages': 0,
                'metadata': {'mime_type': mime_type},
                'method': 'unsupported',
                'error': f'Unsupported file type: {mime_type}'
            }
            
    except Exception as e:
        logger.error(f"File extraction failed: {str(e)}")
        return {
            'success': False,
            'text': '',
            'text_length': 0,
            'pages': 0,
            'metadata': {},
            'method': 'error',
            'error': str(e)
        }

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'service': 'PDF Extraction Service',
        'version': '1.1.0',
        'python_version': os.sys.version,
        'libraries': {
            'PyPDF2': PyPDF2.__version__,
            'Flask': '2.3.3'
        },
        'features': ['multi-format', 'german-encoding', 'ocr', 'fallback-methods'],
        'last_updated': '2025-08-15'
    })

@app.route('/extract', methods=['POST'])
def extract_document():
    """
    Extract text from uploaded document (PDF, text, or image files)
    
    Accepts:
    - Multipart form data with 'file' field
    - JSON with base64 encoded file data
    
    Returns:
    - JSON with extraction results
    """
    try:
        file_bytes = None
        filename = 'unknown'
        mime_type = None
        
        # Handle multipart form data
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                raise BadRequest('No file selected')
            
            filename = file.filename
            file_bytes = file.read()
            
            # Detect MIME type
            try:
                mime_type = magic.from_buffer(file_bytes, mime=True)
            except:
                # Fallback to content type from request
                mime_type = file.content_type or 'application/octet-stream'
            
            logger.info(f"Received file upload: {filename} ({len(file_bytes)} bytes, {mime_type})")
        
        # Handle JSON with base64 data
        elif request.is_json:
            data = request.get_json()
            if 'data' not in data:
                raise BadRequest('Missing base64 data field')
            
            try:
                file_bytes = base64.b64decode(data['data'])
                filename = data.get('filename', 'unknown')
                mime_type = data.get('mime_type')
                
                # Detect MIME type if not provided
                if not mime_type:
                    try:
                        mime_type = magic.from_buffer(file_bytes, mime=True)
                    except:
                        mime_type = 'application/octet-stream'
                
                logger.info(f"Received base64 data: {filename} ({len(file_bytes)} bytes, {mime_type})")
            except Exception as e:
                raise BadRequest(f'Invalid base64 data: {str(e)}')
        
        else:
            raise BadRequest('No file data provided. Send either multipart form data with "file" field or JSON with base64 "data" field')
        
        # Validate file bytes
        if not file_bytes or len(file_bytes) < 10:
            raise BadRequest('Invalid or empty file data')
        
        # Extract text using appropriate method
        result = extract_text_from_file(file_bytes, filename, mime_type)
        
        # Add filename and mime_type to result
        result['filename'] = filename
        result['mime_type'] = mime_type
        
        logger.info(f"Extraction completed: {result['success']}, {result['text_length']} characters, method: {result.get('method', 'unknown')}")
        
        return jsonify(result)
        
    except BadRequest as e:
        logger.error(f"Bad request: {str(e)}")
        return jsonify({
            'success': False,
            'text': '',
            'text_length': 0,
            'pages': 0,
            'metadata': {},
            'method': 'error',
            'error': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'success': False,
            'text': '',
            'text_length': 0,
            'pages': 0,
            'metadata': {},
            'method': 'error',
            'error': f'Internal server error: {str(e)}'
        }), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint with sample PDF processing"""
    # Create a simple test PDF content
    test_text = "This is a test PDF extraction service response."
    
    return jsonify({
        'status': 'Test successful',
        'service': 'PDF Extraction Service',
        'test_result': {
            'success': True,
            'text': test_text,
            'text_length': len(test_text),
            'pages': 1,
            'metadata': {'test': True},
            'error': None
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting PDF Extraction Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)