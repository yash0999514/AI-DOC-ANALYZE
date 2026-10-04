# AI DOC – Intelligent Document Analysis & AI Assistant

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.2%2B-lightgrey)
![Gemini AI](https://img.shields.io/badge/Gemini_AI-Integrated-orange)
![License](https://img.shields.io/badge/License-MIT-green)

AI DOC is a robust, visually stunning web application built to ingest, extract, and deeply analyze documents using advanced AI (Google Gemini) and OCR technology. It seamlessly converts your static PDFs, Word documents, text files, and images into structured, interactive intelligence.

## ✨ Features

- **Multi-Format Support**: Upload `.pdf`, `.docx`, `.txt`, `.png`, and `.jpg` files.
- **Smart Data Extraction**: Built-in support for native PDF text extraction, DOCX parsing, and Tesseract OCR for scanned documents and images.
- **AI-Powered Analysis**: Leverages Google Gemini AI to automatically generate:
  - Executive Summaries & Document Classification
  - Key Points & Action Items
  - Obligations, Risks, & Warnings
  - Important Dates & Involved Entities
  - Glossary of Key Terms
- **Interactive Document Chat**: Ask context-aware questions directly against your document's text.
- **Heuristic Fallback**: A built-in local fallback engine ensures document parsing and intelligence extraction even if the API key isn't configured.
- **Premium User Interface**: Dark/Light mode, sleek glassmorphism elements, drag-and-drop uploads, and dynamic micro-animations.
- **User Authentication**: Secure individual workspaces and file privacy.

## 🚀 Quick Setup

### 1. Clone the repository
```bash
git clone https://github.com/yash0999514/AI-DOC-ANALYZE.git
cd AI-DOC-ANALYZE
```

### 2. Create a Virtual Environment (Recommended)
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
Ensure you have [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed on your system if you plan to scan image-based PDFs or images.
```bash
pip install -r requirements.txt
```

### 4. Configuration
Create a `.env` file in the root directory (you can use `.env.example` as a template):
```env
# Flask Settings
FLASK_ENV=development
SECRET_KEY=your_secure_secret_key_here
PORT=5000

# Google Gemini API Key (Required for AI features, otherwise falls back to local heuristics)
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

## 🛠️ Technology Stack

- **Backend**: Python, Flask, SQLAlchemy (SQLite by default)
- **Document Processing**: PyMuPDF (`pypdfium2`), `python-docx`, `pytesseract`, `pdf2image`, `Pillow`
- **AI Integration**: Google Generative AI SDK (`google-generativeai`)
- **Frontend**: HTML5, Vanilla CSS3 (Custom Design System), JavaScript (ES6)

## 📝 License
This project is open-source and available under the [MIT License](LICENSE).
