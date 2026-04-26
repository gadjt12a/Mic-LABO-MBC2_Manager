-- ============================================================
-- MBC2 Motor Tracking Database Schema
-- Version: 1.0.0
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ============================================================
-- LOOKUP TABLES
-- ============================================================

-- Motor mount types
CREATE TABLE IF NOT EXISTS mount_types (
    mount_type_id   INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,   -- 'Front', 'Rear', 'Midship'
    shaft_type      TEXT NOT NULL,          -- 'Single', 'Dual'
    default_direction TEXT                  -- 'F', 'R', NULL = unconfirmed
);

INSERT INTO mount_types (name, shaft_type, default_direction) VALUES
    ('Front',    'Single', 'R'),    -- Confirmed: front mount = reverse = race direction
    ('Rear',     'Single', 'R'),    -- Confirmed: rear mount = reverse = race direction
    ('Midship',  'Dual',   'R');    -- Confirmed: midship (dual shaft) = reverse = race direction

-- Chassis lookup table
CREATE TABLE IF NOT EXISTS chassis (
    chassis_id      INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    mount_type_id   INTEGER NOT NULL REFERENCES mount_types(mount_type_id),
    notes           TEXT
);

INSERT INTO chassis (name, mount_type_id, notes) VALUES
    -- Front mount (Single shaft, Reverse) - CONFIRMED
    ('FM-A',        1, 'Modern front motor. Confirmed reverse direction.'),
    ('Super FM',    1, 'Evolution of FM chassis.'),
    ('FM',          1, 'Original front motor chassis.'),
    -- Midship (Dual shaft, R = race direction confirmed)
    ('ME',          3, 'Newest dual shaft midship chassis. R = race direction.'),
    ('MA',          3, 'Midship Aero. Dual shaft. R = race direction.'),
    ('MS',          3, 'Modular 3-piece chassis. Dual shaft. R = race direction.'),
    -- Rear mount (Single shaft, R = race direction confirmed)
    ('VZ',          2, 'Lightweight modern rear chassis. R = race direction.'),
    ('AR',          2, 'Aerodynamic Racing. Popular competitive chassis. R = race direction.'),
    ('VS',          2, 'Lightweight compact rear chassis. R = race direction.'),
    ('Super TZ-X',  2, 'Evolution of Super TZ.'),
    ('Super TZ',    2, 'Mid-length wheelbase rear chassis.'),
    ('Super XX',    2, 'Evolution of Super X.'),
    ('Super X',     2, 'Wide tread long wheelbase.'),
    ('Super-II',    2, 'Evolution of Super-1.'),
    ('Super-1',     2, 'Classic rear chassis.'),
    ('Zero',        2, 'Low centre of gravity rear chassis.'),
    ('Type 5',      2, 'Flat underside aero rear chassis.'),
    ('Type 4',      2, 'Evolution of Type 2.'),
    ('Type 3',      2, 'On-road version of Type 1.'),
    ('Type 2',      2, 'First on-road Mini 4WD chassis.'),
    ('Type 1',      2, 'Original off-road style chassis.');

-- Motor models lookup table
CREATE TABLE IF NOT EXISTS motor_models (
    model_id        INTEGER PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,   -- Full name e.g. 'Sprint Dash'
    code            TEXT NOT NULL UNIQUE,   -- Short code e.g. 'SD'
    shaft_type      TEXT NOT NULL,          -- 'Single' or 'Dual'
    speed_stars     REAL,                   -- Tamiya rating out of 4
    torque_stars    REAL,                   -- Tamiya rating out of 4
    legal_classes   TEXT,                   -- e.g. 'BMax, Advanced, Open'
    notes           TEXT
);

INSERT INTO motor_models (name, code, shaft_type, speed_stars, torque_stars, legal_classes, notes) VALUES
    ('Stock (Mabuchi)',  'STK-M', 'Single', 1.0, 1.0,  'Box Stock',               'Mabuchi variant. High speed bias.'),
    ('Stock (SMC)',      'STK-S', 'Single', 1.0, 1.0,  'Box Stock',               'SMC variant. High torque bias.'),
    ('Rev-Tuned 2',      'RT2',   'Single', 2.5, 1.0,  'Basic, Tuned, BMax, Advanced, Open', NULL),
    ('Atomic-Tuned 2',  'AT2',   'Single', 1.5, 1.5,  'Basic, Tuned, BMax, Advanced, Open', NULL),
    ('Torque-Tuned 2',  'TT2',   'Single', 1.0, 2.5,  'Basic, Tuned, BMax, Advanced, Open', NULL),
    ('Light-Dash',       'LD',    'Single', 2.5, 2.5,  'Basic, BMax, Advanced, Open', NULL),
    ('Hyper-Dash 3',     'HD3',   'Single', 3.0, 3.0,  'BMax, Advanced, Open',    NULL),
    ('Power-Dash',       'PD',    'Single', 3.0, 3.5,  'BMax, Advanced, Open',    NULL),
    ('Sprint-Dash',      'SD',    'Single', 4.0, 2.5,  'BMax, Advanced, Open',    NULL),
    ('Ultra-Dash',       'UD',    'Single', 4.0, 3.5,  'Open',                    NULL),
    ('Plasma-Dash',      'PLD',   'Single', 4.0, 4.0,  'None',                    'Exhibition/display only. Not competition legal.'),
    -- Dual shaft variants (MA/MS/ME chassis)
    ('Stock Dual Shaft', 'STK-D', 'Dual',   1.0, 1.0,  'Box Stock',               'Included with MA chassis kits.'),
    ('Rev-Tuned 2 PRO',  'RT2-P', 'Dual',   2.5, 1.0,  'Basic, Tuned, BMax, Advanced, Open', 'PRO dual shaft variant.'),
    ('Atomic-Tuned 2 PRO','AT2-P','Dual',   1.5, 1.5,  'Basic, Tuned, BMax, Advanced, Open', 'PRO dual shaft variant.'),
    ('Torque-Tuned 2 PRO','TT2-P','Dual',   1.0, 2.5,  'Basic, Tuned, BMax, Advanced, Open', 'PRO dual shaft variant.'),
    ('Light-Dash PRO',   'LD-P',  'Dual',   2.5, 2.5,  'Basic, BMax, Advanced, Open', 'PRO dual shaft variant.'),
    ('Hyper-Dash PRO',   'HD3-P', 'Dual',   3.0, 3.0,  'BMax, Advanced, Open',    'PRO dual shaft variant.'),
    ('Mach-Dash PRO',    'MD-P',  'Dual',   3.0, 3.0,  'BMax, Advanced, Open',    'PRO dual shaft variant.');

-- ============================================================
-- MOTOR REGISTRY
-- ============================================================

CREATE TABLE IF NOT EXISTS motors (
    motor_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier          TEXT NOT NULL UNIQUE,   -- e.g. 'SD-R-01'
    model_id            INTEGER NOT NULL REFERENCES motor_models(model_id),
    breakin_direction   TEXT NOT NULL CHECK(breakin_direction IN ('F', 'R')),
    date_registered     TEXT NOT NULL DEFAULT (date('now')),
    status              TEXT NOT NULL DEFAULT 'Active' 
                            CHECK(status IN ('Active', 'Retired', 'Lost', 'Damaged')),
    notes               TEXT
);

-- Tracks which chassis a motor is compatible with / intended for
-- A motor can be intended for multiple chassis
CREATE TABLE IF NOT EXISTS motor_chassis_assignments (
    assignment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    motor_id        INTEGER NOT NULL REFERENCES motors(motor_id),
    chassis_id      INTEGER NOT NULL REFERENCES chassis(chassis_id),
    UNIQUE(motor_id, chassis_id)
);

-- ============================================================
-- SESSIONS
-- ============================================================

-- A session is one MBC2 connection/run period
-- Could contain benchmark runs and/or break-in runs
CREATE TABLE IF NOT EXISTS sessions (
    session_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    motor_id        INTEGER NOT NULL REFERENCES motors(motor_id),
    session_type    TEXT NOT NULL CHECK(session_type IN ('Benchmark', 'Breakin', 'Manual')),
    session_date    TEXT NOT NULL DEFAULT (datetime('now')),
    notes           TEXT,
    ambient_temp_c  REAL    -- optional, room temp at time of session
);

-- Individual data rows captured from MBC2 serial stream
CREATE TABLE IF NOT EXISTS session_data (
    data_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id),
    timestamp_ms    INTEGER NOT NULL,   -- ms since session start
    raw_line        TEXT,               -- original CSV line from MBC2
    -- Parsed fields
    mode            TEXT,               -- MANU, PROG etc
    program_step    INTEGER,
    voltage_mv      INTEGER,            -- millivolts
    current_ma      INTEGER,            -- milliamps  
    rpm             INTEGER,
    temp_c          REAL,
    elapsed_sec     INTEGER,
    rpm_cap         INTEGER,
    -- Calculated fields
    kv_efficiency   REAL                -- RPM per volt
);

-- ============================================================
-- BENCHMARK RUNS
-- ============================================================

-- A benchmark is always: 3.0V, fixed duration, set direction
-- Linked to a session, stored separately for easy comparison
CREATE TABLE IF NOT EXISTS benchmarks (
    benchmark_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER NOT NULL REFERENCES sessions(session_id),
    motor_id            INTEGER NOT NULL REFERENCES motors(motor_id),
    benchmark_type      TEXT NOT NULL CHECK(benchmark_type IN ('Pre', 'Post', 'Periodic')),
    voltage_v           REAL NOT NULL DEFAULT 3.0,
    direction           TEXT NOT NULL CHECK(direction IN ('F', 'R')),
    duration_sec        INTEGER NOT NULL DEFAULT 120,   -- 2 min standard
    peak_rpm            INTEGER,
    avg_rpm             INTEGER,
    peak_current_ma     INTEGER,
    avg_current_ma      INTEGER,
    peak_temp_c         REAL,
    final_temp_c        REAL,
    notes               TEXT
);

-- ============================================================
-- PROGRAM LIBRARY
-- ============================================================

-- Top-level break-in profile (e.g. "Dash Motor", "Tuned Motor")
CREATE TABLE IF NOT EXISTS profiles (
    profile_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,          -- e.g. 'Dash Motor'
    motor_model     TEXT,                   -- e.g. 'Sprint-Dash'
    chassis         TEXT,                   -- e.g. 'FM-A'
    class           TEXT,                   -- e.g. 'BMax, Advanced, Open'
    notes           TEXT,
    created_date    TEXT NOT NULL DEFAULT (date('now')),
    modified_date   TEXT NOT NULL DEFAULT (date('now'))
);

-- Sub-program within a profile (e.g. DASH-A, DASH-B, DASH-C)
CREATE TABLE IF NOT EXISTS programs (
    program_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id      INTEGER NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    name            TEXT NOT NULL,          -- e.g. 'DASH-A'
    mbc2_label      TEXT,                   -- 4-char MBC2 screen label e.g. 'DSHA'
    step_order      INTEGER NOT NULL DEFAULT 0,  -- order within profile (A=0, B=1, C=2)
    cycles          INTEGER NOT NULL DEFAULT 1,
    target_rpm      INTEGER,
    notes           TEXT
);

-- Individual steps within a sub-program
CREATE TABLE IF NOT EXISTS program_steps (
    step_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id      INTEGER NOT NULL REFERENCES programs(program_id) ON DELETE CASCADE,
    step_order      INTEGER NOT NULL,
    volts           REAL NOT NULL,
    direction       TEXT NOT NULL CHECK(direction IN ('F', 'R', 'N')),  -- N = neutral/reverse for break-in
    duration_sec    INTEGER NOT NULL,       -- run time in seconds
    cool_sec        INTEGER,                -- cool time in seconds, NULL = full cool
    notes           TEXT
);

-- Links a motor record to the programs that were run on it
CREATE TABLE IF NOT EXISTS motor_breakin_log (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    motor_id        INTEGER NOT NULL REFERENCES motors(motor_id),
    program_id      INTEGER NOT NULL REFERENCES programs(program_id),
    date_run        TEXT NOT NULL DEFAULT (date('now')),
    session_id      INTEGER REFERENCES sessions(session_id),  -- optional link to session data
    notes           TEXT
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_session_data_session ON session_data(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_motor ON sessions(motor_id);
CREATE INDEX IF NOT EXISTS idx_benchmarks_motor ON benchmarks(motor_id);
CREATE INDEX IF NOT EXISTS idx_motors_model ON motors(model_id);
CREATE INDEX IF NOT EXISTS idx_programs_profile ON programs(profile_id);
CREATE INDEX IF NOT EXISTS idx_steps_program ON program_steps(program_id);
CREATE INDEX IF NOT EXISTS idx_breakin_log_motor ON motor_breakin_log(motor_id);

-- ============================================================
-- VIEWS
-- ============================================================

-- Easy motor summary view
CREATE VIEW IF NOT EXISTS v_motor_summary AS
SELECT
    m.motor_id,
    m.identifier,
    mm.name         AS model_name,
    mm.code         AS model_code,
    mm.shaft_type,
    m.breakin_direction,
    m.date_registered,
    m.status,
    COUNT(DISTINCT s.session_id)    AS total_sessions,
    COUNT(DISTINCT b.benchmark_id)  AS total_benchmarks,
    MAX(b.peak_rpm)                 AS best_peak_rpm,
    m.notes
FROM motors m
JOIN motor_models mm ON m.model_id = mm.model_id
LEFT JOIN sessions s ON m.motor_id = s.motor_id
LEFT JOIN benchmarks b ON m.motor_id = b.motor_id
GROUP BY m.motor_id;

-- Benchmark comparison view
CREATE VIEW IF NOT EXISTS v_benchmark_comparison AS
SELECT
    m.identifier,
    mm.name         AS model_name,
    b.benchmark_type,
    b.voltage_v,
    b.direction,
    b.duration_sec,
    b.peak_rpm,
    b.avg_rpm,
    b.peak_current_ma,
    b.peak_temp_c,
    b.final_temp_c,
    s.session_date
FROM benchmarks b
JOIN sessions s ON b.session_id = s.session_id
JOIN motors m ON b.motor_id = m.motor_id
JOIN motor_models mm ON m.model_id = mm.model_id
ORDER BY m.identifier, s.session_date;
