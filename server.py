#!/usr/bin/env python3
"""
MBC2 Dashboard Server v2.0
- Serves mbc2-dashboard.html
- Handles program library (programs.json)
- Handles motor registry (SQLite via db_manager)
- Auto-opens browser on start
- Shuts down via Stop Server button in app or Ctrl+C
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
# Look for seed file in multiple locations
_seed_candidates = [
    DATA_DIR / 'seed_programs.json',
    BASE_DIR / 'default_programs.json',
    BASE_DIR / 'src' / 'data' / 'default_programs.json',
    DATA_DIR / 'default_programs.json',
]
SEED_JSON = next((p for p in _seed_candidates if p.exists()), _seed_candidates[0])

PORT               = 8766

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
        print(f'[MBC2] Seeded {count} break-in profiles from {SEED_JSON.name}')
except Exception as e:
    print(f'[MBC2] Seed warning: {e}')

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
            self._json({'ok': True})
            return

        # ── Session data rows (for compare chart) ────────────
        if path.startswith('/api/motors/session/') and path.endswith('/data'):
            parts = path.split('/')
            if len(parts) == 6:
                try:
                    import csv as csv_mod
                    from datetime import datetime
                    session_id = int(parts[4])
                    with db.get_connection() as conn:
                        sess = conn.execute(
                            'SELECT * FROM sessions WHERE session_id = ?', (session_id,)
                        ).fetchone()
                    if not sess:
                        self._json({'error': 'Session not found'}, 404)
                        return
                    sess = dict(sess)
                    sess_date = sess.get('session_date', '')[:16]  # YYYY-MM-DD HH:MM

                    # Find best matching CSV by timestamp proximity
                    sessions_dir = DATA_DIR / 'sessions'
                    best_file = None
                    best_diff = float('inf')
                    for csv_file in sessions_dir.glob('*.csv'):
                        try:
                            mtime = datetime.fromtimestamp(csv_file.stat().st_mtime)
                            # Try parsing session_date
                            if sess_date:
                                sd = datetime.fromisoformat(sess_date)
                                diff = abs((mtime - sd).total_seconds())
                                if diff < best_diff:
                                    best_diff = diff
                                    best_file = csv_file
                        except Exception:
                            continue

                    rows = []
                    if best_file and best_diff < 300:  # within 5 minutes
                        try:
                            with open(best_file, 'r') as f:
                                reader = csv_mod.DictReader(f)
                                rows = [{'rpm': int(r.get('rpm', 0) or 0),
                                        'amps': float(r.get('amps', 0) or 0),
                                        'volts': float(r.get('volts', 0) or 0),
                                        'kv': int(r.get('kv', 0) or 0),
                                        'temp': int(r.get('temp', 0) or 0),
                                        'step': int(r.get('step', 0) or 0),
                                        'elapsed': int(r.get('elapsed_ms', 0) or 0)} for r in reader]
                        except Exception:
                            pass

                    self._json({'session_id': session_id, 'rows': rows,
                               'peak_rpm': sess.get('peak_rpm'),
                               'session_date': sess.get('session_date'),
                               'csv_matched': best_file.name if best_file else None})
                except Exception as e:
                    self._json({'error': str(e)}, 500)
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
                self.send_header('Content-Length', len(content))
                self.send_header('Access-Control-Allow-Origin', '*')
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

    def do_DELETE(self):
        path = self.path.split('?')[0]

        # ── Delete session CSV ────────────────────────────────
        if path.startswith('/api/sessions/'):
            fname = path.split('/')[-1]
            fpath = DATA_DIR / 'sessions' / fname
            if fpath.exists() and fpath.suffix == '.csv':
                fpath.unlink()
                self._json({'ok': True, 'deleted': fname})
            else:
                self._json({'error': 'Not found'}, 404)
            return

        # ── Delete motor + all sessions/benchmarks ───────────
        if path.startswith('/api/motors/') and len(path.split('/')) == 4:
            identifier = path.split('/')[3]
            motor = db.get_motor_by_identifier(identifier)
            if motor:
                try:
                    with db.get_connection() as conn:
                        motor_id = motor['motor_id']
                        # Enable foreign keys and delete in correct order
                        conn.execute('PRAGMA foreign_keys = OFF')
                        conn.execute('DELETE FROM motor_breakin_log WHERE motor_id = ?', (motor_id,))
                        conn.execute('DELETE FROM benchmarks WHERE motor_id = ?', (motor_id,))
                        conn.execute('DELETE FROM sessions WHERE motor_id = ?', (motor_id,))
                        conn.execute('DELETE FROM motor_chassis_assignments WHERE motor_id = ?', (motor_id,))
                        conn.execute('DELETE FROM motors WHERE motor_id = ?', (motor_id,))
                        conn.execute('PRAGMA foreign_keys = ON')
                        conn.commit()
                    self._json({'ok': True, 'deleted': identifier})
                    print(f'[MBC2] Motor deleted: {identifier}')
                except Exception as e:
                    print(f'[MBC2] Delete error: {e}')
                    self._json({'error': str(e)}, 500)
            else:
                self._json({'error': 'Motor not found'}, 404)
            return

        # ── Delete individual session ─────────────────────────
        if path.startswith('/api/motors/session/') and not path.endswith('/data'):
            parts = path.split('/')
            if len(parts) == 5:
                try:
                    session_id = int(parts[4])
                    with db.get_connection() as conn:
                        conn.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                        conn.commit()
                    self._json({'ok': True, 'deleted': session_id})
                except Exception as e:
                    self._json({'error': str(e)}, 500)
            return

        # ── Clear motor DB sessions ───────────────────────────
        if path.startswith('/api/motors/') and path.endswith('/sessions/clear'):
            parts = path.split('/')
            if len(parts) >= 4:
                identifier = parts[3]
                motor = db.get_motor_by_identifier(identifier)
                if motor:
                    try:
                        with db.get_connection() as conn:
                            conn.execute('DELETE FROM sessions WHERE motor_id = ?', (motor['motor_id'],))
                            conn.commit()
                        self._json({'ok': True, 'cleared': identifier})
                    except Exception as e:
                        self._json({'error': str(e)}, 500)
                else:
                    self._json({'error': 'Motor not found'}, 404)
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
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n[MBC2] Server stopped.')
