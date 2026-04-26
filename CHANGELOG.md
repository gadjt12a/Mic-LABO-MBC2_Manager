# Changelog

All notable changes to MBC2 Dashboard are documented here.

---

## [0.4.0] — 2026-04-26

### Added

- **Target RPM line on live chart** — when a program with a target RPM is selected, a yellow dashed TARGET line is drawn on the RPM chart. Y-axis scales to include it so it is always visible. Updates across live recording, session replay, tab switching, and window resize.
- **kV curve in benchmark results** — benchmark results now display a panel below the benchmark banner showing peak RPM, avg RPM/W, avg current at 3V, efficiency rating (A–D), and a per-step kV table (1.0V → 3.0V). Previously only shown in DevTools console.
- **Motor comparison side-by-side** — select sessions from any motor's detail view using the Compare button. A comparison panel appears showing a stats table (peak RPM, avg RPM, peak/avg kV, peak/avg amps, peak temp) with colour-coded columns per motor, a best-in-comparison ★ marker, and RPM bar indicators. The RPM chart tab shows a multi-session overlay in parallel. Clear button resets all selections.
- **Session notes and ambient temperature** — two new fields in the sessions sidebar: a text field for notes (lube used, track conditions, etc.) and an ambient temperature field in °C. Both are saved with the session, shown as a subtitle on the session chip, and sent to the API.
- **Per-step cooldown timer in sidebar** — when the MBC2 stream shows direction — and RPM = 0 while a program is active, the sidebar TIME LEFT row is replaced with a cyan COOLING countdown. Switches back automatically when the next step starts.
- **Pre-treatment structured dropdown** — the freetext pre-treatment notes field is replaced with a structured dropdown (None/dry, Water, IPA, Alcohol, ChemZ No8 multilube, Light oil, Motor spray, Other) plus a separate additional notes textarea. Selected treatment is sent as `pre_treatment` in the motor registration payload.

### Fixed

- **BUG-01** — PRO motor direction lock now has a hard guard inside `mrSelectDir()` with a toast message. Previously only a UI-level disabled button — could be bypassed.
- **BUG-02** — `resolveSelectedProgramDbId()` now correctly matches the selected program against DB profiles by name and MBC2 label. Previously always returned the first program in the database regardless of selection.
- **BUG-03** — Removed duplicate `voltage_v` key from benchmark session finalise payload. JS silently dropped the first value — latent bug.
- **BUG-04** — `populateProgramDropdownForMotor()` now re-syncs benchmark type dropdown visibility after rebuilding the `<select>` element. Previously the benchmark type row could stay visible when switching to a non-baseline program via a motor change.
- **BUG-05** — `setMotorFromRoster()` now properly updates `#activeMotorSelect`, `#activeMotorId`, and `#activeMotorName` in the sidebar. Previously tried to update a non-existent DOM element, leaving the sidebar desynced.
- **BUG-07** — Session chips now use `data-session-key` attributes and `addEventListener` instead of inline `onclick` string interpolation. Session names containing apostrophes no longer cause JS syntax errors.
- **BUG-08** — `sortRoster()` now applies the `sort-asc`/`sort-desc` class to the correct column header using `th.dataset.col`. Previously cleared all classes but never re-applied them.
- **BUG-09** — CSV filename sanitiser now allows dots so version numbers (e.g. `v1.2`) are preserved in exported filenames.
- **BUG-10** — Benchmark kV curve per step is now displayed in the UI result panel. Previously only written to `console.table()`.
- **BUG-11** — Local variable in `addRawLine()` renamed from `console` to `rawConsoleEl` — no longer shadows the global `console` object.
- **BUG-12** — `mrShowMotorDetail()` now checks both `registeredMotors` and `MR.motors` as fallback. Motors registered during a session now appear correctly in the detail view without requiring a page reload.

### Data

- **seed_programs.json** — removed MiniMod Garage reference profiles (`tuned-ref-001`, `dash-ref-001`). Removed unused `class` field from all profiles.
- **default_programs.json** — removed MiniMod Garage reference profiles (`tuned-ref-001`, `dash-ref-001`). Removed unused `class` field from all profiles.

---

## [0.3.0] — 2026-04-24

### Architecture

- SQLite motor registry database (`mbc2.db`) — persistent across sessions
- `db/` folder — `schema.sql`, `db_manager.py`, `motor_api.py`
- `data/seed_programs.json` — seeds break-in profiles into DB on first run
- `server.py` updated — motor registry API integrated alongside existing program/session API
- Motor registry JS and CSS merged into `mbc2-dashboard.html`

### Added

- **Motors tab** — new tab alongside Charts and Raw Data
- **Motor registration** — register motors with auto-generated identifier labels (e.g. `SD-R-01`)
- **Motor model selector** — full Tamiya motor lineup, collapsible Single shaft / PRO dual shaft sections
- **Break-in direction** — Forward / Reverse, dual shaft motors constrained correctly
- **Chassis assignment** — tag which chassis a motor is intended for, filtered by shaft type
- **Break-in program linking** — select profile from saved program library, then select which sub-programs were run in order with sequence display
- **Pre-treatment notes** — freeform field for water treatment, lube etc.
- **Motor identifier preview** — shows auto-generated label before committing
- **Motor registry view** — lists all registered motors with session count and best peak RPM
- **Motor naming standard** — `MODEL-DIRECTION-NUMBER` e.g. `SD-R-01`, sequential per model

### API routes added to server.py

| Method | Route | Description |
|--------|-------|-------------|
| GET | /api/motors | List active motors |
| GET | /api/motors/all | List all motors |
| GET | /api/motors/`<id>` | Motor detail + break-in history |
| POST | /api/motors/register | Register new motor |
| POST | /api/motors/`<id>`/status | Update motor status |
| GET | /api/profiles | List break-in profiles with sub-programs |
| GET | /api/profiles/`<id>` | Profile with full step detail |
| POST | /api/profiles/import | Import programs JSON into DB |

### Database schema

- `mount_types` — Front / Rear / Midship with shaft type and direction
- `chassis` — all 21 Tamiya chassis mapped to mount type
- `motor_models` — all 18 Tamiya motors with speed/torque ratings
- `motors` — registered motor records with auto-generated identifiers
- `motor_chassis_assignments` — motor to chassis links
- `profiles` — top-level break-in profiles (Stock Motor, Tuned Motor, Dash Motor)
- `programs` — sub-programs within profiles (DASH-A, DASH-B, DASH-C)
- `program_steps` — individual steps with volts, direction, duration, cool time
- `motor_breakin_log` — links motors to programs run on them
- `sessions` — MBC2 session records
- `session_data` — raw parsed MBC2 CSV rows
- `benchmarks` — pre/post benchmark run summaries

### Notes

- Rear mount and Midship chassis direction flagged as TBD — confirm by testing motors on actual chassis

---

## [0.2.0] — 2026-04-23

### Architecture

- Moved to server-based architecture matching Race Tournament App pattern
- `server.py` — Python local server on port 8766
- `data/programs.json` — program library with JSON persistence
- `data/sessions/` — saved session CSVs
- `src/data/default_programs.json` — pre-populated default profiles
- Windows `.bat` launcher and Mac `.command` launcher
- Program library persists to server API with localStorage fallback

### Added

- **Program Library drawer** — slides in from right, full CRUD for profiles and programs
- **Motor profiles** — named profiles (Stock, TT2, Dash) each containing multiple programs
- **Program editor** — edit name, MBC2 label, cycle count, target RPM, all 5 steps, notes
- **MBC2 Entry Guide** — modal showing exact values to enter on MBC2 screen, per program
- **Active program selector** — dropdown in right panel, persists between sessions
- **Active program badge** — shown in control bar, click to open library
- Pre-populated defaults: Stock (Box), Torque Tuned 2 (Evo), Hyper Dash (Pro)
- Export/Import program library as JSON
- Firmware panel — fetches versions.csv from esp32.miclabo.xyz, lists versions with download links
- Firmware falls back to hardcoded list if server unreachable

### Fixed

- Temperature display shows `--` when external sensor disconnected (-273°C)
- RPM source corrected to col[7] (confirmed live RPM)
- Max RPM from col[8] — MBC2's own internal peak latch
- Voltage from duty/1000 (confirmed: 2000 = 2.0V)
- Amps ×10 to match MBC2 display scaling

### Notes

- Manual Run panel hidden — pending serial command interface from mic-LABO
- Contact sent to mic-LABO (id100082@gmail.com) re serial command interface
- MBC2 firmware dump confirmed: serial is output-only, no command interface exists in v0.105

---

## [0.1.2] — 2026-04-23

### Added
- Firmware panel with version list and download links
- Manual Run panel (hidden — serial output-only)

### Fixed
- Temperature -273°C now shows as `--`

---

## [0.1.1] — 2026-04-23

### Fixed
- RPM col[7], voltage duty/1000, amps ×10 scaling

---

## [0.1.0] — 2026-04-23

### Initial release
- Web Serial API connection
- Live RPM, Amps, Voltage, kV, Temperature charts
- Session recording and CSV save/load
- Program panel with step indicators
