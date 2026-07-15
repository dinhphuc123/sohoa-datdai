# core/file_handler.py
"""Handle PDF and image files for land documents."""
import os
import tempfile
from typing import Optional


def get_pdf_page_count(pdf_path: str) -> int:
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count


def render_pdf_page(pdf_path: str, page_index: int, dpi: int = 200) -> str:
    """Render PDF page to a temporary PNG file. Returns path to PNG."""
    import fitz
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    doc.close()

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    pix.save(tmp.name)
    return tmp.name


def get_image_info(image_path: str) -> dict:
    """Return basic image info dict."""
    from PIL import Image
    with Image.open(image_path) as img:
        return {"width": img.width, "height": img.height, "mode": img.mode, "format": img.format}


def crop_image_region(image_path: str, x1: float, y1: float, x2: float, y2: float,
                      normalized: bool = True, output_path: Optional[str] = None) -> str:
    """
    Crop a region from an image.
    If normalized=True, coords are 0.0-1.0 fraction of image size.
    Returns path to cropped image.
    """
    from PIL import Image
    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    if normalized:
        px1, py1 = int(x1 * w), int(y1 * h)
        px2, py2 = int(x2 * w), int(y2 * h)
    else:
        px1, py1, px2, py2 = int(x1), int(y1), int(x2), int(y2)

    cropped = img.crop((px1, py1, px2, py2))
    if not output_path:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        output_path = tmp.name
    cropped.save(output_path)
    return output_path


def is_supported_image(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}


def is_pdf(path: str) -> bool:
    return os.path.splitext(path)[1].lower() == ".pdf"
