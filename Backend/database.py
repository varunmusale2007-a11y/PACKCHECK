import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compliance_checker.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            image_path TEXT NOT NULL,
            commodity_type TEXT,
            ocr_text TEXT,
            compliance_score REAL DEFAULT 0.0,
            compliance_status TEXT DEFAULT 'PENDING',
            rule_results TEXT,
            status TEXT DEFAULT 'UPLOADED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def insert_scan_record(filename: str, image_path: str, commodity_type: str = "Packaged Commodity") -> int:
    """Inserts a brand new scan record for an upload and returns its unique scan_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO scan_records (filename, image_path, commodity_type, status, created_at, updated_at)
        VALUES (?, ?, ?, 'UPLOADED', ?, ?)
        """,
        (filename, image_path, commodity_type, datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
    )
    scan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return scan_id

def update_ocr_text(scan_id: int, ocr_text: str) -> bool:
    """Updates OCR text strictly and ONLY for the record matching scan_records.id = scan_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE scan_records 
        SET ocr_text = ?, status = 'OCR_COMPLETED', updated_at = ?
        WHERE id = ?
        """,
        (ocr_text, datetime.utcnow().isoformat(), scan_id)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def update_compliance_result(scan_id: int, score: float, status: str, rule_results: dict) -> bool:
    """Updates compliance evaluation results strictly for scan_records.id = scan_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE scan_records 
        SET compliance_score = ?, compliance_status = ?, rule_results = ?, status = 'CHECK_COMPLETED', updated_at = ?
        WHERE id = ?
        """,
        (score, status, json.dumps(rule_results), datetime.utcnow().isoformat(), scan_id)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_scan_by_id(scan_id: int):
    """Retrieves a single scan record strictly by scan_id. No unscoped queries or first() or LIMIT 1 without id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM scan_records WHERE id = ?",
        (scan_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(row)
        if data.get("rule_results") and isinstance(data["rule_results"], str):
            try:
                data["rule_results"] = json.loads(data["rule_results"])
            except Exception:
                pass
        return data
    return None

def get_all_scans():
    """Returns recent scans ordered by ID descending."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, filename, commodity_type, compliance_score, compliance_status, status, created_at FROM scan_records ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]