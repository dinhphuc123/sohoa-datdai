# core/ocr_service.py
"""
OCR Service — hỗ trợ 3 backend:
  • Gemini API  (cloud, Google)
  • Mistral API (cloud, Mistral AI — pixtral-12b-2409)
  • LM Studio   (local, OpenAI-compatible API)
"""
import base64
import json
import os
import re
import requests
from typing import Optional, Callable

from core import config_manager as cfg

# ---------------------------------------------------------------------------
# Prompts đặc thù đất đai Việt Nam
# ---------------------------------------------------------------------------

GCN_OCR_PROMPT = """Bạn là chuyên gia địa chính Việt Nam, chuyên đọc và số hóa Giấy chứng nhận quyền sử dụng đất (GCN/Sổ đỏ/Sổ hồng).

Nhiệm vụ: Đọc toàn bộ nội dung trong ảnh này và trích xuất thông tin theo định dạng JSON sau:

```json
{
  "so_gcn": "",
  "ngay_cap": "",
  "co_quan_cap": "",
  "chu_so_huu": [{"ho_ten": "", "ngay_sinh": "", "cmnd_cccd": "", "dia_chi": ""}],
  "so_to_ban_do": "",
  "so_thua_dat": "",
  "dia_chi_thua_dat": "",
  "dien_tich": "",
  "dien_tich_don_vi": "m2",
  "muc_dich_su_dung": "",
  "thoi_han_su_dung": "",
  "nguon_goc_su_dung": "",
  "so_nha": "",
  "duong_pho": "",
  "phuong_xa": "",
  "quan_huyen": "",
  "tinh_thanh": "",
  "ghi_chu": "",
  "raw_text": ""
}
```

Quy tắc:
- Trích xuất CHÍNH XÁC từng trường, không suy đoán
- "raw_text" chứa toàn bộ văn bản đọc được
- Nếu không tìm thấy trường nào, để chuỗi rỗng ""
- Số tờ bản đồ, số thửa: lấy chính xác con số
- Diện tích: chỉ lấy số (ví dụ: "125.5")
- Ngày tháng: định dạng dd/mm/yyyy
"""

HOP_DONG_OCR_PROMPT = """Bạn là chuyên gia pháp lý bất động sản Việt Nam, chuyên đọc hợp đồng chuyển nhượng quyền sử dụng đất.

Nhiệm vụ: Đọc toàn bộ nội dung trong ảnh này và trích xuất thông tin theo định dạng JSON:

```json
{
  "so_hop_dong": "",
  "ngay_ky": "",
  "noi_ky": "",
  "ben_chuyen_nhuong": [{"ho_ten": "", "ngay_sinh": "", "cmnd_cccd": "", "dia_chi": ""}],
  "ben_nhan_chuyen_nhuong": [{"ho_ten": "", "ngay_sinh": "", "cmnd_cccd": "", "dia_chi": ""}],
  "thong_tin_thua_dat": {
    "so_to_ban_do": "",
    "so_thua_dat": "",
    "dien_tich": "",
    "dia_chi": "",
    "so_gcn": ""
  },
  "gia_chuyen_nhuong": "",
  "don_vi_tien": "VND",
  "phuong_thuc_thanh_toan": "",
  "thoi_gian_ban_giao": "",
  "cong_chung_vien": "",
  "van_phong_cong_chung": "",
  "so_cong_chung": "",
  "ngay_cong_chung": "",
  "ghi_chu": "",
  "raw_text": ""
}
```

Quy tắc:
- Trích xuất CHÍNH XÁC từng trường, không suy đoán
- "raw_text" chứa toàn bộ văn bản đọc được
- Nếu không tìm thấy, để chuỗi rỗng ""
- Giá chuyển nhượng: chỉ lấy số (ví dụ: "1500000000")
- Ngày tháng: định dạng dd/mm/yyyy
"""

GENERIC_LAND_PROMPT = """Bạn là chuyên gia địa chính Việt Nam. Hãy đọc nội dung tài liệu đất đai trong ảnh và trả về JSON với:
- "doc_type": loại tài liệu (gcn, hop_dong, ban_do, quyet_dinh, khac)
- "raw_text": toàn bộ văn bản đọc được
- "key_fields": dict các trường quan trọng tìm được
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _encode_image(image_path: str) -> tuple[str, str]:
    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "webp": "image/webp",
                "bmp": "image/bmp", "tiff": "image/tiff"}
    mime = mime_map.get(ext, "image/png")
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8"), mime


def _extract_json(text: str) -> dict:
    """Extract JSON object from LLM text response."""
    # Try ```json ... ``` block first
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Try first { ... } in text
    m2 = re.search(r"(\{.*\})", text, re.DOTALL)
    if m2:
        try:
            return json.loads(m2.group(1))
        except Exception:
            pass
    # Whole text as JSON
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    return {"raw_text": text, "parse_error": True}

# ---------------------------------------------------------------------------
# Backend 1: Gemini API
# ---------------------------------------------------------------------------

def run_gemini_ocr(image_path: str, prompt: str) -> dict:
    api_key = cfg.get("gemini_api_key", "").strip()
    if not api_key:
        return {"error": "⚠️ Chưa nhập Gemini API key.\nVào Cài đặt → Tab 'Gemini API' để nhập.", "raw_text": ""}

    b64, mime = _encode_image(image_path)
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-3.5-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": mime, "data": b64}}
        ]}],
        "generationConfig": {"temperature": 0.05, "maxOutputTokens": 4096}
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _extract_json(text)
    except requests.exceptions.Timeout:
        return {"error": "⌛ Timeout kết nối Gemini API (60s). Thử lại sau.", "raw_text": ""}
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "?"
        msg = e.response.json().get("error", {}).get("message", str(e)) if e.response else str(e)
        return {"error": f"❌ Gemini API lỗi {code}:\n{msg}", "raw_text": ""}
    except Exception as e:
        return {"error": f"❌ Lỗi Gemini: {e}", "raw_text": ""}

# ---------------------------------------------------------------------------
# Backend 2: Mistral API (pixtral — vision model)
# ---------------------------------------------------------------------------

def run_mistral_ocr(image_path: str, prompt: str) -> dict:
    api_key = cfg.get("mistral_api_key", "").strip()
    if not api_key:
        return {"error": "⚠️ Chưa nhập Mistral API key.\nVào Cài đặt → Tab 'Mistral API' để nhập.", "raw_text": ""}

    b64, mime = _encode_image(image_path)
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "pixtral-12b-2409",   # Mistral vision model
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.05,
        "max_tokens": 4096,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return _extract_json(text)
    except requests.exceptions.Timeout:
        return {"error": "⌛ Timeout kết nối Mistral API (90s). Thử lại sau.", "raw_text": ""}
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "?"
        try:
            msg = e.response.json().get("message", str(e))
        except Exception:
            msg = str(e)
        return {"error": f"❌ Mistral API lỗi {code}:\n{msg}", "raw_text": ""}
    except Exception as e:
        return {"error": f"❌ Lỗi Mistral: {e}", "raw_text": ""}

# ---------------------------------------------------------------------------
# Backend 3: LM Studio (OpenAI-compatible local API)
# ---------------------------------------------------------------------------

def run_lmstudio_ocr(image_path: str, prompt: str) -> dict:
    """
    LM Studio chạy server OpenAI-compatible tại localhost:1234.
    Hỗ trợ các vision model: LLaVA, Gemma, Qwen-VL, Phi-3-vision, v.v.
    """
    base_url = cfg.get("lmstudio_url", "http://localhost:1234").rstrip("/")
    model = cfg.get("lmstudio_model", "local-model")

    b64, mime = _encode_image(image_path)
    url = f"{base_url}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.05,
        "max_tokens": 4096,
        "stream": False,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=180)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return _extract_json(text)
    except requests.exceptions.ConnectionError:
        return {
            "error": (
                f"❌ Không kết nối được LM Studio tại {base_url}.\n\n"
                "Kiểm tra:\n"
                "• LM Studio đang mở?\n"
                "• Đã nhấn 'Start Server' trong LM Studio?\n"
                "• Server URL đúng trong Cài đặt?"
            ),
            "raw_text": ""
        }
    except requests.exceptions.Timeout:
        return {"error": "⌛ Timeout LM Studio (180s). Model đang load hoặc quá nặng.", "raw_text": ""}
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "?"
        try:
            msg = e.response.json().get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return {"error": f"❌ LM Studio lỗi {code}:\n{msg}", "raw_text": ""}
    except Exception as e:
        return {"error": f"❌ Lỗi LM Studio: {e}", "raw_text": ""}

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_PROMPT_MAP = {
    "gcn": GCN_OCR_PROMPT,
    "hop_dong": HOP_DONG_OCR_PROMPT,
    "generic": GENERIC_LAND_PROMPT,
}

_BACKEND_LABELS = {
    "gemini": "Gemini API (Google)",
    "mistral": "Mistral API (pixtral-12b)",
    "lmstudio": "LM Studio (Local)",
}

def run_ocr(image_path: str, doc_type: str = "gcn",
            progress_callback: Optional[Callable[[str], None]] = None) -> dict:
    """
    Run OCR on an image file.

    Args:
        image_path:  Path to image (PNG/JPG/PDF page)
        doc_type:    'gcn' | 'hop_dong' | 'generic'
        progress_callback: callable(str) for status messages

    Returns:
        dict with extracted fields + raw_text + _doc_type + _model_used
    """
    prompt = _PROMPT_MAP.get(doc_type, GENERIC_LAND_PROMPT)
    mode = cfg.get("ocr_mode", "gemini")
    label = _BACKEND_LABELS.get(mode, mode)

    if progress_callback:
        progress_callback(f"🔄 Đang gửi ảnh đến {label}...")

    if mode == "gemini":
        result = run_gemini_ocr(image_path, prompt)
    elif mode == "mistral":
        result = run_mistral_ocr(image_path, prompt)
    elif mode == "lmstudio":
        result = run_lmstudio_ocr(image_path, prompt)
    else:
        result = {"error": f"Chế độ OCR không hợp lệ: '{mode}'", "raw_text": ""}

    result["_doc_type"] = doc_type
    result["_model_used"] = f"{mode}" + (":gemini-3.5-flash" if mode == "gemini" else "")
    return result

# ---------------------------------------------------------------------------
# Connectivity checks
# ---------------------------------------------------------------------------

def check_gemini_connection() -> tuple[bool, str]:
    """Returns (ok, message)."""
    api_key = cfg.get("gemini_api_key", "").strip()
    if not api_key:
        return False, "Chưa nhập API key."
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return True, "Kết nối thành công!"
        msg = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
        return False, msg
    except requests.exceptions.Timeout:
        return False, "Timeout (10s) — kiểm tra internet."
    except Exception as e:
        return False, str(e)


def check_mistral_connection() -> tuple[bool, str]:
    """Returns (ok, message)."""
    api_key = cfg.get("mistral_api_key", "").strip()
    if not api_key:
        return False, "Chưa nhập Mistral API key."
    try:
        url = "https://api.mistral.ai/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            models = [m["id"] for m in resp.json().get("data", [])]
            vision = [m for m in models if "pixtral" in m.lower() or "vision" in m.lower()]
            note = f"\n✅ Vision models: {', '.join(vision[:3])}" if vision else ""
            return True, f"Kết nối thành công!{note}"
        msg = resp.json().get("message", f"HTTP {resp.status_code}")
        return False, msg
    except requests.exceptions.Timeout:
        return False, "Timeout (10s) — kiểm tra internet."
    except Exception as e:
        return False, str(e)


def check_lmstudio_connection() -> tuple[bool, str]:
    """Returns (ok, message)."""
    base_url = cfg.get("lmstudio_url", "http://localhost:1234").rstrip("/")
    try:
        resp = requests.get(f"{base_url}/v1/models", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("id", "") for m in data.get("data", [])]
            loaded = ", ".join(models[:3]) if models else "Chưa có model nào được load"
            return True, f"Kết nối OK!\nModel đang load: {loaded}"
        return False, f"HTTP {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return False, (
            f"Không kết nối được {base_url}\n"
            "LM Studio chưa chạy hoặc chưa bật Server."
        )
    except requests.exceptions.Timeout:
        return False, "Timeout (5s)"
    except Exception as e:
        return False, str(e)


def get_lmstudio_models() -> list[str]:
    """Fetch list of loaded models from LM Studio."""
    base_url = cfg.get("lmstudio_url", "http://localhost:1234").rstrip("/")
    try:
        resp = requests.get(f"{base_url}/v1/models", timeout=5)
        if resp.status_code == 200:
            return [m.get("id", "") for m in resp.json().get("data", [])]
    except Exception:
        pass
    return []
