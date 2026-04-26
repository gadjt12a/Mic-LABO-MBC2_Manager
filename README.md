# MBC2 Dashboard

Data logger, program library and motor registry for the mic-LABO Motor Boot Camp 2 (MBC2) motor break-in machine.

## Features

- Live serial data logging from MBC2 via USB (Web Serial API)
- Real-time charts — RPM, Amps, kV efficiency, Temperature
- **Target RPM line** — dashed reference line on the live RPM chart from the active program's target
- Program library — create, edit and store break-in profiles and programs
- MBC2 Entry Guide — step-by-step reference for entering programs on the device
- Session recording and CSV export with notes and ambient temperature
- Firmware version checker and download links
- **Motor registry** — register, track and compare individual motors with persistent SQLite database
- **Benchmark mode** — automated 1.0→3.0V voltage ramp with per-step kV curve results panel
- **Motor comparison** — side-by-side stats table and RPM overlay for up to 5 sessions
- **Per-step cooldown timer** — sidebar shows live COOLING countdown between program steps

## Requirements

- Python 3.8 or higher
- Chrome or Edge browser (Web Serial API required — Firefox not supported)
- MBC2 connected via USB (CH340 driver may need to be installed on Windows)

## Getting Started

**Windows:** Double-click `START MBC2 DASHBOARD.bat`

**Mac:** Right-click `Start MBC2 Dashboard.command` → Open (required on first launch due to Gatekeeper)

The script starts the local server and opens the dashboard in your default browser at `http://localhost:8766`.

> If you open `mbc2-dashboard.html` directly without running the launcher, the Motor Registry and Program Library will not save — you will see an orange warning banner at the top.

## Files

```
MBC2_Dashboard/
├── mbc2-dashboard.html          ← main app (open this in Chrome/Edge)
├── server.py                    ← local API server (started by the launcher)
├── db_manager.py                ← database functions
├── motor_api.py                 ← motor registry API routes
├── schema.sql                   ← SQLite schema (applied automatically on first run)
├── mbc2.db                      ← motor registry database (created on first run)
├── default_programs.json        ← break-in profiles loaded into the library on first run
├── seed_programs.json           ← profiles seeded into the motor registry DB on first run
├── START MBC2 DASHBOARD.bat     ← Windows launcher
├── Start MBC2 Dashboard.command ← Mac launcher
├── README.md
└── CHANGELOG.md
```

## Motor Registry

The Motors tab lets you register and track individual motors across their entire life cycle.

### Registering a motor

1. Select the motor model (Single shaft or PRO dual shaft)
2. Select break-in direction (Reverse or Forward — PRO motors are Forward only)
3. Tag the target chassis (optional — filters available chassis by shaft type)
4. Link the break-in profile and sub-programs run (optional)
5. Select pre-treatment applied (water, IPA, ChemZ No8, light oil, etc.)
6. Add any additional notes
7. Click **Register motor** — identifier is auto-generated and displayed

### Motor identifier format

`MODEL-DIRECTION-NUMBER` — e.g. `SD-R-01`, `PD-R-02`, `HD3-P-F-01`

Print on 12mm label tape, cut to 5mm, stick on motor end bell.

### Motor detail and comparison

Click any motor in the registry to open its detail panel showing benchmark history and session list. Use the **Compare** button on any session to add it to a side-by-side comparison. Up to 5 sessions can be compared at once across different motors.

### Chassis direction reference

All Tamiya Mini 4WD chassis run the motor in **Reverse (R)** on the MBC2 as the race direction. This is confirmed across Front, Rear, and Midship mount types.

| Mount | Chassis | Break-in direction |
|-------|---------|-------------------|
| Front | FM-A, Super FM, FM | **R (Reverse)** — confirmed |
| Rear | VZ, AR, VS, Super TZ-X, Super TZ, Super XX, Super X, Super-II, Super-1, Zero, Type 1–5 | **R (Reverse)** — confirmed |
| Midship (dual shaft) | ME, MA, MS | **R (Reverse)** — confirmed |

**Why R on all chassis:** The MBC2 treats the right contact as Positive and spins Normal to the right. All Tamiya Mini 4WD chassis mount the motor with the opposite polarity orientation to the MBC2 — so MBC2 Reverse drives the motor in the race direction regardless of chassis type.

## Program Library

Click **☰ Programs** in the header to open the program library drawer.

Pre-populated with:
- **Baseline** — standard 5-step 1.0→3.0V benchmark ramp
- **Stock Motor** — 3-cycle brush seating for kit standard motors
- **Torque Tuned 2** — 3-stage break-in (A: seating, B: wake up, C: polish)
- **Hyper Dash** — 3-stage break-in for high-RPM dash motors

Each profile contains one or more named programs (e.g. TT2-A, TT2-B, TT2-C). Select the active program in the right panel — the **MBC2 Entry Guide** shows the exact values to enter on the device screen.

Voltage steps are validated on save — values above 4.5V will show a warning (5V hard maximum).

## Benchmark Mode

Select **── Baseline ──** from the program dropdown and click **● Start Session**. The MBC2 must be running the matching BASELINE program. The dashboard runs a 3-minute automated ramp (1.0V → 3.0V in 5 steps) and displays a results panel with:

- Peak RPM and average RPM/W
- Average current at 3.0V
- Efficiency rating (A / B / C / D)
- Per-step kV table

## Session Notes

Before stopping a session, fill in the **Notes** field (lube used, track surface, conditions) and **Ambient °C** in the Sessions sidebar. Both are saved with the session and shown on the session chip. The ambient temp field is retained between sessions since it stays valid across multiple motors at the same bench location.

## MBC2 Direction Reference

- **R** (Reverse on MBC2 display) = race direction for **all** Tamiya Mini 4WD chassis
- **N** (Normal on MBC2 display) = opposite of race direction for all chassis

The MBC2 mounts the motor with right contact = Positive. All Tamiya chassis mount the motor with opposite polarity, so MBC2 Reverse always corresponds to forward/race direction in the car.

## Serial Column Mapping (confirmed)

| Col | Field | Notes |
|-----|-------|-------|
| 1 | progName | program name or MANU |
| 3 | cycle | current cycle number |
| 4 | maxCycle | total cycles in program |
| 5 | step | current step (1–5) |
| 7 | rpm | current RPM |
| 8 | maxRpm | MBC2 internal peak |
| 11 | dutyRaw | duty/1000 = volts |
| 12 | dirCode | 0=none, 1=N, 2=R, 3=NP, 4=RP |
| 13 | amps_raw | /1000 = amps |
| 14 | counter | countdown (/100 = seconds remaining) |
| 18 | temperature | °C (−273 = sensor disconnected) |

## Hardware

- ESP32-WROOM-32, 240MHz, 4MB flash
- INA226 current sensor
- CH340 USB-serial at 115200 baud
- Latest firmware: v0.105 — download via the firmware panel or upload at `http://[MBC2-IP]/u`
