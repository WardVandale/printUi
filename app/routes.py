import subprocess
import re
import sqlite3
import os
from urllib.parse import unquote
from flask import Blueprint, render_template, request, redirect
from app.models import has_users, get_printers, insert_printer
from app.setup import create_admin
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models import get_user_by_username, get_user_by_id, get_printers, get_printer_uri_by_name, insert_job, get_all_jobs, User, DB_PATH
from app.setup import create_admin, is_strong_password
from app.utils import onboard_or_login_required
import cups

cuppsconn = cups.Connection()
views = Blueprint('views', __name__)

def sanitize_printer_name(raw_name):
    # Decode URI-encoded characters, replace invalid characters with underscores
    name = unquote(raw_name)
    name = re.sub(r'[^A-Za-z0-9_]', '_', name)
    return name

@views.route('/', methods=['GET'])
@onboard_or_login_required
def root():
    printers = get_printers()
    jobs = get_all_jobs()
    return render_template("index.html", printers=printers)

@views.route('/onboard/user', methods=['GET', 'POST'])
def onboard_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            create_admin(username, password)
        except ValueError as e:
            flash(str(e))
            return render_template("onboarding_user.html")
        return redirect('/onboard/printers')
    return render_template("onboarding_user.html")

@views.route('/onboard/printers')
# @onboard_or_login_required
def onboard_printers():
    return render_template("onboarding_printers.html")

@views.route('/onboard/printers/scan', methods=['POST'])
# @onboard_or_login_required
def scan_and_install_printers():
    result = subprocess.run(['lpinfo', '-v'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    for line in lines:
        if line.startswith("network dnssd://") or line.startswith("network ipp://"):
            try:
                uri = line.split("network ")[1].strip()
                raw_name = uri.split("://")[1].split("._")[0]
                clean_name = sanitize_printer_name(raw_name)
                subprocess.run(['lpadmin', '-p', clean_name, '-E', '-v', uri, '-m', 'everywhere'], check=True)
                insert_printer(clean_name, uri)
            except subprocess.CalledProcessError as e:
                print(f"[!] Printer setup failed: {e}")
    return {"status": "ok"}

@views.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = get_user_by_username(request.form['username'])
        if user:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username = ?", (user.username,))
            stored_hash = c.fetchone()[0]
            conn.close()

            if check_password_hash(stored_hash, request.form['password']):
                login_user(user)
                return redirect(url_for('views.root'))

        flash('Invalid username or password')
    return render_template("login.html")

@views.route('/upload', methods=['POST'])
@login_required
def upload_file():
    printer_name = request.form.get('printer')
    duplex = request.form.get('duplex')
    options={}
    if duplex == 'on':  options= {"sides": "two-sided-long-edge"}
    file = request.files.get('file')

    if not printer_name or not file:
        return "Missing printer or file", 400

    # Save file to /data/printjobs
    save_path = os.path.join("/data/printjobs", file.filename)
    file.save(save_path)

    # Get printer URI from DB (if stored) or use printer name directly
    printer_uri = get_printer_uri_by_name(printer_name) or printer_name

    # Submit print job
    try:
        job_id = cuppsconn.printFile(printer_name, save_path, file.filename, options)
        insert_job(file.filename, printer_name, job_id, "submitted")
        return redirect('/')
    except cuppsconn.IPPError as e:
        return f"Print failed: {e}", 500

@views.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.login'))