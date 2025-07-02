import sqlite3
import os
from flask_login import UserMixin
import cups

DB_PATH = '/data/database.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        is_admin BOOLEAN
    )''')

    # Printers
    c.execute('''CREATE TABLE IF NOT EXISTS printers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        uri TEXT
    )''')

    # Jobs
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        printer_id INTEGER,
        job_id INTEGER,
        status TEXT
    )''')

    conn.commit()
    conn.close()

def has_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def get_printers():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM printers")
    printers = [row[0] for row in c.fetchall()]
    conn.close()
    return printers

def insert_printer(name, uri):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO printers (name, uri) VALUES (?, ?)", (name, uri))
    conn.commit()
    conn.close()

def get_printer_uri_by_name(name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT uri FROM printers WHERE name = ?", (name,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def insert_job(filename, printer_name, job_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO jobs (filename, printer_id, job_id, status) VALUES (?, ?, ?, ?)",
              (filename, printer_name, job_id, status))
    conn.commit()
    conn.close()
    refresh_all_job_statuses()

def update_job(filename, printer_name, job_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE jobs SET status = ? WHERE job_id = ? AND printer_id = ? AND filename = ?", (status, job_id, printer_name, filename))
    conn.commit()
    conn.close()

def get_all_jobs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT filename, printer_id AS printer, status, job_id FROM jobs ORDER BY id DESC")
    jobs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jobs

class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

def get_user_by_username(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(row[0], row[1])
    return None

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(row[0], row[1])
    return None

def refresh_all_job_statuses():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filename, printer_id, job_id, status FROM jobs WHERE status NOT IN ('completed', 'failed')")
    pending_jobs = c.fetchall()
    conn.close()

    cups_conn = cups.Connection()
    active_jobs = cups_conn.getJobs(
        my_jobs=True,
        which_jobs='all',
        requested_attributes=['job-id', 'job-state', 'job-name', 'printer-uri']
    )

    for filename, printer_name, job_id, current_status in pending_jobs:
        matching_job = next(
            (job for job in active_jobs.values() if 'job-id' in job and job['job-id'] == job_id),
            None
        )

        if matching_job:
            state_code = matching_job.get('job-state', -1)
            state_map = {
                3: 'pending',
                4: 'held',
                5: 'processing',
                6: 'stopped',
                7: 'canceled',
                8: 'aborted',
                9: 'completed'
            }
            new_status = state_map.get(state_code, 'unknown')
        else:
            new_status = 'completed'

        if new_status != current_status:
            update_job(filename, printer_name, job_id, new_status)