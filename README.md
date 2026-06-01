<p align="center">
  <img src="assets/icon.png" alt="DualCPY-Linux Logo" width="250">
</p>

# DualCPY-Linux

> **This is a Linux fork of [DualCPY](https://github.com/theswest/ThorCPY) (formerly ThorCPY) by [the_swest](https://github.com/theswest).
> All credit for the original project goes to [theswest](https://github.com/theswest).
> For the Windows version, see the [upstream repository](https://github.com/theswest/ThorCPY).**

**DualCPY-Linux** is a Linux-optimised fork of [DualCPY](https://github.com/theswest/ThorCPY) (formerly ThorCPY) — a multi-window Scrcpy launcher for dual-screen Android handhelds such as the **AYN Thor**.

It launches two scrcpy windows (one per display), supports window docking on X11, and provides wireless ADB connection support.
Designed for screensharing, recording or livestreaming.

| Main UI                             | DualCPY-Linux Screenshot                             |
|-------------------------------------|------------------------------------------------|
| ![](assets/screenshots/main_ui.png) | ![](assets/screenshots/DualCPY-Linux-Screenshot.png) |

---

## Features

- **customtkinter control panel** — native, dark-themed UI with layout sliders,
  presets, FPS selector and a restart button
- **Multi-device support** — automatic ADB device detection with built-in
  profiles (AYN Thor, RG DS, Pocket DS, Odin 3/2/2 Portal/2 Mini + RDS, Retroid
  Pocket 6/G2/5/4 Pro + RDS). Per-device screen ratios are computed on boot
- **Custom device profiles** — in-app profile editor, device selector on launch,
  and a remembered "last used profile" per device
- **X11 Docking** — embed both scrcpy windows into a single container window
- **Wayland Support** — floating window mode (docking not possible on pure Wayland)
- **Wireless ADB Connection** — customtkinter dialog with Quick Connect and
  Android 11+ pairing, plus a network scanner that auto-discovers devices
- **File Transfer window** — two-panel device ↔ local PC transfers with file-type
  icons, quick-nav pills, automatic SD-card detection and inline image previews
- **Gamepad passthrough** — controller forwarded to the device on the top screen
- **Layout presets**, **screenshot capture** (`mss` → PNG), real-time **scale
  control**, **swap screens**, and a **configurable FPS cap**
- **Tuned scrcpy launch** — low-latency H.264 codec options for smooth, responsive
  mirroring; vsync disabled to avoid frame drops on high-refresh monitors

Technical features:
- Automatic `adb`/`scrcpy` installation via package manager (pacman / apt)
- Profile-driven geometry; thread-safe (queue-marshalled) Tk UI updates
- Graceful error handling and shutdown
- Comprehensive logging with daily rotation

---

## Requirements

### System
- **OS**: Linux with X11 (recommended) or Wayland (floating mode via XWayland)
- **Python**: 3.9+ (tested on 3.14)
- **Device**: a supported dual-screen Android handheld (e.g. AYN Thor) with USB Debugging enabled

### System Dependencies

Install `git`, `adb`, `scrcpy` (≥ 4.0) and the X11 dev headers from your distro;
the Python UI packages are installed via `pip` (see **Python Dependencies**).

#### Arch Linux / Manjaro / CachyOS

```bash
sudo pacman -S git base-devel android-tools scrcpy python-xlib
```

> `base-devel` (includes `gcc`) is only needed if you intend to build a standalone executable.

#### Debian / Ubuntu

```bash
sudo apt install git adb python3-dev python3-xlib build-essential
```

`scrcpy` may not be in the default `stable` repo. Enable backports first:

```bash
# Enable backports (Debian stable only — skip if already enabled or on Ubuntu)
echo "deb http://deb.debian.org/debian $(lsb_release -cs)-backports main" \
  | sudo tee /etc/apt/sources.list.d/backports.list
sudo apt update
sudo apt install -t $(lsb_release -cs)-backports scrcpy
```

> On Ubuntu `scrcpy` is available in the universe repository. Just run:
> ```bash
> sudo apt install scrcpy
> ```

### Python Dependencies

#### All distros (venv recommended)

The customtkinter UI needs a few Python packages that are not always available
in distro repos, so install them into a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Always activate the venv (`source venv/bin/activate`) before running
> `python main.py` or `python build.py` in subsequent sessions.

`requirements.txt` installs:
- `customtkinter>=5.2.2` — control panel / dialog UI
- `pillow>=10.0.0` — icons and image previews
- `mss>=9.0.0` — cross-platform screenshots
- `darkdetect>=0.8.0` — appearance-mode detection (customtkinter dependency)
- `python-xlib>=0.33` — X11 window management (Linux only)
- `pyinstaller>=6.0.0` — only needed to build a standalone executable

> DualCPY-Linux can also attempt to install `adb` and `scrcpy` automatically on first launch
> if they are missing (via `pkexec`).

---

## Enable USB Debugging

Before connecting your AYN Thor:

1. On the device go to **Settings > About device**
2. Tap **Build number** seven times to enable Developer Options
3. Go to **Settings > System > Developer Options**
4. Enable **USB Debugging**

---

## Installation

### Option 1: Run from Source (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/DrSkyfaR/ThorCPY-Linux.git
cd ThorCPY-Linux

# 2. Install system dependencies (see Requirements above)
```

**Arch Linux** — deps are already installed via `pacman`, run directly:

```bash
python3 main.py
```

**Debian / Ubuntu / Other distros** — set up a venv first:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

> On subsequent runs, re-activate the venv before launching:
> ```bash
> source .venv/bin/activate && python3 main.py
> ```

### Option 2: Build a Standalone Executable

```bash
# Arch — activate a venv that has pyinstaller
python -m venv .venv && source .venv/bin/activate
pip install pyinstaller

# Debian/Ubuntu — activate the venv created above
source .venv/bin/activate

# Run the build script
python build.py

# Find your binary in dist/DualCPY
# The executable must be placed in a folder containing: bin/, config/, logs/
```

---

## Connecting Your Device

### Via USB (Automatic)
Connect your AYN Thor via USB with USB Debugging enabled. DualCPY-Linux detects the device automatically on startup.

### Via WiFi (Wireless ADB)

Click the **CONNECT** button in the control panel to open the wireless connection dialog.
The button turns **green** when a wireless connection is active.

#### First-time Pairing (Android 11+)

1. On the device: **Developer Options > Wireless debugging > Pair device with pairing code**
2. Note the IP address, pairing port, and 6-digit code shown
3. In DualCPY-Linux, click **CONNECT** → switch to the **First Time Pairing** tab
4. Enter the IP address, pairing port, and 6-digit code, then click **Pair**
5. After pairing, switch to **Quick Connect**, enter the IP with port `5555`, then click **Connect**

#### Subsequent Connections

1. Enable **Wireless debugging** in Developer Options
2. Click **CONNECT** in DualCPY-Linux → **Quick Connect** tab
3. Enter the device IP and port `5555`, click **Connect**

#### Legacy TCP/IP Mode (Android 10 and below)

1. Connect via USB first
2. Run: `adb tcpip 5555`
3. Disconnect USB, then use **Quick Connect** in DualCPY-Linux

---

## Usage

The DualCPY-Linux control panel appears on the right side of your screen:

| Control | Description |
|--------|-------------|
| **Global Scale** | Adjust resolution scale of scrcpy output (requires restart) |
| **Top X / Top Y** | Move top screen position |
| **Bottom X / Bottom Y** | Move bottom screen position |
| **CONNECT** | Open the wireless connection dialog (green when connected wirelessly) |
| **DOCK WINDOWS** | Embed both windows into a single container (X11 only) |
| **UNDOCK WINDOWS** | Separate into independent floating windows |
| **SCREENSHOT** | Capture the docked view to a PNG in `screenshots/` |
| **SAVE** | Save current layout as a named preset |
| **LOAD** | Apply a saved preset |
| **DEL** | Delete a saved preset |

---

## Configuration

### Layout Presets — `config/layout.json`

```json
{
    "Default": {
        "tx": 0,
        "ty": 0,
        "bx": 251,
        "by": 648,
        "global_scale": 0.6
    },
    "Streaming": {
        "tx": 100,
        "ty": 50,
        "bx": 300,
        "by": 700,
        "global_scale": 0.3
    }
}
```

### General Config — `config/config.json`

```json
{
    "global_scale": 0.6,
    "tx": 0,
    "ty": 0,
    "bx": 251,
    "by": 648,
    "layout_mode": "DUAL",
    "swap_screens": false,
    "wireless_connect_ip": "192.168.1.100",
    "wireless_connect_port": "5555"
}
```

### Logging

Logs are saved to `logs/` with daily rotation:

| File | Content |
|------|---------|
| `thorcpy_YYYYMMDD.log` | Main application log |
| `scrcpy_top_YYYYMMDD_HHMMSS.log` | Top window scrcpy output |
| `scrcpy_bottom_YYYYMMDD_HHMMSS.log` | Bottom window scrcpy output |

To increase verbosity, change `logging.INFO` to `logging.DEBUG` in `main.py`.

---

## Troubleshooting

### Device Not Found
- Ensure USB Debugging is enabled
- Try a different USB cable (data cable, not charge-only)
- Revoke USB debugging authorizations and reconnect:
  **Settings > System > Developer Options > Revoke USB debugging authorizations**
- Check if ADB sees the device: `adb devices`
- Restart ADB server: `adb kill-server && adb start-server`

### Scrcpy Not Starting
- Confirm scrcpy is installed: `which scrcpy`
- Try running manually: `scrcpy -s YOUR_DEVICE_SERIAL --display-id=0`
- Check logs in `logs/` for error details
- Ensure your device has display IDs `0` and `4`

### Windows Won't Dock (X11)
- Confirm you are running under **X11**, not Wayland: `echo $XDG_SESSION_TYPE`
- Wait a few seconds for scrcpy to fully initialise
- Toggle Dock / Undock several times
- Restart DualCPY-Linux

### Running on Wayland
- Docking is **not supported** on Wayland (no window reparenting)
- Windows will open as independent floating windows — this is expected behaviour
- To use X11, start your session with an X11 display server or use `XWayland`

### Wireless Connection Fails
- Ensure both PC and device are on the same WiFi network
- Disable any firewall rules blocking port 5555
- For Android 11+, use the **First Time Pairing** flow before attempting Quick Connect
- Check that **Wireless debugging** is enabled on the device (not just USB debugging)

### Performance / Stuttering
- Over WiFi: DualCPY-Linux automatically uses 120 FPS (top) / 60 FPS (bottom)
- Reduce **Global Scale** in the UI to lower resolution and bandwidth
- Use a USB 3.0 port when connecting via cable for best performance
- Close other resource-intensive applications
- To manually adjust FPS limits, edit `DEFAULT_MAX_FPS` in `src/scrcpy_manager.py`

### Layout Issues
- Delete `config/layout.json` and `config/config.json` to reset to defaults
- Reload at 0.6 scale, adjust, and save

### Running in a Distrobox Container (Bazzite / Immutable Systems)

DualCPY-Linux can run inside a [Distrobox](https://distrobox.it/) container on immutable systems like Bazzite.

**Arch container** (`ghcr.io/ublue-os/bazzite-arch`):
```bash
sudo pacman -S git base-devel android-tools scrcpy python-xlib
git clone https://github.com/DrSkyfaR/ThorCPY-Linux.git && cd ThorCPY-Linux
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

**Debian container** (`docker.io/library/debian:stable-slim` or similar):
```bash
sudo apt update
sudo apt install git curl lsb-release python3 python3-venv python3-dev \
     python3-xlib build-essential android-tools-adb
# Enable backports for scrcpy
echo "deb http://deb.debian.org/debian $(lsb_release -cs)-backports main" \
  | sudo tee /etc/apt/sources.list.d/backports.list
sudo apt update && sudo apt install -t $(lsb_release -cs)-backports scrcpy
git clone https://github.com/DrSkyfaR/ThorCPY-Linux.git && cd ThorCPY-Linux
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

> Make sure the container has access to the host display (`DISPLAY`/`WAYLAND_DISPLAY`)
> and that `adb` on the host (or inside the container) can see your USB device.

---

## Project Structure

```
DualCPY-Linux/
├── main.py                     # Entry point
├── build.py                    # PyInstaller build script
├── requirements.txt            # Python dependencies
├── assets/                     # Logo, fonts, file-browser icons, screenshots
├── bin/                        # Local adb/scrcpy binaries (optional)
├── config/                     # Runtime configuration (auto-created)
├── logs/                       # Log files (auto-created)
└── src/
    ├── launcher.py             # Main controller: docking, layout, wireless, tick loop
    ├── scrcpy_manager.py       # scrcpy process management, profiles & ADB
    ├── control_panel.py        # customtkinter control panel UI
    ├── wireless_dialog.py      # customtkinter wireless connection dialog
    ├── file_transfer_dialog.py # device ↔ local PC file transfer window
    ├── device_profile.py       # DeviceProfile dataclass + built-in profiles
    ├── custom_profile_store.py # user-defined profile persistence
    ├── device_detection.py     # ADB device/display detection
    ├── device_selector.py      # profile auto-match on launch
    ├── device_profile_dialog.py / device_profile_editor.py  # profile UI
    ├── ui_constants.py         # shared colours, fonts, icon loader
    ├── platform_compat.py      # Linux shims (dark titlebar, clipboard, mss)
    ├── presets.py              # layout preset store
    ├── config.py               # config manager
    ├── win32_dock.py / win32_darkmode.py   # Windows-only docking/titlebar
    └── docking/
        ├── x11.py              # X11 window docking (Linux)
        └── stateless.py        # Wayland / no-op dock manager
```

---

## Bundled Software

DualCPY-Linux can use locally bundled binaries from the `bin/` folder.
On Linux, **system-installed packages are preferred** — the `bin/` folder is optional.

- **scrcpy** by Genymobile/Romain Vimont — Apache License 2.0
  Source: https://github.com/Genymobile/scrcpy

---

## Licenses

- This project is licensed under **GNU General Public License v3.0** — see `LICENSE`
- [scrcpy](https://github.com/Genymobile/scrcpy) — Apache License 2.0
- [Cal Sans](https://github.com/calcom/font) font — SIL Open Font License 1.1 (see `assets/fonts/OFL.txt`)

---

## Contributing

Contributions are welcome! This is a Linux-specific fork maintained separately.

- For Linux-specific bugs or features: open an issue in **this repository** on [GitHub](https://github.com/DrSkyfaR/ThorCPY-Linux/issues)
- For general ThorCPY issues (Windows / upstream): see the [upstream repository](https://github.com/theswest/ThorCPY/issues)

---

## Acknowledgements

- **[the_swest](https://github.com/theswest)** — Original DualCPY (ThorCPY) author
- **[eldermonkey](https://github.com/eldermonkey)** — Project logo
- **[scrcpy](https://github.com/Genymobile/scrcpy)** by Romain Vimont — the backend that makes this all possible
- **[Cal Sans](https://github.com/calcom/font)** by Cal.com Inc. — UI typography
- **[customtkinter](https://github.com/TomSchimansky/CustomTkinter)** — UI toolkit
