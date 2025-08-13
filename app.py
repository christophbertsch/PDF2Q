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
    Extract text from PDF bytes using PyPDF2
    
    Args:
        pdf_bytes: PDF file as bytes
        
    Returns:
        dict: Extraction result with success status, text, and metadata
    """
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
            extracted_text += page_text + "\n"
        
        # Clean up the text
        extracted_text = extracted_text.strip()
        
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
        
        return {
            'success': True,
            'text': extracted_text,
            'text_length': len(extracted_text),
            'pages': num_pages,
            'metadata': metadata,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        return {
            'success': False,
            'text': '',
            'text_length': 0,
            'pages': 0,
            'metadata': {},
            'error': str(e)
        }

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