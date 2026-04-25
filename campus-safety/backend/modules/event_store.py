"""事件存储模块 - SQLite 持久化"""
import sqlite3
import json
import os
import uuid
from datetime import datetime
from threading import Lock

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "events.db")
_lock = Lock()

def _ensure_schema(conn: sqlite3.Connection):
    """
    确保数据库表结构存在。

    说明：有些场景下（例如运行中删除了 events.db，或首次运行刚创建空文件）
    仅在 import 时 init_db 可能不足，因此在每次获取连接时也做一次兜底建表。
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            camera_id TEXT,
            camera_name TEXT,
            behavior TEXT,
            confidence REAL,
            clip_path TEXT,
            vl_result TEXT,
            report TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            recipient TEXT,
            phone TEXT,
            role TEXT,
            message TEXT,
            status TEXT,
            event_id TEXT
        )
    """)
    conn.commit()

def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn

def init_db():
    with _lock:
        conn = _get_conn()
        # _get_conn 内已保证建表，这里只做一次连接验证
        conn.close()

# 启动时初始化
init_db()

def add_event(camera_id, camera_name, behavior, confidence, clip_path, vl_result, report):
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "camera_id": camera_id,
        "camera_name": camera_name,
        "behavior": behavior,
        "confidence": round(confidence, 3),
        "clip_path": clip_path or "",
        "vl_result": vl_result,
        "report": report,
        "status": "pending",
    }
    with _lock:
        conn = _get_conn()
        conn.execute("""
            INSERT INTO events (id, timestamp, camera_id, camera_name, behavior, confidence, clip_path, vl_result, report, status)
            VALUES (:id, :timestamp, :camera_id, :camera_name, :behavior, :confidence, :clip_path, :vl_result, :report, :status)
        """, event)
        conn.commit()
        conn.close()
    return event

def get_events(limit=50, behavior=None, camera_id=None, date_start=None, date_end=None):
    with _lock:
        conn = _get_conn()
        sql = "SELECT * FROM events WHERE 1=1"
        params = []
        if behavior:
            sql += " AND behavior=?"
            params.append(behavior)
        if camera_id:
            sql += " AND camera_id=?"
            params.append(camera_id)
        if date_start:
            sql += " AND timestamp >= ?"
            params.append(date_start)
        if date_end:
            sql += " AND timestamp <= ?"
            params.append(date_end + "T23:59:59")
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
    return [dict(r) for r in rows]

def get_event_by_id(event_id):
    with _lock:
        conn = _get_conn()
        row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        conn.close()
    return dict(row) if row else None

def update_event_status(event_id, status):
    with _lock:
        conn = _get_conn()
        conn.execute("UPDATE events SET status=? WHERE id=?", (status, event_id))
        conn.commit()
        conn.close()
    return True

def get_stats(date_start=None, date_end=None):
    with _lock:
        conn = _get_conn()
        sql = "SELECT behavior, camera_name, timestamp FROM events WHERE 1=1"
        params = []
        if date_start:
            sql += " AND timestamp >= ?"
            params.append(date_start)
        if date_end:
            sql += " AND timestamp <= ?"
            params.append(date_end + "T23:59:59")
        rows = conn.execute(sql, params).fetchall()
        conn.close()

    behavior_count = {}
    camera_count = {}
    hourly = {}

    for r in rows:
        b = r["behavior"]
        behavior_count[b] = behavior_count.get(b, 0) + 1
        c = r["camera_name"]
        camera_count[c] = camera_count.get(c, 0) + 1
        hour = r["timestamp"][11:13] + ":00"
        hourly[hour] = hourly.get(hour, 0) + 1

    return {
        "total": len(rows),
        "by_behavior": behavior_count,
        "by_camera": camera_count,
        "by_hour": hourly,
    }

def natural_language_query(query_text):
    with _lock:
        conn = _get_conn()
        rows = conn.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 200").fetchall()
        conn.close()
    data = [dict(r) for r in rows]

    query_lower = query_text.lower()
    results = data

    for keyword in ["打架", "fighting"]:
        if keyword in query_lower:
            results = [e for e in data if e["behavior"] == "fighting"]
            break
    for keyword in ["霸凌", "bullying"]:
        if keyword in query_lower:
            results = [e for e in data if e["behavior"] == "bullying"]
            break
    for keyword in ["今天"]:
        if keyword in query_lower:
            today = datetime.now().strftime("%Y-%m-%d")
            results = [e for e in results if e["timestamp"].startswith(today)]
            break

    return results[:20]

def save_notification(record):
    with _lock:
        conn = _get_conn()
        conn.execute("""
            INSERT INTO notifications (time, recipient, phone, role, message, status, event_id)
            VALUES (:time, :recipient, :phone, :role, :message, :status, :event_id)
        """, record)
        conn.commit()
        conn.close()

def get_notifications(limit=30):
    with _lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM notifications ORDER BY time DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
    return [dict(r) for r in rows]
