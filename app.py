#!/usr/bin/env python3
"""
PDF Extraction Microservice
Dedicated service for reliable PDF text extraction using PyPDF2
Designed for deployment on Render.com
"""

import os
import base64
import json
import logging
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
from werkzeug.exceptions import BadRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def extract_pdf_text(pdf_bytes):
    """
    Extract text from PDF bytes using multiple methods with encoding support
    
    Args:
        pdf_bytes: PDF file as bytes
        
    Returns:
        dict: Extraction result with success status, text, and metadata
    """
    
    # Method 1: Try PyPDF2 with enhanced text extraction
    try:
        logger.info("Attempting PyPDF2 extraction...")
        pdf_stream = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_stream)
        
        # Get number of pages
        num_pages = len(pdf_reader.pages)
        logger.info(f"PDF has {num_pages} pages")
        
        # Extract text from all pages with enhanced extraction
        extracted_text = ""
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            
            # Try multiple extraction methods for each page
            page_text = ""
            
            # Standard extraction
            try:
                page_text = page.extract_text()
            except Exception as e:
                logger.warning(f"Standard extraction failed for page {page_num}: {e}")
            
            # If standard extraction fails or returns minimal text, try alternative methods
            if not page_text or len(page_text.strip()) < 10:
                try:
                    # Try extracting with different parameters
                    page_text = page.extract_text(extraction_mode="layout")
                except:
                    try:
                        # Fallback to basic extraction
                        page_text = page.extract_text(extraction_mode="plain")
                    except:
                        logger.warning(f"All extraction methods failed for page {page_num}")
            
            if page_text:
                extracted_text += page_text + "\n"
        
        # Clean up the text and handle encoding
        extracted_text = extracted_text.strip()
        
        # Apply text cleaning for German documents
        if extracted_text:
            extracted_text = clean_extracted_text(extracted_text)
        
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
        
        if extracted_text and len(extracted_text.strip()) > 10:
            logger.info(f"PyPDF2 extraction successful: {len(extracted_text)} characters")
            return {
                'success': True,
                'text': extracted_text,
                'text_length': len(extracted_text),
                'pages': num_pages,
                'metadata': metadata,
                'method': 'PyPDF2',
                'error': None
            }
        else:
            logger.warning("PyPDF2 extracted minimal text, trying fallback methods...")
            
    except Exception as e:
        logger.error(f"PyPDF2 extraction failed: {str(e)}")
    
    # Method 2: Try basic binary text extraction as fallback
    try:
        logger.info("Attempting basic binary extraction...")
        extracted_text = extract_text_from_binary(pdf_bytes)
        
        if extracted_text and len(extracted_text.strip()) > 10:
            logger.info(f"Binary extraction successful: {len(extracted_text)} characters")
            return {
                'success': True,
                'text': extracted_text,
                'text_length': len(extracted_text),
                'pages': 1,  # Unknown page count for binary extraction
                'metadata': {},
                'method': 'Binary',
                'error': None
            }
            
    except Exception as e:
        logger.error(f"Binary extraction failed: {str(e)}")
    
    # If all methods fail
    logger.error("All extraction methods failed")
    return {
        'success': False,
        'text': '',
        'text_length': 0,
        'pages': 0,
        'metadata': {},
        'method': 'None',
        'error': 'All extraction methods failed'
    }


def clean_extracted_text(text):
    """
    Clean and normalize extracted text, especially for German documents
    """
    import re
    
    if not text:
        return text
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Fix common PDF extraction issues
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between camelCase
    
    # Clean up PDF artifacts
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)  # Remove control characters
    
    # Handle German umlauts and special characters that might be encoded incorrectly
    replacements = {
        'Ã¤': 'ä', 'Ã¶': 'ö', 'Ã¼': 'ü',
        'Ã„': 'Ä', 'Ã–': 'Ö', 'Ãœ': 'Ü',
        'ÃŸ': 'ß', 'â‚¬': '€'
    }
    
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    return text.strip()


def extract_text_from_binary(pdf_bytes):
    """
    Extract text from PDF using binary analysis as fallback
    """
    import re
    
    try:
        # Try UTF-8 decoding first
        try:
            text_content = pdf_bytes.decode('utf-8', errors='ignore')
        except:
            # Fallback to latin-1
            text_content = pdf_bytes.decode('latin-1', errors='ignore')
        
        # Extract text using regex patterns
        text_patterns = [
            r'\((.*?)\)',  # Text in parentheses
            r'<(.*?)>',    # Text in angle brackets
            r'/Title\s*\((.*?)\)',  # Title field
            r'/Subject\s*\((.*?)\)',  # Subject field
            r'BT\s+(.*?)\s+ET',  # Text between BT and ET markers
            r'Tj\s*\[(.*?)\]',  # Text arrays
            r'Tf\s+(.*?)\s+Tj',  # Text with font info
        ]
        
        extracted_parts = []
        
        for pattern in text_patterns:
            matches = re.findall(pattern, text_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if isinstance(match, str) and len(match.strip()) > 2:
                    # Clean the match
                    clean_match = re.sub(r'[^\w\s\-.,;:!?äöüÄÖÜß€]', ' ', match)
                    clean_match = re.sub(r'\s+', ' ', clean_match).strip()
                    if len(clean_match) > 3:
                        extracted_parts.append(clean_match)
        
        # Combine and deduplicate
        if extracted_parts:
            combined_text = ' '.join(extracted_parts)
            # Remove duplicates while preserving order
            words = combined_text.split()
            seen = set()
            unique_words = []
            for word in words:
                if word.lower() not in seen:
                    seen.add(word.lower())
                    unique_words.append(word)
            
            result = ' '.join(unique_words)
            return clean_extracted_text(result)
        
        return ""
        
    except Exception as e:
        logger.error(f"Binary extraction error: {e}")
        return ""

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'service': 'PDF Extraction Service',
        'version': '1.0.0',
        'python_version': os.sys.version,
        'libraries': {
            'PyPDF2': PyPDF2.__version__,
            'Flask': '2.3.3'
        }
    })

@app.route('/extract', methods=['POST'])
def extract_pdf():
    """
    Extract text from uploaded PDF file
    
    Accepts:
    - Multipart form data with 'file' field
    - JSON with base64 encoded PDF data
    
    Returns:
    - JSON with extraction results
    """
    try:
        pdf_bytes = None
        filename = 'unknown.pdf'
        
        # Handle multipart form data
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                raise BadRequest('No file selected')
            
            filename = file.filename
            pdf_bytes = file.read()
            logger.info(f"Received file upload: {filename} ({len(pdf_bytes)} bytes)")
        
        # Handle JSON with base64 data
        elif request.is_json:
            data = request.get_json()
            if 'data' not in data:
                raise BadRequest('Missing base64 data field')
            
            try:
                pdf_bytes = base64.b64decode(data['data'])
                filename = data.get('filename', 'unknown.pdf')
                logger.info(f"Received base64 data: {filename} ({len(pdf_bytes)} bytes)")
            except Exception as e:
                raise BadRequest(f'Invalid base64 data: {str(e)}')
        
        else:
            raise BadRequest('No PDF data provided. Send either multipart form data with "file" field or JSON with base64 "data" field')
        
        # Validate PDF bytes
        if not pdf_bytes or len(pdf_bytes) < 100:
            raise BadRequest('Invalid or empty PDF data')
        
        # Check if it's actually a PDF
        if not pdf_bytes.startswith(b'%PDF'):
            raise BadRequest('File is not a valid PDF')
        
        # Extract text
        result = extract_pdf_text(pdf_bytes)
        
        # Add filename to result
        result['filename'] = filename
        
        logger.info(f"Extraction completed: {result['success']}, {result['text_length']} characters")
        
        return jsonify(result)
        
    except BadRequest as e:
        logger.error(f"Bad request: {str(e)}")
        return jsonify({
            'success': False,
            'text': '',
            'text_length': 0,
            'pages': 0,
            'metadata': {},
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