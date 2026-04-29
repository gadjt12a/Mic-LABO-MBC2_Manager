# MBC2 Dashboard — Mac Setup Guide

Everything you need to get the MBC2 Dashboard running on a Mac, step by step.

---

## What you need

- A Mac running macOS 10.15 (Catalina) or later
- Google Chrome or Microsoft Edge browser
- Python 3 (instructions below if you don't have it)
- The MBC2 Dashboard folder

---

## Step 1 — Install the CH340 USB driver

The MBC2 connects via a CH340 USB chip. Macs don't include this driver by default so you need to install it once.

1. Go to: **https://www.wch-ic.com/downloads/CH341SER_MAC_ZIP.html**
2. Download the ZIP file and open it
3. Run the `.pkg` installer inside
4. When macOS asks, go to **System Settings → Privacy & Security** and click **Allow** next to the blocked driver notice
5. **Restart your Mac**

> If you're on macOS Sonoma or Ventura, the Privacy & Security step is required — the driver won't work without it.

---

## Step 2 — Check Python is installed

Open **Terminal** (search for it in Spotlight with `Cmd + Space`) and type:

```
python3 --version
```

If you see a version number (e.g. `Python 3.11.4`) you're good — skip to Step 3.

If you get an error or a prompt to install developer tools:

1. Go to **https://python.org/downloads**
2. Download the latest version for macOS and run the installer
3. Reopen Terminal and run `python3 --version` again to confirm

---

## Step 3 — Prepare the launcher to run

Two things need to happen before the launcher will work. Do both before trying to run it.

### 3a — Set execute permission (required)

Downloaded files on Mac don't have execute permission by default. Without this, the file will just display its contents as text instead of running.

1. Open **Terminal** (search for it in Spotlight with `Cmd + Space`)
2. Type `chmod +x ` (with a space after it — don't press Enter yet)
3. Open Finder and locate **`Start MBC2 Dashboard.command`** in the MBC2 Dashboard folder
4. Drag the file into the Terminal window — the full path will be filled in automatically
5. Press **Enter**

That's it — you only need to do this once.

### 3b — Allow through Gatekeeper (required on first launch)

Because the file was downloaded from the internet, macOS will warn you the first time:

1. In Finder, **right-click** `Start MBC2 Dashboard.command` and select **Open**
2. A warning will appear saying the file is from an unidentified developer — click **Open** anyway

> After the first launch, you can double-click it normally.

---

## Step 4 — Connect the MBC2

1. Plug the MBC2 into your Mac via USB
2. The MBC2 should power on
3. Wait a few seconds for macOS to recognise the device

---

## Step 5 — Open the dashboard

1. Double-click **`Start MBC2 Dashboard.command`**
2. A Terminal window opens — leave it running in the background
3. Chrome or Edge should open automatically at **http://localhost:8766**
4. If the browser doesn't open, type `http://localhost:8766` into Chrome or Edge manually

> **Important:** Use Chrome or Edge only. Safari and Firefox do not support the Web Serial API that connects to the MBC2.

---

## Step 6 — Connect to the MBC2

1. In the dashboard, click **Connect** in the top left
2. A browser popup will appear listing available serial ports
3. Look for a port with a name like:
   - `cu.usbserial-XXXXXXXX`
   - `cu.wchusbserial_XXXXXXXX`
4. Select it and click **Connect**

The dashboard will start showing live data as soon as the MBC2 begins a session.

---

## Troubleshooting

**No ports appear in the connect popup**
- Check the CH340 driver is installed and the Mac has been restarted (Step 1)
- Try a different USB cable — some cables are charge-only and have no data lines
- Unplug and replug the MBC2 then try connecting again

**Port appears but no data comes through**
- Make sure the MBC2 is powered on and running or at the menu screen
- Confirm the baud rate is 115200 (this is set automatically by the dashboard)

**Terminal window closes immediately after launching**
- Python is not installed — follow Step 2
- Try running the server manually: open Terminal, drag the folder into the Terminal window to navigate to it, then type `python3 server.py`

**Dashboard opens but shows an orange warning banner**
- You opened `mbc2-dashboard.html` directly instead of using the launcher
- Close the tab, run the launcher again, and use **http://localhost:8766**

**Port shows as `tty.` instead of `cu.`**
- Always use the `cu.` version — the `tty.` variant can cause connection issues on Mac

---

## Stopping the dashboard

Close the Terminal window that opened when you launched the dashboard. This stops the server.

You can also click **Stop Server** inside the dashboard if the button is visible.

---

## Summary — quick start checklist

- [ ] CH340 driver installed and Mac restarted
- [ ] Python 3 installed
- [ ] Execute permission set on launcher (`chmod +x`)
- [ ] Launcher allowed through Gatekeeper (right-click → Open, first time only)
- [ ] MBC2 plugged in via USB
- [ ] Dashboard opened in **Chrome or Edge** (not Safari or Firefox)
- [ ] Connected to `cu.usbserial-XXXX` or `cu.wchusbserial-XXXX` port
