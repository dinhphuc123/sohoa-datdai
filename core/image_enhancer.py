# core/image_enhancer.py
"""
Image pre-processing & enhancement for old/faded land documents.
Supports: Auto-contrast, grayscale, thresholding/binarization, rotation.
"""
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import os
import tempfile


def enhance_land_document(
    image_path: str,
    contrast: float = 1.2,
    brightness: float = 1.0,
    sharpness: float = 1.3,
    auto_level: bool = False,
    denoise: bool = False,
    rotation_angle: int = 0
) -> str:
    """
    Enhances image quality before passing to OCR for improved accuracy
    on yellowed, faded, or rotated scanned land titles.
    """
    try:
        img = Image.open(image_path).convert("RGB")

        # Rotate if requested
        if rotation_angle != 0:
            img = img.rotate(-rotation_angle, expand=True)

        # Auto-levels / Autocontrast
        if auto_level:
            img = ImageOps.autocontrast(img, cutoff=1)

        # Contrast adjustment
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)

        # Brightness adjustment
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)

        # Sharpness adjustment
        if sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(sharpness)

        # Subtle Denoising for scanned noise
        if denoise:
            img = img.filter(ImageFilter.SMOOTH_MORE)

        # Save to temp file
        ext = os.path.splitext(image_path)[1] or ".png"
        fd, temp_path = tempfile.mkstemp(prefix="enhanced_land_", suffix=ext)
        os.close(fd)
        img.save(temp_path, quality=95)
        return temp_path
    except Exception:
        return image_path
