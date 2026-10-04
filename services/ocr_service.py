import sys, os
from PIL import Image, ImageOps, ImageFilter
import pytesseract

def clean_ocr_text(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines()]
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                cleaned_lines.append("")
                prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False
    return "\n".join(cleaned_lines).strip()

def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    try:
        # Convert to grayscale
        gray = img.convert('L')
        # Autocontrast to make text pop
        contrasted = ImageOps.autocontrast(gray)
        return contrasted
    except Exception:
        return img

def ocr_image(image_source) -> str:
    """Extract text from an image file path or PIL Image object using Tesseract OCR."""
    try:
        if isinstance(image_source, str):
            if not os.path.isfile(image_source):
                return ""
            img = Image.open(image_source)
        elif isinstance(image_source, Image.Image):
            img = image_source
        else:
            return ""

        processed_img = preprocess_image_for_ocr(img)
        raw_text = pytesseract.image_to_string(processed_img, lang='eng')
        return clean_ocr_text(raw_text)
    except Exception as e:
        print(f"[OCR Service] Error during image OCR: {e}")
        return ""

def ocr_pdf_pages(pdf_path: str, max_pages: int = 15) -> str:
    """Rasterize PDF pages and run OCR on scanned/image-based PDF documents."""
    if not os.path.isfile(pdf_path):
        return ""

    extracted_pages = []
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_path)
        total_pages = min(len(pdf), max_pages)

        for i in range(total_pages):
            try:
                page = pdf.get_page(i)
                pil_image = page.render(scale=2.0).to_pil()
                text = ocr_image(pil_image)
                if text:
                    extracted_pages.append(f"--- [Page {i + 1}] ---\n{text}")
            except Exception as pe:
                print(f"[OCR Service] Failed page {i + 1}: {pe}")
                continue

        pdf.close()
    except Exception as e:
        print(f"[OCR Service] pypdfium2 OCR failed, trying pdf2image: {e}")
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, first_page=1, last_page=max_pages)
            for idx, img in enumerate(images):
                text = ocr_image(img)
                if text:
                    extracted_pages.append(f"--- [Page {idx + 1}] ---\n{text}")
        except Exception as e2:
            print(f"[OCR Service] Both PDF rasterizers failed: {e2}")

    return "\n\n".join(extracted_pages).strip()
