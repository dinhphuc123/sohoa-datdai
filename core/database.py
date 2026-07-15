# core/database.py
"""
SQLite database for Vietnamese land document management.
Tables: land_records, documents, owners
"""
import sqlite3
import json
import datetime
import os

from core import config_manager as cfg


def _get_conn() -> sqlite3.Connection:
    db_path = cfg.get("db_path")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if not exist."""
    conn = _get_conn()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS land_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type    TEXT NOT NULL,          -- 'gcn' | 'hop_dong' | 'generic'
            status      TEXT DEFAULT 'draft',   -- 'draft' | 'verified' | 'archived'
            source_file TEXT,
            page_index  INTEGER DEFAULT 0,
            image_path  TEXT,
            raw_ocr     TEXT,                   -- JSON string from OCR
            created_at  TEXT,
            updated_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS gcn_records (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id       INTEGER UNIQUE,
            so_gcn          TEXT,
            ngay_cap        TEXT,
            co_quan_cap     TEXT,
            so_to_ban_do    TEXT,
            so_thua_dat     TEXT,
            dia_chi_thua_dat TEXT,
            dien_tich       REAL,
            dien_tich_don_vi TEXT DEFAULT 'm2',
            muc_dich_su_dung TEXT,
            thoi_han_su_dung TEXT,
            nguon_goc_su_dung TEXT,
            so_nha          TEXT,
            duong_pho       TEXT,
            phuong_xa       TEXT,
            quan_huyen      TEXT,
            tinh_thanh      TEXT,
            ghi_chu         TEXT,
            FOREIGN KEY(record_id) REFERENCES land_records(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS hop_dong_records (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id       INTEGER UNIQUE,
            so_hop_dong     TEXT,
            ngay_ky         TEXT,
            noi_ky          TEXT,
            gia_chuyen_nhuong REAL,
            don_vi_tien     TEXT DEFAULT 'VND',
            phuong_thuc_thanh_toan TEXT,
            thoi_gian_ban_giao TEXT,
            cong_chung_vien TEXT,
            van_phong_cong_chung TEXT,
            so_cong_chung   TEXT,
            ngay_cong_chung TEXT,
            so_to_ban_do    TEXT,
            so_thua_dat     TEXT,
            dien_tich       REAL,
            dia_chi_thua_dat TEXT,
            so_gcn_lien_quan TEXT,
            ghi_chu         TEXT,
            FOREIGN KEY(record_id) REFERENCES land_records(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS owners (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id   INTEGER,
            role        TEXT,   -- 'chu_so_huu' | 'ben_chuyen' | 'ben_nhan'
            ho_ten      TEXT,
            ngay_sinh   TEXT,
            cmnd_cccd   TEXT,
            dia_chi     TEXT,
            FOREIGN KEY(record_id) REFERENCES land_records(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS attachments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id   INTEGER,
            file_path   TEXT,
            file_name   TEXT,
            file_type   TEXT,
            created_at  TEXT,
            FOREIGN KEY(record_id) REFERENCES land_records(id) ON DELETE CASCADE
        );
    """)

    # FTS5 for full-text search
    try:
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS land_fts USING fts5(
                record_id UNINDEXED,
                content,
                tokenize='unicode61'
            )
        """)
    except sqlite3.OperationalError:
        pass  # FTS5 not available

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def save_gcn_record(parsed: dict, source_file: str = "", page_index: int = 0, image_path: str = "") -> int:
    """Save a GCN/Sổ đỏ record. Returns record id."""
    conn = _get_conn()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO land_records (doc_type, source_file, page_index, image_path, raw_ocr, created_at, updated_at)
        VALUES ('gcn', ?, ?, ?, ?, ?, ?)
    """, (source_file, page_index, image_path, json.dumps(parsed, ensure_ascii=False), now, now))
    record_id = cur.lastrowid

    def _to_float(s):
        try:
            return float(str(s).replace(",", "."))
        except Exception:
            return None

    cur.execute("""
        INSERT INTO gcn_records (
            record_id, so_gcn, ngay_cap, co_quan_cap,
            so_to_ban_do, so_thua_dat, dia_chi_thua_dat,
            dien_tich, dien_tich_don_vi, muc_dich_su_dung,
            thoi_han_su_dung, nguon_goc_su_dung,
            so_nha, duong_pho, phuong_xa, quan_huyen, tinh_thanh, ghi_chu
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        record_id,
        parsed.get("so_gcn", ""),
        parsed.get("ngay_cap", ""),
        parsed.get("co_quan_cap", ""),
        parsed.get("so_to_ban_do", ""),
        parsed.get("so_thua_dat", ""),
        parsed.get("dia_chi_thua_dat", ""),
        _to_float(parsed.get("dien_tich", "")),
        parsed.get("dien_tich_don_vi", "m2"),
        parsed.get("muc_dich_su_dung", ""),
        parsed.get("thoi_han_su_dung", ""),
        parsed.get("nguon_goc_su_dung", ""),
        parsed.get("so_nha", ""),
        parsed.get("duong_pho", ""),
        parsed.get("phuong_xa", ""),
        parsed.get("quan_huyen", ""),
        parsed.get("tinh_thanh", ""),
        parsed.get("ghi_chu", ""),
    ))

    # Save owners
    for owner in parsed.get("chu_so_huu", []):
        if isinstance(owner, dict):
            cur.execute("""
                INSERT INTO owners (record_id, role, ho_ten, ngay_sinh, cmnd_cccd, dia_chi)
                VALUES (?, 'chu_so_huu', ?, ?, ?, ?)
            """, (record_id, owner.get("ho_ten", ""), owner.get("ngay_sinh", ""),
                  owner.get("cmnd_cccd", ""), owner.get("dia_chi", "")))

    # FTS index
    fts_text = " ".join(filter(None, [
        parsed.get("so_gcn", ""), parsed.get("so_thua_dat", ""),
        parsed.get("so_to_ban_do", ""), parsed.get("dia_chi_thua_dat", ""),
        parsed.get("tinh_thanh", ""), parsed.get("quan_huyen", ""),
        " ".join(o.get("ho_ten", "") for o in parsed.get("chu_so_huu", []) if isinstance(o, dict))
    ]))
    try:
        cur.execute("INSERT INTO land_fts (record_id, content) VALUES (?, ?)", (record_id, fts_text))
    except Exception:
        pass

    conn.commit()
    conn.close()
    return record_id


def save_hop_dong_record(parsed: dict, source_file: str = "", page_index: int = 0, image_path: str = "") -> int:
    """Save a Hợp đồng chuyển nhượng record. Returns record id."""
    conn = _get_conn()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO land_records (doc_type, source_file, page_index, image_path, raw_ocr, created_at, updated_at)
        VALUES ('hop_dong', ?, ?, ?, ?, ?, ?)
    """, (source_file, page_index, image_path, json.dumps(parsed, ensure_ascii=False), now, now))
    record_id = cur.lastrowid

    def _to_float(s):
        try:
            return float(str(s).replace(",", ""))
        except Exception:
            return None

    thua = parsed.get("thong_tin_thua_dat", {}) or {}
    cur.execute("""
        INSERT INTO hop_dong_records (
            record_id, so_hop_dong, ngay_ky, noi_ky,
            gia_chuyen_nhuong, don_vi_tien, phuong_thuc_thanh_toan,
            thoi_gian_ban_giao, cong_chung_vien, van_phong_cong_chung,
            so_cong_chung, ngay_cong_chung,
            so_to_ban_do, so_thua_dat, dien_tich, dia_chi_thua_dat,
            so_gcn_lien_quan, ghi_chu
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        record_id,
        parsed.get("so_hop_dong", ""),
        parsed.get("ngay_ky", ""),
        parsed.get("noi_ky", ""),
        _to_float(parsed.get("gia_chuyen_nhuong", "")),
        parsed.get("don_vi_tien", "VND"),
        parsed.get("phuong_thuc_thanh_toan", ""),
        parsed.get("thoi_gian_ban_giao", ""),
        parsed.get("cong_chung_vien", ""),
        parsed.get("van_phong_cong_chung", ""),
        parsed.get("so_cong_chung", ""),
        parsed.get("ngay_cong_chung", ""),
        thua.get("so_to_ban_do", ""),
        thua.get("so_thua_dat", ""),
        _to_float(thua.get("dien_tich", "")),
        thua.get("dia_chi", ""),
        thua.get("so_gcn", ""),
        parsed.get("ghi_chu", ""),
    ))

    # Save parties
    for owner in parsed.get("ben_chuyen_nhuong", []):
        if isinstance(owner, dict):
            cur.execute("""
                INSERT INTO owners (record_id, role, ho_ten, ngay_sinh, cmnd_cccd, dia_chi)
                VALUES (?, 'ben_chuyen', ?, ?, ?, ?)
            """, (record_id, owner.get("ho_ten", ""), owner.get("ngay_sinh", ""),
                  owner.get("cmnd_cccd", ""), owner.get("dia_chi", "")))
    for owner in parsed.get("ben_nhan_chuyen_nhuong", []):
        if isinstance(owner, dict):
            cur.execute("""
                INSERT INTO owners (record_id, role, ho_ten, ngay_sinh, cmnd_cccd, dia_chi)
                VALUES (?, 'ben_nhan', ?, ?, ?, ?)
            """, (record_id, owner.get("ho_ten", ""), owner.get("ngay_sinh", ""),
                  owner.get("cmnd_cccd", ""), owner.get("dia_chi", "")))

    # FTS index
    fts_text = " ".join(filter(None, [
        parsed.get("so_hop_dong", ""), thua.get("so_thua_dat", ""),
        " ".join(o.get("ho_ten", "") for o in parsed.get("ben_chuyen_nhuong", []) if isinstance(o, dict)),
        " ".join(o.get("ho_ten", "") for o in parsed.get("ben_nhan_chuyen_nhuong", []) if isinstance(o, dict))
    ]))
    try:
        cur.execute("INSERT INTO land_fts (record_id, content) VALUES (?, ?)", (record_id, fts_text))
    except Exception:
        pass

    conn.commit()
    conn.close()
    return record_id


def update_record_status(record_id: int, status: str):
    conn = _get_conn()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE land_records SET status=?, updated_at=? WHERE id=?", (status, now, record_id))
    conn.commit()
    conn.close()


def delete_record(record_id: int):
    conn = _get_conn()
    conn.execute("DELETE FROM land_records WHERE id=?", (record_id,))
    try:
        conn.execute("DELETE FROM land_fts WHERE record_id=?", (record_id,))
    except Exception:
        pass
    conn.commit()
    conn.close()


def search_records(query: str = "", doc_type: str = "", status: str = "", limit: int = 200) -> list:
    """Full-text search across all land records."""
    conn = _get_conn()
    cur = conn.cursor()

    if query:
        try:
            sql = """
                SELECT lr.*, lf.content
                FROM land_fts lf
                JOIN land_records lr ON lr.id = lf.record_id
                WHERE lf.land_fts MATCH ?
            """
            params = [query + "*"]
            if doc_type:
                sql += " AND lr.doc_type = ?"
                params.append(doc_type)
            if status:
                sql += " AND lr.status = ?"
                params.append(status)
            sql += " ORDER BY lr.id DESC LIMIT ?"
            params.append(limit)
            cur.execute(sql, params)
        except Exception:
            # Fallback LIKE
            sql = "SELECT * FROM land_records WHERE 1=1"
            params = []
            if doc_type:
                sql += " AND doc_type=?"
                params.append(doc_type)
            if status:
                sql += " AND status=?"
                params.append(status)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            cur.execute(sql, params)
    else:
        sql = "SELECT * FROM land_records WHERE 1=1"
        params = []
        if doc_type:
            sql += " AND doc_type=?"
            params.append(doc_type)
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        cur.execute(sql, params)

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_record_detail(record_id: int) -> dict:
    """Get full record with GCN or hop_dong details and owners."""
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM land_records WHERE id=?", (record_id,))
    base = cur.fetchone()
    if not base:
        conn.close()
        return {}
    result = dict(base)

    if result["doc_type"] == "gcn":
        cur.execute("SELECT * FROM gcn_records WHERE record_id=?", (record_id,))
        gcn = cur.fetchone()
        if gcn:
            result["detail"] = dict(gcn)
    elif result["doc_type"] == "hop_dong":
        cur.execute("SELECT * FROM hop_dong_records WHERE record_id=?", (record_id,))
        hd = cur.fetchone()
        if hd:
            result["detail"] = dict(hd)

    cur.execute("SELECT * FROM owners WHERE record_id=?", (record_id,))
    result["owners"] = [dict(r) for r in cur.fetchall()]

    conn.close()
    return result


def get_statistics() -> dict:
    """Return aggregate statistics for dashboard."""
    conn = _get_conn()
    cur = conn.cursor()
    stats = {}

    cur.execute("SELECT COUNT(*) FROM land_records")
    stats["total"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM land_records WHERE doc_type='gcn'")
    stats["gcn_count"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM land_records WHERE doc_type='hop_dong'")
    stats["hop_dong_count"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM land_records WHERE status='verified'")
    stats["verified"] = cur.fetchone()[0]

    cur.execute("SELECT SUM(dien_tich) FROM gcn_records")
    row = cur.fetchone()
    stats["total_area"] = round(row[0], 2) if row and row[0] else 0

    conn.close()
    return stats
