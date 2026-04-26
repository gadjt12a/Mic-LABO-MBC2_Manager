"""
MBC2 Motor Tracking Database Manager
Handles all DB operations for motor registry, sessions, and benchmarks.
"""

import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).parent / "mbc2.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Get a DB connection with row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    """Initialise the database from schema if it doesn't exist."""
    if not DB_PATH.exists():
        print(f"Creating new database at {DB_PATH}")
        with get_connection() as conn:
            with open(SCHEMA_PATH, 'r') as f:
                conn.executescript(f.read())
        print("Database initialised successfully.")
    else:
        print(f"Database already exists at {DB_PATH}")


# ============================================================
# MOTOR REGISTRY
# ============================================================

def get_next_motor_identifier(model_code: str, direction: str) -> str:
    """
    Generate the next identifier for a motor e.g. SD-R-01, SD-R-02
    Sequence resets per model code.
    """
    with get_connection() as conn:
        prefix = f"{model_code}-{direction}-"
        result = conn.execute("""
            SELECT identifier FROM motors
            WHERE identifier LIKE ?
            ORDER BY identifier DESC
            LIMIT 1
        """, (f"{prefix}%",)).fetchone()

        if result is None:
            return f"{prefix}01"
        
        last = result['identifier']
        last_num = int(last.split('-')[-1])
        return f"{prefix}{str(last_num + 1).zfill(2)}"


def register_motor(model_code: str, direction: str, chassis_ids: list = None, notes: str = None) -> dict:
    """
    Register a new motor. Returns the created motor record.
    
    Args:
        model_code: e.g. 'SD' for Sprint Dash
        direction: 'F' or 'R'
        chassis_ids: list of chassis_id ints this motor is intended for
        notes: optional notes
    """
    with get_connection() as conn:
        # Look up model
        model = conn.execute(
            "SELECT * FROM motor_models WHERE code = ?", (model_code,)
        ).fetchone()
        
        if not model:
            raise ValueError(f"Unknown motor model code: {model_code}")
        
        # Generate identifier
        identifier = get_next_motor_identifier(model_code, direction)
        
        # Insert motor
        cursor = conn.execute("""
            INSERT INTO motors (identifier, model_id, breakin_direction, notes)
            VALUES (?, ?, ?, ?)
        """, (identifier, model['model_id'], direction, notes))
        
        motor_id = cursor.lastrowid
        
        # Assign chassis if provided
        if chassis_ids:
            for chassis_id in chassis_ids:
                conn.execute("""
                    INSERT OR IGNORE INTO motor_chassis_assignments (motor_id, chassis_id)
                    VALUES (?, ?)
                """, (motor_id, chassis_id))
        
        conn.commit()
        return get_motor(motor_id)


def get_motor(motor_id: int) -> dict:
    """Get a motor record with full detail."""
    with get_connection() as conn:
        motor = conn.execute("""
            SELECT v.*, 
                   GROUP_CONCAT(c.name, ', ') as chassis_names
            FROM v_motor_summary v
            LEFT JOIN motor_chassis_assignments mca ON v.motor_id = mca.motor_id
            LEFT JOIN chassis c ON mca.chassis_id = c.chassis_id
            WHERE v.motor_id = ?
            GROUP BY v.motor_id
        """, (motor_id,)).fetchone()
        
        return dict(motor) if motor else None


def get_motor_by_identifier(identifier: str) -> dict:
    """Get a motor by its label identifier e.g. 'SD-R-01'."""
    with get_connection() as conn:
        motor = conn.execute(
            "SELECT motor_id FROM motors WHERE identifier = ?", (identifier,)
        ).fetchone()
        if motor:
            return get_motor(motor['motor_id'])
        return None


def list_motors(status: str = 'Active') -> list:
    """List all motors, optionally filtered by status."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT v.*,
                   GROUP_CONCAT(c.name, ', ') as chassis_names
            FROM v_motor_summary v
            LEFT JOIN motor_chassis_assignments mca ON v.motor_id = mca.motor_id
            LEFT JOIN chassis c ON mca.chassis_id = c.chassis_id
            WHERE (? IS NULL OR v.status = ?)
            GROUP BY v.motor_id
            ORDER BY v.model_code, v.identifier
        """, (status, status)).fetchall()
        return [dict(r) for r in rows]


def update_motor_status(motor_id: int, status: str):
    """Update motor status: Active, Retired, Lost, Damaged."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE motors SET status = ? WHERE motor_id = ?",
            (status, motor_id)
        )
        conn.commit()


# ============================================================
# SESSIONS
# ============================================================

def create_session(motor_id: int, session_type: str, notes: str = None, ambient_temp_c: float = None) -> int:
    """Create a new session record. Returns session_id."""
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO sessions (motor_id, session_type, notes, ambient_temp_c)
            VALUES (?, ?, ?, ?)
        """, (motor_id, session_type, notes, ambient_temp_c))
        conn.commit()
        return cursor.lastrowid


def log_session_data(session_id: int, rows: list):
    """
    Bulk insert parsed MBC2 data rows into session_data.
    
    Each row dict should contain parsed MBC2 CSV fields.
    """
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO session_data 
            (session_id, timestamp_ms, raw_line, mode, program_step,
             voltage_mv, current_ma, rpm, temp_c, elapsed_sec, rpm_cap, kv_efficiency)
            VALUES 
            (:session_id, :timestamp_ms, :raw_line, :mode, :program_step,
             :voltage_mv, :current_ma, :rpm, :temp_c, :elapsed_sec, :rpm_cap, :kv_efficiency)
        """, rows)
        conn.commit()


def get_session_data(session_id: int) -> list:
    """Get all data rows for a session."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM session_data WHERE session_id = ? ORDER BY timestamp_ms",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# BENCHMARKS
# ============================================================

def record_benchmark(session_id: int, motor_id: int, benchmark_type: str,
                     direction: str, data_rows: list, notes: str = None) -> int:
    """
    Calculate and store benchmark summary from session data rows.
    benchmark_type: 'Pre', 'Post', or 'Periodic'
    Returns benchmark_id.
    """
    rpms = [r['rpm'] for r in data_rows if r.get('rpm') and r['rpm'] > 0]
    currents = [r['current_ma'] for r in data_rows if r.get('current_ma')]
    temps = [r['temp_c'] for r in data_rows if r.get('temp_c')]

    peak_rpm = max(rpms) if rpms else None
    avg_rpm = int(sum(rpms) / len(rpms)) if rpms else None
    peak_current = max(currents) if currents else None
    avg_current = int(sum(currents) / len(currents)) if currents else None
    peak_temp = max(temps) if temps else None
    final_temp = temps[-1] if temps else None

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO benchmarks 
            (session_id, motor_id, benchmark_type, voltage_v, direction,
             duration_sec, peak_rpm, avg_rpm, peak_current_ma, avg_current_ma,
             peak_temp_c, final_temp_c, notes)
            VALUES (?, ?, ?, 3.0, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, motor_id, benchmark_type, direction,
              len(data_rows),  # duration as row count for now
              peak_rpm, avg_rpm, peak_current, avg_current,
              peak_temp, final_temp, notes))
        conn.commit()
        return cursor.lastrowid


def get_motor_benchmarks(motor_id: int) -> list:
    """Get all benchmarks for a motor in chronological order."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM v_benchmark_comparison
            WHERE identifier = (SELECT identifier FROM motors WHERE motor_id = ?)
            ORDER BY session_date
        """, (motor_id,)).fetchall()
        return [dict(r) for r in rows]


def compare_benchmarks(motor_id: int) -> dict:
    """
    Compare Pre vs Post benchmark for a motor.
    Returns dict with delta values.
    """
    benchmarks = get_motor_benchmarks(motor_id)
    pre = next((b for b in benchmarks if b['benchmark_type'] == 'Pre'), None)
    post = next((b for b in reversed(benchmarks) if b['benchmark_type'] == 'Post'), None)

    if not pre or not post:
        return {'error': 'Need both Pre and Post benchmarks to compare'}

    return {
        'motor_identifier': pre['identifier'],
        'pre': pre,
        'post': post,
        'delta': {
            'peak_rpm': (post['peak_rpm'] or 0) - (pre['peak_rpm'] or 0),
            'avg_rpm': (post['avg_rpm'] or 0) - (pre['avg_rpm'] or 0),
            'peak_current_ma': (post['peak_current_ma'] or 0) - (pre['peak_current_ma'] or 0),
            'peak_temp_c': (post['peak_temp_c'] or 0) - (pre['peak_temp_c'] or 0),
        }
    }


# ============================================================
# LOOKUP HELPERS
# ============================================================

def get_all_motor_models() -> list:
    """Get all motor models for UI dropdowns."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM motor_models ORDER BY speed_stars, torque_stars"
        ).fetchall()
        return [dict(r) for r in rows]


def get_chassis_for_direction(direction: str) -> list:
    """Get chassis compatible with a given break-in direction."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT c.*, mt.name as mount_type, mt.default_direction
            FROM chassis c
            JOIN mount_types mt ON c.mount_type_id = mt.mount_type_id
            WHERE mt.default_direction = ? OR mt.default_direction IS NULL
            ORDER BY mt.name, c.name
        """, (direction,)).fetchall()
        return [dict(r) for r in rows]


def get_chassis_for_shaft_type(shaft_type: str) -> list:
    """Get chassis compatible with a given shaft type (Single/Dual)."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT c.*, mt.name as mount_type, mt.default_direction
            FROM chassis c
            JOIN mount_types mt ON c.mount_type_id = mt.mount_type_id
            WHERE mt.shaft_type = ?
            ORDER BY mt.name, c.name
        """, (shaft_type,)).fetchall()
        return [dict(r) for r in rows]


def update_mount_direction(mount_type_name: str, direction: str):
    """
    Update the confirmed break-in direction for a mount type.
    Call this once Kris has confirmed Rear and Midship directions.
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE mount_types SET default_direction = ? WHERE name = ?",
            (direction, mount_type_name)
        )
        conn.commit()
        print(f"Updated {mount_type_name} mount direction to: {direction}")




def get_motor_benchmark_trend(motor_id: int) -> dict:
    """
    Get benchmark trend for a motor — RPM improvement over time.
    Returns improvement status: improving / plateaued / declining.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT b.peak_rpm, b.avg_rpm, b.peak_current_ma, b.avg_current_ma,
                   b.voltage_v, b.final_temp_c, s.session_date
            FROM benchmarks b
            JOIN sessions s ON b.session_id = s.session_id
            WHERE b.motor_id = ?
            ORDER BY s.session_date ASC
        """, (motor_id,)).fetchall()

        benchmarks = [dict(r) for r in rows]
        if len(benchmarks) < 2:
            return {'status': 'insufficient_data', 'benchmarks': benchmarks}

        # Calculate RPM per watt (efficiency) for each benchmark
        for b in benchmarks:
            if b.get('avg_current_ma') and b.get('voltage_v') and b['avg_current_ma'] > 0:
                watts = (b['voltage_v'] * b['avg_current_ma']) / 1000
                b['rpm_per_watt'] = round((b['avg_rpm'] or 0) / watts, 1) if watts > 0 else None
            else:
                b['rpm_per_watt'] = None

        # Compare last two benchmarks
        last = benchmarks[-1]
        prev = benchmarks[-2]
        delta_rpm = (last.get('peak_rpm') or 0) - (prev.get('peak_rpm') or 0)
        pct_change = (delta_rpm / prev['peak_rpm'] * 100) if prev.get('peak_rpm') else 0

        if pct_change > 2:
            status = 'improving'
        elif pct_change < -2:
            status = 'declining'
        else:
            status = 'plateaued'

        return {
            'status': status,
            'delta_rpm': delta_rpm,
            'pct_change': round(pct_change, 1),
            'benchmarks': benchmarks,
            'latest_peak_rpm': last.get('peak_rpm'),
            'latest_rpm_per_watt': last.get('rpm_per_watt'),
        }


def calculate_efficiency_score(motor_id: int) -> dict:
    """
    Calculate motor efficiency score from best benchmark.
    Score = RPM per watt at benchmark voltage.
    Rating: A (top 25%), B (good), C (average), D (retire consideration).
    Thresholds based on Sprint/Power Dash at 3V:
      A: > 13,000 RPM/W  (e.g. 34500 RPM at 0.80A * 3V = 2.4W = 14375)
      B: 11,000-13,000
      C: 9,000-11,000
      D: < 9,000
    """
    with get_connection() as conn:
        best = conn.execute("""
            SELECT b.peak_rpm, b.avg_rpm, b.avg_current_ma, b.voltage_v, s.session_date
            FROM benchmarks b
            JOIN sessions s ON b.session_id = s.session_id
            WHERE b.motor_id = ?
            ORDER BY b.peak_rpm DESC NULLS LAST
            LIMIT 1
        """, (motor_id,)).fetchone()

        if not best:
            return {'score': None, 'rating': 'N/A', 'rpm_per_watt': None}

        best = dict(best)
        rpm_per_watt = None
        if best.get('avg_current_ma') and best.get('voltage_v') and best['avg_current_ma'] > 0:
            watts = (best['voltage_v'] * best['avg_current_ma']) / 1000
            rpm_per_watt = round((best['avg_rpm'] or 0) / watts, 1) if watts > 0 else None

        if rpm_per_watt is None:
            rating = 'N/A'
        elif rpm_per_watt >= 13000:
            rating = 'A'
        elif rpm_per_watt >= 11000:
            rating = 'B'
        elif rpm_per_watt >= 9000:
            rating = 'C'
        else:
            rating = 'D'

        return {
            'score': rpm_per_watt,
            'rating': rating,
            'peak_rpm': best.get('peak_rpm'),
            'avg_rpm': best.get('avg_rpm'),
            'avg_current_ma': best.get('avg_current_ma'),
            'voltage_v': best.get('voltage_v'),
            'session_date': best.get('session_date'),
        }


def get_motor_roster() -> list:
    """
    Get full motor roster with efficiency scores and trend for the comparison view.
    """
    with get_connection() as conn:
        motors = conn.execute("""
            SELECT v.*,
                   GROUP_CONCAT(c.name, ', ') as chassis_names
            FROM v_motor_summary v
            LEFT JOIN motor_chassis_assignments mca ON v.motor_id = mca.motor_id
            LEFT JOIN chassis c ON mca.chassis_id = c.chassis_id
            GROUP BY v.motor_id
            ORDER BY v.status, v.model_code, v.identifier
        """).fetchall()

        result = []
        for m in motors:
            m = dict(m)
            # Add efficiency score
            eff = calculate_efficiency_score(m['motor_id'])
            m['efficiency_score'] = eff.get('score')
            m['rating'] = eff.get('rating', 'N/A')
            m['best_peak_rpm'] = eff.get('peak_rpm') or m.get('best_peak_rpm')
            # Add trend
            trend = get_motor_benchmark_trend(m['motor_id'])
            m['trend'] = trend.get('status', 'insufficient_data')
            m['trend_delta_rpm'] = trend.get('delta_rpm', 0)
            m['total_benchmarks'] = m.get('total_benchmarks', 0)
            result.append(m)
        return result


def record_benchmark_from_session(session_id: int, motor_id: int,
                                   benchmark_type: str, direction: str,
                                   peak_rpm: int, avg_rpm: int,
                                   peak_current_ma: int, avg_current_ma: int,
                                   peak_temp_c: float, final_temp_c: float,
                                   duration_sec: int = 120,
                                   voltage_v: float = 3.0,
                                   notes: str = None) -> int:
    """Store a benchmark with pre-computed summary values."""
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO benchmarks
            (session_id, motor_id, benchmark_type, voltage_v, direction,
             duration_sec, peak_rpm, avg_rpm, peak_current_ma, avg_current_ma,
             peak_temp_c, final_temp_c, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, motor_id, benchmark_type, voltage_v, direction,
              duration_sec, peak_rpm, avg_rpm, peak_current_ma, avg_current_ma,
              peak_temp_c, final_temp_c, notes))
        conn.commit()
        return cursor.lastrowid


# ============================================================
# JSON MIGRATION
# ============================================================

def migrate_from_json(json_path: str):
    """
    Migrate existing session data from JSON file to SQLite.
    Expects the JSON structure from the existing dashboard.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    print(f"Migrating {len(data)} records from {json_path}")
    # TODO: implement once we know the exact JSON structure
    # This is a placeholder - will be built out when the JSON schema is confirmed
    print("Migration placeholder - implement after confirming JSON structure")




# ============================================================
# PROGRAM LIBRARY
# ============================================================

def import_programs_from_json(json_path: str) -> int:
    """
    Import profiles/programs/steps from the existing programs.json file.
    Returns number of profiles imported.
    Skips profiles that already exist by name.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)

    imported = 0
    with get_connection() as conn:
        for profile in data.get('profiles', []):
            # Skip if already exists
            existing = conn.execute(
                "SELECT profile_id FROM profiles WHERE name = ?", (profile['name'],)
            ).fetchone()
            if existing:
                print(f"  Skipping existing profile: {profile['name']}")
                continue

            cursor = conn.execute("""
                INSERT INTO profiles (name, motor_model, chassis, class, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                profile.get('name'),
                profile.get('motor'),
                profile.get('chassis'),
                profile.get('class'),
                profile.get('notes')
            ))
            profile_id = cursor.lastrowid

            for step_order, prog in enumerate(profile.get('programs', [])):
                pcursor = conn.execute("""
                    INSERT INTO programs (profile_id, name, mbc2_label, step_order, cycles, target_rpm, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    profile_id,
                    prog.get('name'),
                    prog.get('mbc2Label'),
                    step_order,
                    prog.get('cycles', 1),
                    prog.get('targetRpm'),
                    prog.get('notes')
                ))
                program_id = pcursor.lastrowid

                for s_order, step in enumerate(prog.get('steps', [])):
                    # Parse time string "MM:SS" → seconds
                    def parse_time(t):
                        if not t or t == 'Full Cool':
                            return None
                        parts = str(t).split(':')
                        return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else int(t)

                    conn.execute("""
                        INSERT INTO program_steps (program_id, step_order, volts, direction, duration_sec, cool_sec)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        program_id, s_order,
                        step.get('volts'),
                        step.get('dir', 'R'),
                        parse_time(step.get('time')),
                        parse_time(step.get('cool'))
                    ))

            imported += 1
            print(f"  Imported profile: {profile['name']}")

        conn.commit()
    return imported


def get_all_profiles() -> list:
    """Get all profiles with their program names for UI display."""
    with get_connection() as conn:
        profiles = conn.execute(
            "SELECT * FROM profiles ORDER BY name"
        ).fetchall()
        result = []
        for p in profiles:
            p = dict(p)
            programs = conn.execute("""
                SELECT program_id, name, mbc2_label, step_order, cycles, target_rpm, notes
                FROM programs WHERE profile_id = ?
                ORDER BY step_order
            """, (p['profile_id'],)).fetchall()
            p['programs'] = [dict(pr) for pr in programs]
            result.append(p)
        return result


def get_profile_with_steps(profile_id: int) -> dict:
    """Get a full profile including all programs and their steps."""
    with get_connection() as conn:
        profile = conn.execute(
            "SELECT * FROM profiles WHERE profile_id = ?", (profile_id,)
        ).fetchone()
        if not profile:
            return None
        profile = dict(profile)
        programs = conn.execute(
            "SELECT * FROM programs WHERE profile_id = ? ORDER BY step_order",
            (profile_id,)
        ).fetchall()
        profile['programs'] = []
        for prog in programs:
            prog = dict(prog)
            steps = conn.execute(
                "SELECT * FROM program_steps WHERE program_id = ? ORDER BY step_order",
                (prog['program_id'],)
            ).fetchall()
            prog['steps'] = [dict(s) for s in steps]
            profile['programs'].append(prog)
        return profile


def log_breakin_run(motor_id: int, program_ids: list, session_id: int = None, notes: str = None):
    """
    Record which programs were run on a motor during registration or a session.
    program_ids: list of program_id ints in the order they were run.
    """
    with get_connection() as conn:
        for program_id in program_ids:
            conn.execute("""
                INSERT INTO motor_breakin_log (motor_id, program_id, session_id, notes)
                VALUES (?, ?, ?, ?)
            """, (motor_id, program_id, session_id, notes))
        conn.commit()


def get_motor_breakin_history(motor_id: int) -> list:
    """Get full break-in program history for a motor."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                mbl.log_id,
                mbl.date_run,
                mbl.notes,
                pr.name     AS profile_name,
                pg.name     AS program_name,
                pg.mbc2_label,
                pg.step_order,
                mbl.session_id
            FROM motor_breakin_log mbl
            JOIN programs pg ON mbl.program_id = pg.program_id
            JOIN profiles pr ON pg.profile_id = pr.profile_id
            WHERE mbl.motor_id = ?
            ORDER BY mbl.date_run, pg.step_order
        """, (motor_id,)).fetchall()
        return [dict(r) for r in rows]
    init_db()
    print("\nMotor models loaded:")
    for m in get_all_motor_models():
        print(f"  {m['code']:8} {m['name']}")
    
    print("\nChassis loaded:")
    from itertools import groupby
    chassis = get_chassis_for_shaft_type('Single')
    print(f"  Single shaft: {', '.join(c['name'] for c in chassis)}")
    chassis = get_chassis_for_shaft_type('Dual')
    print(f"  Dual shaft:   {', '.join(c['name'] for c in chassis)}")


def get_motor_sessions(motor_id: int) -> list:
    """Get all sessions for a motor with summary stats."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                s.session_id,
                s.session_type,
                s.session_date,
                s.notes,
                mbl.program_id,
                pr.name     AS profile_name,
                pg.name     AS program_name,
                pg.mbc2_label,
                b.peak_rpm,
                b.avg_rpm,
                b.peak_temp_c,
                b.benchmark_type
            FROM sessions s
            LEFT JOIN motor_breakin_log mbl ON mbl.session_id = s.session_id
            LEFT JOIN programs pg ON mbl.program_id = pg.program_id
            LEFT JOIN profiles pr ON pg.profile_id = pr.profile_id
            LEFT JOIN benchmarks b ON b.session_id = s.session_id
            WHERE s.motor_id = ?
            ORDER BY s.session_date DESC
        """, (motor_id,)).fetchall()
        return [dict(r) for r in rows]
