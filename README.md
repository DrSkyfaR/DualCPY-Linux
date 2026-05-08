<p align="center">
  <img src="assets/icon.png" alt="ThorCPY Logo" width="250">
</p>

# ThorCPY Linux

> **This is a Linux fork of [ThorCPY](https://github.com/theswest/ThorCPY) by [the_swest](https://github.com/theswest).
> All credit for the original project goes to [theswest](https://github.com/theswest).
> For the Windows version, see the [upstream repository](https://github.com/theswest/ThorCPY).**

**ThorCPY Linux** is a Linux-optimised fork of [ThorCPY](https://github.com/theswest/ThorCPY) — a multi-window Scrcpy launcher designed for the **AYN Thor** handheld.

It launches two scrcpy windows (one per display), supports window docking on X11, and provides wireless ADB connection support.
Designed for screensharing, recording or livestreaming.

| Main UI                             | ThorCPY Screenshot                             |
|-------------------------------------|------------------------------------------------|
| ![](assets/screenshots/main_ui.png) | ![](assets/screenshots/ThorCPY-Screenshot.png) |

---

## Features

- **Dual-screen support** built for the AYN Thor (Display 0 + Display 4)
- **X11 Docking** — embed both scrcpy windows into a single container window
- **Wayland Support** — floating window mode (docking not possible on Wayland)
- **Wireless ADB Connection** — native in-app overlay, no separate window (Android 11+ pairing supported)
- **Network Scanner** — auto-discover Android devices on your local network
- **Layout Presets** — save and restore screen positions
- **Screenshot capture** — capture both screens into one image
- **Scale control** — adjust scrcpy output resolution in real time
- **Swap screens** — flip which display is top/bottom
- **Per-display FPS** — top display runs at 120 FPS, bottom at 60 FPS
- **Wireless optimisation** — automatically reduces FPS and applies settings when connected over WiFi

Technical features:
- Automatic `adb`/`scrcpy` installation via package manager (pacman / apt)
- Thread-safe window management
- Graceful error handling and shutdown
- Comprehensive logging with daily rotation

---

## Requirements

### System
- **OS**: Linux with X11 (recommended) or Wayland (floating mode)
- **Python**: 3.8–3.13 (3.14 not yet supported — pygame has no wheel for it)
- **Device**: AYN Thor with USB Debugging enabled

### System Dependencies

#### Arch Linux / Manjaro / CachyOS

```bash
sudo pacman -S git base-devel android-tools scrcpy python-pygame python-xlib
```

> `python-pygame` and `python-xlib` are installed here from the official repos.
> **Skip the `pip install -r requirements.txt` step** — all runtime dependencies are already present.
> `base-devel` (includes `gcc`) is only needed if you intend to build a standalone executable.

#### Debian / Ubuntu

```bash
sudo apt install git adb python3-dev python3-xlib python3-pygame build-essential
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

#### Arch Linux

All runtime dependencies (`pygame`, `python-xlib`) are already installed via `pacman` above.
No `pip` step is needed to *run* ThorCPY. Skip to **Installation**.

If you want to build a standalone executable (optional), create a venv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install pyinstaller
```

#### Debian / Ubuntu / Other distros

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Always activate the venv (`source .venv/bin/activate`) before running `python3 main.py`
> or `python build.py` in subsequent sessions.

`requirements.txt` installs:
- `pygame>=2.6.0` — UI rendering
- `python-xlib>=0.33` — X11 window management (Linux only)

> ThorCPY can also attempt to install `adb` and `scrcpy` automatically on first launch
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

# Find your binary in dist/ThorCPY
# The executable must be placed in a folder containing: bin/, config/, logs/
```

---

## Connecting Your Device

### Via USB (Automatic)
Connect your AYN Thor via USB with USB Debugging enabled. ThorCPY detects the device automatically on startup.

### Via WiFi (Wireless ADB)

Click the **CONNECT** button in the control panel to open the wireless connection overlay.
The button turns **green** when a wireless connection is active.

#### First-time Pairing (Android 11+)

1. On the device: **Developer Options > Wireless debugging > Pair device with pairing code**
2. Note the IP address, pairing port, and 6-digit code shown
3. In ThorCPY, click **CONNECT** → switch to the **First Time Pairing** tab
4. Enter the IP address, pairing port, and 6-digit code, then click **Pair**
5. After pairing, switch to **Quick Connect**, enter the IP with port `5555`, then click **Connect**

#### Subsequent Connections

1. Enable **Wireless debugging** in Developer Options
2. Click **CONNECT** in ThorCPY → **Quick Connect** tab
3. Enter the device IP and port `5555`, click **Connect**

#### Legacy TCP/IP Mode (Android 10 and below)

1. Connect via USB first
2. Run: `adb tcpip 5555`
3. Disconnect USB, then use **Quick Connect** in ThorCPY

---

## Usage

The ThorCPY control panel appears on the right side of your screen:

| Control | Description |
|--------|-------------|
| **Global Scale** | Adjust resolution scale of scrcpy output (requires restart) |
| **Top X / Top Y** | Move top screen position |
| **Bottom X / Bottom Y** | Move bottom screen position |
| **CONNECT** | Open wireless connection overlay (green when connected wirelessly) |
| **DOCK WINDOWS** | Embed both windows into a single container (X11 only) |
| **UNDOCK WINDOWS** | Separate into independent floating windows |
| **SCREENSHOT** | Capture the docked view to clipboard |
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
- Restart ThorCPY

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
- Over WiFi: ThorCPY automatically uses 120 FPS (top) / 60 FPS (bottom)
- Reduce **Global Scale** in the UI to lower resolution and bandwidth
- Use a USB 3.0 port when connecting via cable for best performance
- Close other resource-intensive applications
- To manually adjust FPS limits, edit `DEFAULT_MAX_FPS` in `src/scrcpy_manager.py`

### Layout Issues
- Delete `config/layout.json` and `config/config.json` to reset to defaults
- Reload at 0.6 scale, adjust, and save

### Running in a Distrobox Container (Bazzite / Immutable Systems)

ThorCPY can run inside a [Distrobox](https://distrobox.it/) container on immutable systems like Bazzite.

**Arch container** (`ghcr.io/ublue-os/bazzite-arch`):
```bash
sudo pacman -S git base-devel android-tools scrcpy python-pygame python-xlib
git clone https://github.com/DrSkyfaR/ThorCPY-Linux.git && cd ThorCPY-Linux
python3 main.py
```

**Debian container** (`docker.io/library/debian:stable-slim` or similar):
```bash
sudo apt update
sudo apt install git curl lsb-release python3 python3-venv python3-dev \
     python3-xlib python3-pygame build-essential android-tools-adb
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
ThorCPYLinux/
├── main.py                  # Entry point
├── build.py                 # PyInstaller build script
├── requirements.txt         # Python dependencies
├── assets/                  # Icons, fonts, screenshots
├── bin/                     # Local adb/scrcpy binaries (optional)
├── config/                  # Runtime configuration (auto-created)
├── logs/                    # Log files (auto-created)
└── src/
    ├── launcher.py          # Main controller: docking, layout, wireless
    ├── scrcpy_manager.py    # scrcpy process management & ADB
    ├── ui_pygame.py         # Pygame control panel UI + wireless overlay
    ├── presets.py           # Layout preset store
    ├── config.py            # Config manager
    ├── win32_dock.py        # Windows docking (Win32 API)
    ├── win32_darkmode.py    # Windows dark title bar
    └── docking/
        ├── x11.py           # X11 window docking (Linux)
        └── stateless.py     # Wayland / no-op dock manager
```

---

## Bundled Software

ThorCPY can use locally bundled binaries from the `bin/` folder.
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

- **[the_swest](https://github.com/theswest)** — Original ThorCPY author
- **[eldermonkey](https://github.com/eldermonkey)** — Project logo
- **[scrcpy](https://github.com/Genymobile/scrcpy)** by Romain Vimont — the backend that makes this all possible
- **[Cal Sans](https://github.com/calcom/font)** by Cal.com Inc. — UI typography
- **[Pygame](https://www.pygame.org/)** — UI rendering and event handling
