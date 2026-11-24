import io
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF
from PIL import Image
from config import settings
from utils.logger import logger

try:
    import pytesseract
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False


def extract_text_from_file(file_path: Path) -> Dict[str, Any]:
    """Extract text from PDF (PyMuPDF + OCR fallback) or Image (Pillow + Tesseract OCR)."""
    ext = file_path.suffix.lower()
    extracted_text = ""
    method = "none"
    page_count = 1
    warnings: List[str] = []

    try:
        if ext == ".pdf":
            doc = fitz.open(str(file_path))
            page_count = len(doc)
            chunks = []
            for idx, page in enumerate(doc):
                page_text = page.get_text("text").strip()
                if page_text:
                    chunks.append(f"--- Page {idx + 1} ---\n{page_text}")
                elif TESSERACT_AVAILABLE:
                    # Fallback OCR for scanned PDF page
                    pix = page.get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_txt = pytesseract.image_to_string(img).strip()
                    if ocr_txt:
                        chunks.append(f"--- Page {idx + 1} (OCR) ---\n{ocr_txt}")
            doc.close()
            extracted_text = "\n".join(chunks).strip()
            method = "PyMuPDF" if extracted_text else "PyMuPDF (No embedded text)"
            if not extracted_text and not TESSERACT_AVAILABLE:
                warnings.append("PDF appears scanned and Tesseract OCR is not installed on host.")

        elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
            with Image.open(file_path) as img:
                width, height = img.size
                img_format = img.format
                if TESSERACT_AVAILABLE:
                    try:
                        extracted_text = pytesseract.image_to_string(img).strip()
                        method = f"Tesseract OCR ({width}x{height} {img_format})"
                    except Exception as ocr_err:
                        method = f"Pillow Metadata ({width}x{height} {img_format})"
                        warnings.append(f"OCR unavailable at runtime: {ocr_err}")
                else:
                    method = f"Pillow Metadata ({width}x{height} {img_format})"
                    warnings.append("Tesseract OCR binary not available; image metadata verified.")
    except Exception as exc:
        logger.error(f"Document extraction error for {file_path.name}: {exc}")
        warnings.append(f"Extraction error: {str(exc)}")

    return {
        "file_name": file_path.name,
        "extension": ext,
        "page_count": page_count,
        "extraction_method": method,
        "text": extracted_text,
        "warnings": warnings,
    }


def extract_claim_documents(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process all uploaded documents attached to a claim."""
    results = []
    combined_sections = []

    for doc in documents:
        rel = doc.get("relative_path", "")
        full_path = settings.upload_path / rel
        if not full_path.exists():
            results.append({
                "file_name": doc.get("original_name", rel),
                "extraction_method": "missing",
                "text": "",
                "warnings": ["Stored file not found on disk."],
            })
            continue

        info = extract_text_from_file(full_path)
        info["original_name"] = doc.get("original_name", full_path.name)
        info["doc_category"] = doc.get("doc_category", "supporting_document")
        results.append(info)

        header = f"=== DOCUMENT: {info['original_name']} ({info['doc_category']}) ==="
        body = info["text"] if info["text"] else "[No machine-readable text extracted]"
        combined_sections.append(f"{header}\n{body}")

    return {
        "documents": results,
        "combined_text": "\n\n".join(combined_sections),
        "total_files": len(results),
    }
