import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "incidents.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT UNIQUE NOT NULL,
            service TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT DEFAULT 'ANALYZED',
            created_at TEXT NOT NULL,
            raw_input TEXT NOT NULL,
            analysis_result TEXT NOT NULL,
            root_cause TEXT,
            confidence TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_incident(incident_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    incident_id = incident_data.get("incident_id") or analysis_result.get("incident_id") or f"INC-{int(datetime.now().timestamp())}"
    service = incident_data.get("service") or analysis_result.get("service") or "Unknown"
    severity = incident_data.get("severity") or analysis_result.get("severity") or "MEDIUM"
    created_at = datetime.now().isoformat()
    raw_input_json = json.dumps(incident_data)
    analysis_result_json = json.dumps(analysis_result)
    root_cause = analysis_result.get("root_cause", "")
    confidence = analysis_result.get("confidence", "MEDIUM")

    cursor.execute("""
        INSERT INTO incidents (incident_id, service, severity, status, created_at, raw_input, analysis_result, root_cause, confidence)
        VALUES (?, ?, ?, 'ANALYZED', ?, ?, ?, ?, ?)
        ON CONFLICT(incident_id) DO UPDATE SET
            service=excluded.service,
            severity=excluded.severity,
            status='ANALYZED',
            created_at=excluded.created_at,
            raw_input=excluded.raw_input,
            analysis_result=excluded.analysis_result,
            root_cause=excluded.root_cause,
            confidence=excluded.confidence
    """, (incident_id, service, severity, created_at, raw_input_json, analysis_result_json, root_cause, confidence))

    conn.commit()
    conn.close()

    return {
        "incident_id": incident_id,
        "service": service,
        "severity": severity,
        "created_at": created_at,
        "root_cause": root_cause,
        "confidence": confidence,
        "analysis": analysis_result
    }


def list_incidents(limit: int = 50) -> List[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, incident_id, service, severity, status, created_at, root_cause, confidence
        FROM incidents
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_incident(incident_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, incident_id, service, severity, status, created_at, raw_input, analysis_result, root_cause, confidence
        FROM incidents
        WHERE incident_id = ?
    """, (incident_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    data = dict(row)
    data["raw_input"] = json.loads(data["raw_input"])
    data["analysis_result"] = json.loads(data["analysis_result"])
    return data


def delete_incident(incident_id: str) -> bool:
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM incidents WHERE incident_id = ?", (incident_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0
