# core/land_parser.py
"""
Land data parser: normalize and validate OCR output for Vietnamese land documents.
"""
import re
from typing import Optional


def normalize_date(s: str) -> str:
    """Try to normalize date string to dd/mm/yyyy."""
    if not s:
        return ""
    s = s.strip()
    # Already correct format
    if re.match(r"\d{2}/\d{2}/\d{4}", s):
        return s
    # dd-mm-yyyy
    m = re.match(r"(\d{1,2})[.\-](\d{1,2})[.\-](\d{4})", s)
    if m:
        return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"
    # "ngày dd tháng mm năm yyyy"
    m = re.search(r"ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", s, re.IGNORECASE)
    if m:
        return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"
    return s


def normalize_area(s: str) -> str:
    """Extract numeric area value, remove units."""
    if not s:
        return ""
    # Remove units like m2, ha, etc.
    cleaned = re.sub(r"(m²|m2|ha|hecta|hectare|dm2)", "", s, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", ".").strip()
    # Keep only digits and dot
    m = re.search(r"[\d.]+", cleaned)
    return m.group(0) if m else s


def normalize_price(s: str) -> str:
    """Normalize price: remove currency units, keep number."""
    if not s:
        return ""
    cleaned = re.sub(r"(đồng|vnd|vnđ|nghìn|triệu|tỷ)", "", s, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", "").replace(".", "").strip()
    m = re.search(r"\d+", cleaned)
    return m.group(0) if m else s


def parse_gcn(raw: dict) -> dict:
    """Clean and validate a GCN OCR result dict."""
    out = dict(raw)
    out["ngay_cap"] = normalize_date(out.get("ngay_cap", ""))
    out["dien_tich"] = normalize_area(out.get("dien_tich", ""))
    # Normalize chu_so_huu list
    owners = out.get("chu_so_huu", [])
    if isinstance(owners, list):
        out["chu_so_huu"] = owners
    elif isinstance(owners, str):
        out["chu_so_huu"] = [{"ho_ten": owners}]
    return out


def parse_hop_dong(raw: dict) -> dict:
    """Clean and validate a Hop Dong OCR result dict."""
    out = dict(raw)
    out["ngay_ky"] = normalize_date(out.get("ngay_ky", ""))
    out["ngay_cong_chung"] = normalize_date(out.get("ngay_cong_chung", ""))
    out["gia_chuyen_nhuong"] = normalize_price(out.get("gia_chuyen_nhuong", ""))
    dat = out.get("thong_tin_thua_dat", {})
    if isinstance(dat, dict):
        dat["dien_tich"] = normalize_area(dat.get("dien_tich", ""))
    return out


def parse_ocr_result(result: dict) -> dict:
    """Auto-detect doc type and parse accordingly."""
    if result.get("error"):
        return result
    doc_type = result.get("_doc_type", "generic")
    if doc_type == "gcn":
        return parse_gcn(result)
    elif doc_type == "hop_dong":
        return parse_hop_dong(result)
    return result


# -------------------------------------------------------------------
# Summary string builders (for table display)
# -------------------------------------------------------------------

def gcn_summary(data: dict) -> str:
    parts = []
    owner = data.get("chu_so_huu", [])
    if isinstance(owner, list) and owner:
        parts.append(owner[0].get("ho_ten", ""))
    elif isinstance(owner, str):
        parts.append(owner)
    if data.get("so_thua_dat"):
        parts.append(f"Thửa {data['so_thua_dat']}")
    if data.get("so_to_ban_do"):
        parts.append(f"Tờ {data['so_to_ban_do']}")
    if data.get("dien_tich"):
        parts.append(f"{data['dien_tich']} {data.get('dien_tich_don_vi','m²')}")
    return " | ".join(p for p in parts if p)


def hop_dong_summary(data: dict) -> str:
    parts = []
    ben_chuyen = data.get("ben_chuyen_nhuong", [])
    if ben_chuyen:
        parts.append(f"Bên chuyển: {ben_chuyen[0].get('ho_ten','')}")
    ben_nhan = data.get("ben_nhan_chuyen_nhuong", [])
    if ben_nhan:
        parts.append(f"Bên nhận: {ben_nhan[0].get('ho_ten','')}")
    if data.get("gia_chuyen_nhuong"):
        g = int(data["gia_chuyen_nhuong"]) if data["gia_chuyen_nhuong"].isdigit() else data["gia_chuyen_nhuong"]
        parts.append(f"Giá: {g:,} VNĐ" if isinstance(g, int) else f"Giá: {g} VNĐ")
    if data.get("ngay_ky"):
        parts.append(f"Ngày: {data['ngay_ky']}")
    return " | ".join(p for p in parts if p)
