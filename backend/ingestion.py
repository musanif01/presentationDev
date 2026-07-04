import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import fitz
except ImportError:
    fitz = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


async def extract_text_from_pdf(file_bytes: bytes) -> str:
    if fitz is None:
        return "[PDF parsing unavailable - PyMuPDF not installed]"
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""


async def extract_text_from_image(file_bytes: bytes) -> str:
    if Image is None or pytesseract is None:
        return "[OCR unavailable - Pillow or pytesseract not installed]"
    try:
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""


async def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return await extract_text_from_pdf(file_bytes)
    elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"):
        return await extract_text_from_image(file_bytes)
    else:
        return ""
