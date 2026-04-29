# MBC2 Dashboard — Windows Setup Guide

Everything you need to get the MBC2 Dashboard running on Windows, step by step.

---

## What you need

- Windows 10 or Windows 11
- Google Chrome or Microsoft Edge browser
- Python 3 (instructions below if you don't have it)
- The MBC2 Dashboard folder

---

## Step 1 — Install the CH340 USB driver

The MBC2 connects via a CH340 USB chip. Most Windows 10/11 machines will install this driver automatically when you plug the MBC2 in. If they don't, install it manually.

**Not sure which CPU you have?** Go to **Settings → System → About** and check the **System type** or **Processor** field. Surface Pro X, Surface Pro 9/10 (SQ series), and Snapdragon-based laptops are ARM. Most other PCs are Intel/AMD.

### Intel / AMD (x86/x64)

1. Go to: **https://www.wch-ic.com/downloads/CH341SER_EXE.html**
2. Download and run the `.exe` installer
3. Click **Install**
4. Restart your PC

### ARM (Surface Pro X, Snapdragon laptops, etc.)

The `.exe` installer does not work on ARM — you need to install the `.dll` manually:

1. Go to: **https://www.wch-ic.com/downloads/CH341SER_ZIP.html**
2. Download and extract the ZIP file
3. Inside the extracted folder, find **`CH341SER.DLL`**
4. **Right-click** the `.dll` file and select **Install**
5. Restart your PC

> To check if the driver is already installed: plug in the MBC2, open **Device Manager** (search for it in the Start menu) and look under **Ports (COM & LPT)**. You should see something like `USB-SERIAL CH340 (COM3)`. If it shows a yellow warning icon, the driver needs installing.

---

## Step 2 — Check Python is installed

Open **Command Prompt** (search for `cmd` in the Start menu) and type:

```
python --version
```

If you see a version number (e.g. `Python 3.11.4`) you're good — skip to Step 3.

If you get an error:

1. Go to **https://python.org/downloads**
2. Download the latest version for Windows and run the installer
3. **Important:** On the first screen of the installer, tick **"Add Python to PATH"** before clicking Install
4. Reopen Command Prompt and run `python --version` again to confirm

> If you skip the "Add to PATH" step, the launcher won't be able to find Python and will show an error.

---

## Step 3 — Allow the launcher to run

Because the launcher was downloaded from the internet, Windows SmartScreen may block it the first time.

1. In File Explorer, locate **`START MBC2 DASHBOARD.bat`** in the MBC2 Dashboard folder
2. Double-click it
3. If a blue SmartScreen warning appears saying "Windows protected your PC", click **More info** then **Run anyway**
4. A Command Prompt window will open and the server will start

> After the first time it runs without the warning.

---

## Step 4 — Connect the MBC2

1. Plug the MBC2 into your PC via USB
2. The MBC2 should power on
3. Wait a few seconds for Windows to recognise the device
4. Check Device Manager if you want to confirm the COM port number (e.g. COM3, COM4)

---

## Step 5 — Open the dashboard

1. Double-click **`START MBC2 DASHBOARD.bat`**
2. A Command Prompt window opens — leave it running in the background
3. Chrome or Edge should open automatically at **http://localhost:8766**
4. If the browser doesn't open, type `http://localhost:8766` into Chrome or Edge manually

> **Important:** Use Chrome or Edge only. Firefox does not support the Web Serial API that connects to the MBC2.

---

## Step 6 — Connect to the MBC2

1. In the dashboard, click **Connect** in the top left
2. A browser popup will appear listing available serial ports
3. Look for a port with a name like:
   - `USB-SERIAL CH340 (COM3)`
   - `USB-SERIAL CH340 (COM4)`
   - The COM number may vary — if you have multiple, check Device Manager to confirm which one is the MBC2
4. Select it and click **Connect**

The dashboard will start showing live data as soon as the MBC2 begins a session.

---

## Troubleshooting

**No ports appear in the connect popup**
- Check the CH340 driver is installed (Step 1) — look in Device Manager under Ports
- Try a different USB cable — some cables are charge-only and have no data lines
- Unplug and replug the MBC2 then try connecting again
- If the port shows a yellow warning icon in Device Manager, reinstall the driver

**Port appears but no data comes through**
- Make sure the MBC2 is powered on and running or at the menu screen
- Confirm the baud rate is 115200 (set automatically by the dashboard)

**Command Prompt window closes immediately after launching**
- Python is not installed or not added to PATH — follow Step 2 carefully
- Try running the server manually: open Command Prompt, navigate to the MBC2 Dashboard folder using `cd` (e.g. `cd C:\Users\YourName\Downloads\MBC2_Dashboard`) then type `python server.py`

**Dashboard opens but shows an orange warning banner**
- You opened `mbc2-dashboard.html` directly instead of using the launcher
- Close the tab, run the launcher again, and use **http://localhost:8766**

**SmartScreen blocks the launcher every time**
- Right-click `START MBC2 DASHBOARD.bat` → Properties → tick **Unblock** at the bottom → OK

**Port disappears after a while**
- The MBC2 may have gone to sleep or disconnected — unplug and replug, then reconnect in the dashboard

---

## Stopping the dashboard

Close the Command Prompt window that opened when you launched the dashboard. This stops the server.

You can also click **Stop Server** inside the dashboard if the button is visible.

---

## Summary — quick start checklist

- [ ] CH340 driver installed (check Device Manager — should show under Ports with no warning icon)
- [ ] Python 3 installed with **Add to PATH** ticked
- [ ] SmartScreen bypassed on first launch (More info → Run anyway)
- [ ] MBC2 plugged in via USB
- [ ] Dashboard opened in **Chrome or Edge** (not Firefox)
- [ ] Connected to `USB-SERIAL CH340 (COMX)` port
