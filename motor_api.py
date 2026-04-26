"""
MBC2 Motor Registry API
Drop-in API handler for the existing MBC2 server.py

HOW TO INTEGRATE INTO server.py:
1. Copy this file into the same folder as server.py
2. Add this import near the top of server.py:
       from motor_api import handle_motor_api
3. In your MBC2Handler.do_GET and do_POST, add before the existing route checks:
       if self.path.startswith('/api/motors') or self.path.startswith('/api/profiles'):
           handle_motor_api(self)
           return

ROUTES:
  GET  /api/motors              — list all motors (active by default)
  GET  /api/motors/<id>         — get single motor with full history
  POST /api/motors/register     — register a new motor
  POST /api/motors/<id>/status  — update motor status
  GET  /api/profiles            — list all break-in profiles with sub-programs
  POST /api/profiles/import     — import programs from JSON
  GET  /api/motors/<id>/history — get break-in history for a motor
"""

import json
import sys
from pathlib import Path

# Ensure db_manager is importable from same directory
sys.path.insert(0, str(Path(__file__).parent))
import db_manager as db


def _send_json(handler, data, status=200):
    """Send a JSON response."""
    body = json.dumps(data, default=str).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Content-Length', len(body))
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.end_headers()
    handler.wfile.write(body)


def _send_error(handler, message, status=400):
    """Send an error response."""
    _send_json(handler, {'error': message}, status)


def _read_body(handler):
    """Read and parse JSON request body."""
    length = int(handler.headers.get('Content-Length', 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode('utf-8'))


def handle_motor_api(handler):
    """
    Main router — call this from server.py do_GET and do_POST.
    Strips query strings before matching routes.
    """
    path = handler.path.split('?')[0].rstrip('/')
    method = handler.command

    # ── GET /api/motors ─────────────────────────────────────────
    if method == 'GET' and path == '/api/motors':
        motors = db.list_motors(status='Active')
        _send_json(handler, {'motors': motors, 'count': len(motors)})
        return

    # ── GET /api/motors/all ──────────────────────────────────────
    if method == 'GET' and path == '/api/motors/all':
        motors = db.list_motors(status=None)
        _send_json(handler, {'motors': motors, 'count': len(motors)})
        return

    # ── GET /api/motors/<identifier> ────────────────────────────
    # e.g. /api/motors/SD-R-01
    if method == 'GET' and path.startswith('/api/motors/'):
        parts = path.split('/')
        if len(parts) == 4:
            identifier = parts[3]
            motor = db.get_motor_by_identifier(identifier)
            if motor:
                motor['breakin_history'] = db.get_motor_breakin_history(motor['motor_id'])
                _send_json(handler, motor)
            else:
                _send_error(handler, f'Motor not found: {identifier}', 404)
            return

        # ── GET /api/motors/<id>/history ─────────────────────────
        if len(parts) == 5 and parts[4] == 'history':
            identifier = parts[3]
            motor = db.get_motor_by_identifier(identifier)
            if motor:
                history = db.get_motor_breakin_history(motor['motor_id'])
                _send_json(handler, {'identifier': identifier, 'history': history})
            else:
                _send_error(handler, f'Motor not found: {identifier}', 404)
            return

    # ── POST /api/motors/register ────────────────────────────────
    if method == 'POST' and path == '/api/motors/register':
        try:
            body = _read_body(handler)
            model_code   = body.get('model_code')
            direction    = body.get('direction')
            chassis_ids  = body.get('chassis_ids', [])
            program_ids  = body.get('program_ids', [])
            pre_treatment = body.get('pre_treatment', '')
            notes        = body.get('notes', '')

            # Combine pre_treatment and notes into the notes field
            combined_notes = ''
            if pre_treatment:
                combined_notes = f'Pre-treatment: {pre_treatment}'
            if notes:
                combined_notes = (combined_notes + '\n' + notes).strip() if combined_notes else notes

            if not model_code or not direction:
                _send_error(handler, 'model_code and direction are required')
                return
            if direction not in ('F', 'R'):
                _send_error(handler, 'direction must be F or R')
                return

            motor = db.register_motor(
                model_code=model_code,
                direction=direction,
                chassis_ids=chassis_ids if chassis_ids else None,
                notes=combined_notes or None
            )

            if program_ids:
                db.log_breakin_run(motor['motor_id'], program_ids)

            motor['breakin_history'] = db.get_motor_breakin_history(motor['motor_id'])
            _send_json(handler, {
                'success': True,
                'motor': motor,
                'message': f"Motor {motor['identifier']} registered successfully"
            }, 201)

        except ValueError as e:
            _send_error(handler, str(e))
        except Exception as e:
            _send_error(handler, f'Registration failed: {str(e)}', 500)
        return

    # ── POST /api/motors/<identifier>/status ─────────────────────
    if method == 'POST' and path.startswith('/api/motors/') and path.endswith('/status'):
        parts = path.split('/')
        if len(parts) == 5:
            identifier = parts[3]
            motor = db.get_motor_by_identifier(identifier)
            if not motor:
                _send_error(handler, f'Motor not found: {identifier}', 404)
                return
            body = _read_body(handler)
            status = body.get('status')
            if status not in ('Active', 'Retired', 'Lost', 'Damaged'):
                _send_error(handler, 'status must be Active, Retired, Lost, or Damaged')
                return
            db.update_motor_status(motor['motor_id'], status)
            _send_json(handler, {'success': True, 'identifier': identifier, 'status': status})
            return

    # ── GET /api/profiles ────────────────────────────────────────
    if method == 'GET' and path == '/api/profiles':
        profiles = db.get_all_profiles()
        _send_json(handler, {'profiles': profiles, 'count': len(profiles)})
        return

    # ── GET /api/profiles/<id> ───────────────────────────────────
    if method == 'GET' and path.startswith('/api/profiles/'):
        parts = path.split('/')
        if len(parts) == 4:
            try:
                profile_id = int(parts[3])
                profile = db.get_profile_with_steps(profile_id)
                if profile:
                    _send_json(handler, profile)
                else:
                    _send_error(handler, f'Profile not found: {profile_id}', 404)
            except ValueError:
                _send_error(handler, 'Profile ID must be an integer')
            return

    # ── POST /api/profiles/import ────────────────────────────────
    if method == 'POST' and path == '/api/profiles/import':
        try:
            body = _read_body(handler)
            # Write to a temp file and import
            import tempfile, os
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.json', delete=False
            ) as tmp:
                json.dump(body, tmp)
                tmp_path = tmp.name
            count = db.import_programs_from_json(tmp_path)
            os.unlink(tmp_path)
            _send_json(handler, {
                'success': True,
                'imported': count,
                'message': f'Imported {count} profiles'
            })
        except Exception as e:
            _send_error(handler, f'Import failed: {str(e)}', 500)
        return

    # ── POST /api/motors/session/start ───────────────────────────
    if method == 'POST' and path == '/api/motors/session/start':
        try:
            body = _read_body(handler)
            motor_id    = body.get('motor_id')
            session_type = body.get('session_type', 'Breakin')
            if not motor_id:
                _send_error(handler, 'motor_id required')
                return
            session_id = db.create_session(
                motor_id=motor_id,
                session_type=session_type,
                notes=body.get('notes')
            )
            _send_json(handler, {'success': True, 'session_id': session_id}, 201)
        except Exception as e:
            _send_error(handler, str(e), 500)
        return

    # ── POST /api/motors/session/finalise ────────────────────────
    if method == 'POST' and path == '/api/motors/session/finalise':
        try:
            body = _read_body(handler)
            session_id       = body.get('session_id')
            motor_id         = body.get('motor_id')
            program_id       = body.get('program_id')
            is_baseline      = body.get('is_baseline', False)
            benchmark_type   = body.get('benchmark_type', 'Periodic')  # Pre, Post, Periodic
            peak_rpm         = body.get('peak_rpm')
            avg_rpm          = body.get('avg_rpm')
            peak_current_ma  = body.get('peak_current_ma')
            avg_current_ma   = body.get('avg_current_ma')
            peak_temp        = body.get('peak_temp')
            final_temp       = body.get('final_temp')
            duration_sec     = body.get('duration_sec', 120)
            voltage_v        = body.get('voltage_v', 3.0)
            direction        = body.get('direction', 'R')

            # Log program run if program_id provided
            if program_id:
                db.log_breakin_run(motor_id, [program_id], session_id=session_id)

            # Store benchmark if it's a benchmark session
            if is_baseline and session_id and motor_id:
                db.record_benchmark_from_session(
                    session_id=session_id,
                    motor_id=motor_id,
                    benchmark_type=benchmark_type,
                    direction=direction,
                    peak_rpm=peak_rpm,
                    avg_rpm=avg_rpm,
                    peak_current_ma=peak_current_ma,
                    avg_current_ma=avg_current_ma,
                    peak_temp_c=peak_temp,
                    final_temp_c=final_temp,
                    duration_sec=duration_sec,
                    voltage_v=voltage_v
                )

            # Return updated efficiency score
            score = db.calculate_efficiency_score(motor_id) if motor_id else {}
            _send_json(handler, {'success': True, 'efficiency': score})
        except Exception as e:
            _send_error(handler, str(e), 500)
        return

    # ── GET /api/motors/<identifier>/sessions ────────────────────
    if method == 'GET' and path.startswith('/api/motors/') and path.endswith('/sessions'):
        parts = path.split('/')
        if len(parts) == 5:
            identifier = parts[3]
            motor = db.get_motor_by_identifier(identifier)
            if not motor:
                _send_error(handler, f'Motor not found: {identifier}', 404)
                return
            sessions = db.get_motor_sessions(motor['motor_id'])
            _send_json(handler, {'identifier': identifier, 'sessions': sessions})
            return

    # ── GET /api/motors/session/<id>/data ───────────────────────
    if method == 'GET' and path.startswith('/api/motors/session/'):
        parts = path.split('/')
        if len(parts) == 5 and parts[4] == 'data':
            try:
                session_id = int(parts[3])
                rows = db.get_session_data(session_id)
                _send_json(handler, {'session_id': session_id, 'rows': rows})
            except ValueError:
                _send_error(handler, 'Session ID must be integer')
            return


    # ── GET /api/motors/roster ───────────────────────────────────
    if method == 'GET' and path == '/api/motors/roster':
        roster = db.get_motor_roster()
        _send_json(handler, {'motors': roster, 'count': len(roster)})
        return

    # ── GET /api/motors/<id>/trend ───────────────────────────────
    if method == 'GET' and path.startswith('/api/motors/') and path.endswith('/trend'):
        parts = path.split('/')
        if len(parts) == 5:
            identifier = parts[3]
            motor = db.get_motor_by_identifier(identifier)
            if not motor:
                _send_error(handler, f'Motor not found: {identifier}', 404)
                return
            trend = db.get_motor_benchmark_trend(motor['motor_id'])
            score = db.calculate_efficiency_score(motor['motor_id'])
            _send_json(handler, {
                'identifier': identifier,
                'trend': trend,
                'efficiency': score
            })
            return

    # ── GET /api/motors/<id>/benchmarks ─────────────────────────
    if method == 'GET' and path.startswith('/api/motors/') and path.endswith('/benchmarks'):
        parts = path.split('/')
        if len(parts) == 5:
            identifier = parts[3]
            motor = db.get_motor_by_identifier(identifier)
            if not motor:
                _send_error(handler, f'Motor not found: {identifier}', 404)
                return
            benchmarks = db.get_motor_benchmarks(motor['motor_id'])
            score = db.calculate_efficiency_score(motor['motor_id'])
            _send_json(handler, {
                'identifier': identifier,
                'benchmarks': benchmarks,
                'efficiency': score
            })
            return

    # ── 404 fallthrough ──────────────────────────────────────────
    _send_error(handler, f'Unknown motor API route: {path}', 404)
