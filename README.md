# PDF2Q - PDF Extraction Microservice

A dedicated microservice for reliable PDF text extraction using PyPDF2, designed for deployment on Render.com.

## Features

- 🔍 **Reliable PDF Text Extraction** - Uses PyPDF2 for consistent text extraction
- 🌐 **REST API** - Simple HTTP endpoints for PDF processing
- 📄 **Multiple Input Formats** - Supports file uploads and base64 encoded data
- 🚀 **Production Ready** - Optimized for deployment on Render.com
- 🔧 **German Tax Documents** - Optimized for German financial documents
- 📊 **Metadata Extraction** - Extracts PDF metadata and document information

## API Endpoints

### Health Check
```
GET /
```
Returns service status and version information.

### Extract PDF Text
```
POST /extract
```

**Input Options:**

1. **Multipart Form Data:**
```bash
curl -X POST -F "file=@document.pdf" https://your-service.onrender.com/extract
```

2. **JSON with Base64:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"data":"base64_encoded_pdf_data","filename":"document.pdf"}' \
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
  "metadata": {
    "title": "Document Title",
    "author": "Author Name",
    "creation_date": "2024-01-01"
  },
  "error": null
}
```

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

Update your main application to use this service:

```javascript
const PDF_SERVICE_URL = 'https://your-pdf2q-service.onrender.com';

async function extractPDFText(buffer, filename) {
  const formData = new FormData();
  formData.append('file', new Blob([buffer]), filename);
  
  const response = await fetch(`${PDF_SERVICE_URL}/extract`, {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}
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