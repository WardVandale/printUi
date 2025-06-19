import sqlite3
import re
from werkzeug.security import generate_password_hash

from app.models import DB_PATH

def is_strong_password(password):
    return (
        len(password) >= 8 and
        re.search(r"[A-Z]", password) and
        re.search(r"[a-z]", password) and
        re.search(r"[0-9]", password) and
        re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )

def create_admin(username, password):
    if not is_strong_password(password):
        raise ValueError("Password not strong enough")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    hashed = generate_password_hash(password)
    c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)", (username, hashed))
    conn.commit()
    conn.close()