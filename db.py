import sqlite3
import os
from datetime import datetime

DB_PATH = "database/fall_events.db"

def get_conn():
    os.makedirs("database", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fall_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_name TEXT NOT NULL,
            image_path TEXT,
            location TEXT,
            timestamp TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def save_fall_event(person_name, image_path, location, timestamp):
    conn = get_conn()
    conn.execute("""
        INSERT INTO fall_events (person_name, image_path, location, timestamp)
        VALUES (?, ?, ?, ?)
    """, (person_name, image_path, location, timestamp))
    conn.commit()
    conn.close()

def get_all_events():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM fall_events ORDER BY timestamp DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_weekly_stats():
    """สถิติรายบุคคลใน 7 วันที่ผ่านมา"""
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT 
            person_name,
            COUNT(*) as total_falls,
            date(timestamp) as fall_date
        FROM fall_events
        WHERE timestamp >= datetime('now', '+7 hours', '-6 days')
        GROUP BY person_name, date(timestamp)
        ORDER BY fall_date DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_person_stats(person_name):
    """สถิติรายบุคคล 7 วัน"""
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT 
            date(timestamp) as fall_date,
            COUNT(*) as count
        FROM fall_events
        WHERE person_name = ?
          AND timestamp >= datetime('now', '+7 hours', '-6 days')
        GROUP BY date(timestamp)
        ORDER BY fall_date ASC
    """, (person_name,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_persons():
    conn = get_conn()
    rows = conn.execute("""
        SELECT DISTINCT person_name FROM fall_events ORDER BY person_name
    """).fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_summary():
    """ภาพรวมทั้งหมด"""
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT 
            COUNT(*) as total_events,
            COUNT(DISTINCT person_name) as total_persons,
            COUNT(CASE WHEN timestamp >= datetime('now', '+7 hours', '-6 days') THEN 1 END) as week_events,
            COUNT(CASE WHEN timestamp >= datetime('now', '+7 hours') THEN 1 END) as today_events
        FROM fall_events
    """).fetchone()
    conn.close()
    return dict(row) if row else {}
