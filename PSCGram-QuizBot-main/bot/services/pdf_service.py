from io import BytesIO
from pypdf import PdfReader


def extract_pdf_text(data, ocr=True):
    """Extract selectable text page-by-page, OCRing only pages with no text."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ValueError("The uploaded PDF is empty or invalid.")

    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ValueError("The PDF is password-protected.") from exc
        pages = list(reader.pages)
    except Exception as exc:
        raise ValueError(f"Could not read the PDF: {exc}") from exc

    extracted = []
    ocr_pages = []
    for number, page in enumerate(pages, start=1):
        try:
            page_text = (page.extract_text() or "").strip()
        except Exception:
            page_text = ""
        if page_text:
            extracted.append((number, page_text))
        elif ocr:
            ocr_pages.append(number)

    if ocr_pages:
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
            images = convert_from_bytes(bytes(data), dpi=200)
            for number in ocr_pages:
                if number <= len(images):
                    page_text = (pytesseract.image_to_string(images[number - 1]) or "").strip()
                    if page_text:
                        extracted.append((number, page_text))
        except Exception as exc:
            if not extracted:
                raise ValueError(
                    "No selectable text was found and OCR failed. Install Tesseract "
                    "and Poppler on the host. Details: " + str(exc)
                ) from exc

    extracted.sort(key=lambda item: item[0])
    result = "\n\n".join(f"[PDF page {number}]\n{text}" for number, text in extracted).strip()
    if not result:
        raise ValueError("No readable text was found in this PDF.")
    return result


def chunk_text(text, size=10000, overlap=500):
    """Split text into bounded chunks while retaining page markers."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if size <= 0:
        raise ValueError("size must be greater than zero")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be non-negative and smaller than size")
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks
