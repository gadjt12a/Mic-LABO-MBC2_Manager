#!/usr/bin/env python3
"""
MBC2 Dashboard Server v2.0
- Serves mbc2-dashboard.html
- Handles program library (programs.json)
- Handles motor registry (SQLite via db_manager)
- Auto-opens browser on start
- Shuts down when browser closes (keepalive watchdog)
"""

import http.server
import time
import socketserver
import webbrowser
import threading
import json
import os
import sys
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
DATA_DIR       = BASE_DIR / 'data'
DB_DIR         = BASE_DIR / 'db'
DASHBOARD_HTML = BASE_DIR / 'mbc2-dashboard.html'
PROGRAMS_JSON  = DATA_DIR / 'programs.json'
SEED_JSON      = DATA_DIR / 'seed_programs.json'

PORT               = 8766
KEEPALIVE_TIMEOUT  = 10   # seconds — shutdown if no ping received

# ── Ensure folders exist ─────────────────────────────────────
DATA_DIR.mkdir(exist_ok=True)

# ── DB setup ─────────────────────────────────────────────────
sys.path.insert(0, str(DB_DIR))
import db_manager as db
import motor_api

db.init_db()

# Seed programs on first run if programs table is empty
try:
    if not db.get_all_profiles() and SEED_JSON.exists():
        count = db.import_programs_from_json(str(SEED_JSON))
        print(f'[MBC2] Seeded {count} break-in profiles from seed_programs.json')
except Exception as e:
    print(f'[MBC2] Seed warning: {e}')

# ── Keepalive watchdog ────────────────────────────────────────
_last_ping = time.time()

def _watchdog(httpd):
    global _last_ping
    time.sleep(30)  # grace period on startup
    while True:
        time.sleep(2)
        if time.time() - _last_ping > KEEPALIVE_TIMEOUT:
            print('\n[MBC2] Browser closed — shutting down.')
            httpd.shutdown()
            break

# ── Request handler ───────────────────────────────────────────
class MBC2Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence request logging

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]

        # ── Motor / Profile API ───────────────────────────────
        if path.startswith('/api/motors') or path.startswith('/api/profiles'):
            motor_api.handle_motor_api(self)
            return

        # ── Keepalive ping ────────────────────────────────────
        if path == '/api/ping':
            global _last_ping
            _last_ping = time.time()
            self._json({'ok': True})
            return

        # ── Shutdown ──────────────────────────────────────────
        if path == '/api/shutdown':
            self._json({'ok': True, 'message': 'Server shutting down'})
            print('\n[MBC2] Shutdown requested from browser.')
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        # ── Firmware proxy ────────────────────────────────────
        if path == '/api/firmware/versions':
            try:
                import urllib.request
                req = urllib.request.Request(
                    'http://esp32.miclabo.xyz/versions.csv',
                    headers={'User-Agent': 'MBC2-Dashboard/1.0'}
                )
                with urllib.request.urlopen(req, timeout=3) as r:
                    csv_data = r.read().decode('utf-8')
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/csv')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(csv_data.encode())
                except Exception:
                    pass  # Client disconnected — harmless
            except Exception:
                try:
                    self._json({'error': 'firmware server unavailable'}, 503)
                except Exception:
                    pass  # Client disconnected — harmless
            return

        # ── Programs (existing JSON file API) ─────────────────
        if path == '/api/programs':
            if PROGRAMS_JSON.exists():
                data = json.loads(PROGRAMS_JSON.read_text())
            else:
                data = {'version': '1.0', 'profiles': []}
            self._json(data)
            return

        # ── Sessions list ─────────────────────────────────────
        if path == '/api/sessions':
            sessions_dir = DATA_DIR / 'sessions'
            sessions_dir.mkdir(exist_ok=True)
            files = sorted(sessions_dir.glob('*.csv'), reverse=True)
            self._json({'sessions': [f.name for f in files]})
            return

        # ── Session download ──────────────────────────────────
        if path.startswith('/api/sessions/'):
            fname = path.split('/')[-1]
            fpath = DATA_DIR / 'sessions' / fname
            if fpath.exists() and fpath.suffix == '.csv':
                content = fpath.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv')
                self.send_header('Content-Disposition', f'attachment; filename="{fname}"')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
            else:
                self._json({'error': 'Not found'}, 404)
            return

        # ── Serve dashboard HTML ──────────────────────────────
        if path in ('/', '/index.html', '/mbc2-dashboard.html'):
            if DASHBOARD_HTML.exists():
                content = DASHBOARD_HTML.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
            else:
                self._json({'error': 'Dashboard HTML not found'}, 404)
            return

        self._json({'error': f'Unknown route: {path}'}, 404)

    def do_POST(self):
        path = self.path.split('?')[0]

        # ── Motor / Profile API ───────────────────────────────
        if path.startswith('/api/motors') or path.startswith('/api/profiles'):
            motor_api.handle_motor_api(self)
            return

        # ── Save programs JSON ────────────────────────────────
        if path == '/api/programs':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            PROGRAMS_JSON.write_text(json.dumps(body, indent=2))
            self._json({'ok': True})
            return

        # ── Save session CSV ──────────────────────────────────
        if path == '/api/sessions':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            fname = body.get('filename', f'session_{int(time.time())}.csv')  # time imported above
            csv_data = body.get('data', '')
            sessions_dir = DATA_DIR / 'sessions'
            sessions_dir.mkdir(exist_ok=True)
            (sessions_dir / fname).write_text(csv_data)
            self._json({'ok': True, 'filename': fname})
            return

        self._json({'error': f'Unknown route: {path}'}, 404)

    def _json(self, data, status=200):
        body = json.dumps(data, default=str).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)


# ── Main ──────────────────────────────────────────────────────
if __name__ == '__main__':
    with socketserver.TCPServer(('', PORT), MBC2Handler) as httpd:
        httpd.allow_reuse_address = True
        url = f'http://localhost:{PORT}'
        print(f'[MBC2] Server running at {url}')
        print(f'[MBC2] Press Ctrl+C to stop manually')
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        threading.Thread(target=_watchdog, args=(httpd,), daemon=True).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n[MBC2] Server stopped.')
