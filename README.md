# PDF2Q - Document Extraction Microservice

A comprehensive microservice for reliable document text extraction supporting PDF, text files, and OCR for images. Designed for deployment on Render.com with multiple fallback extraction methods.

## Features

- 🔍 **Multi-Format Document Extraction** - Supports PDF, text files, and images
- 📄 **Multiple PDF Extraction Methods** - PyPDF2, pdfplumber, and pdfminer fallbacks
- 🖼️ **OCR Support** - Tesseract OCR for image-based documents with German language support
- 🌐 **REST API** - Simple HTTP endpoints for document processing
- 📄 **Multiple Input Formats** - Supports file uploads and base64 encoded data
- 🚀 **Production Ready** - Optimized for deployment on Render.com
- 🔧 **German Tax Documents** - Optimized for German financial documents
- 📊 **Metadata Extraction** - Extracts document metadata and processing information
- 🛡️ **Robust Error Handling** - Graceful fallbacks when extraction methods fail

## API Endpoints

### Health Check
```
GET /
```
Returns service status and version information.

### Extract Document Text
```
POST /extract
```

**Supported File Types:**
- PDF documents (`.pdf`)
- Text files (`.txt`, `.md`, etc.)
- Image files (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`) with OCR

**Input Options:**

1. **Multipart Form Data:**
```bash
# PDF file
curl -X POST -F "file=@document.pdf" https://your-service.onrender.com/extract

# Text file
curl -X POST -F "file=@document.txt" https://your-service.onrender.com/extract

# Image file (OCR)
curl -X POST -F "file=@scanned_document.png" https://your-service.onrender.com/extract
```

2. **JSON with Base64:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"data":"base64_encoded_file_data","filename":"document.pdf","mime_type":"application/pdf"}' \
  https://your-service.onrender.com/extract
```

**Response:**
```json
{
  "success": true,
  "text": "Extracted text content...",
  "text_length": 1234,
  "pages": 3,
  "filename": "document.pdf",
  "mime_type": "application/pdf",
  "method": "PyPDF2",
  "metadata": {
    "title": "Document Title",
    "author": "Author Name",
    "creation_date": "2024-01-01"
  },
  "error": null
}
```

**Extraction Methods:**
- **PDF Files**: PyPDF2 → pdfplumber → pdfminer (fallback chain)
- **Text Files**: Direct UTF-8/Latin-1/CP1252 decoding
- **Image Files**: Tesseract OCR with German + English language support

### Test Endpoint
```
GET /test
```
Returns a test response to verify service functionality.

## Deployment on Render

1. **Connect Repository** - Link this GitHub repository to Render
2. **Service Type** - Choose "Web Service"
3. **Build Command** - `pip install -r requirements.txt`
4. **Start Command** - `gunicorn --bind 0.0.0.0:$PORT app:app`
5. **Environment** - Python 3.11

### Environment Variables
- `FLASK_ENV=production`
- `PYTHONUNBUFFERED=1`

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py

# Test the service
curl http://localhost:5000/
```

## Integration with Main Application

Update your main application to use this enhanced service:

```javascript
const DOCUMENT_SERVICE_URL = 'https://your-pdf2q-service.onrender.com';

async function extractDocumentText(buffer, filename, mimeType) {
  const formData = new FormData();
  formData.append('file', new Blob([buffer], { type: mimeType }), filename);
  
  const response = await fetch(`${DOCUMENT_SERVICE_URL}/extract`, {
    method: 'POST',
    body: formData
  });
  
  const result = await response.json();
  
  if (result.success) {
    console.log(`Extracted ${result.text_length} characters using ${result.method}`);
    return result.text;
  } else {
    console.error(`Extraction failed: ${result.error}`);
    throw new Error(result.error);
  }
}

// Usage examples:
// await extractDocumentText(pdfBuffer, 'document.pdf', 'application/pdf');
// await extractDocumentText(txtBuffer, 'document.txt', 'text/plain');
// await extractDocumentText(imgBuffer, 'scan.png', 'image/png');
```

## Architecture Benefits

- ✅ **Separation of Concerns** - PDF processing isolated from main application
- ✅ **Scalability** - Independent scaling of PDF processing workload
- ✅ **Reliability** - Dedicated Python environment for PDF libraries
- ✅ **Maintainability** - Focused codebase for PDF extraction logic
- ✅ **Performance** - Optimized for PDF processing tasks

## German Tax Document Support

This service is optimized for German tax documents including:
- Lohnsteuerbescheinigung
- Spendenquittungen
- Steuerliche Belege
- Rechnungen und Quittungen

## License

MIT License - See LICENSE file for details.