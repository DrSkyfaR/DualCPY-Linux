# Changelog

## 1.0.0 - 01-06-2026
> Note: previously known as **ThorCPY-Linux**. As of v1.0.0 the project supports
> all dual-screen Android handhelds — not just the AYN Thor — and has been
> renamed to **DualCPY-Linux**, tracking the upstream Windows project (ThorCPY →
> DualCPY). This release brings the Linux port to parity with upstream 1.0,
> adapted throughout for Linux/X11.

### Added
- **Complete UI rewrite in customtkinter** — a native dark-themed control panel
  replacing the old pygame menu (layout sliders, presets, status, FPS selector,
  restart button, dialogs)
- **Multi-device support** — automatic ADB device detection and built-in
  profiles (AYN Thor, RG DS, Pocket DS, Odin 3/2/2 Portal/2 Mini + RDS,
  Retroid Pocket 6/G2/5/4 Pro + RDS). Per-device screen ratios computed on boot
- **Custom device profiles** with an in-app profile editor, a device selector
  on launch, and a remembered "last used profile" per device (in config)
- **Per-profile custom scrcpy launch arguments** (`extra_scrcpy_args_top/bottom`)
- **Gamepad passthrough** — `--gamepad=uhid` on the top screen, disabled on the
  bottom
- **File Transfer window** (adopted from upstream) — two-panel device ↔ local
  PC transfers with file-type icons, quick-nav pills (local: Home/Desktop/…,
  device: Internal/Download/DCIM/…), automatic SD-card detection, inline image
  previews with metadata, and create-folder / rename / delete
- **Configurable Max FPS** in the control panel (persisted; top window uses it,
  bottom capped to ≤60)
- **Configurable screen-launch delay** per profile for lower-powered devices
- App icon used as the favicon across every window

### Changed
- **Rebranded ThorCPY-Linux → DualCPY-Linux**, including the new logo, window
  titles, and app naming; version bumped to 0.4.0
- **scrcpy launch tuning** — explicit `--video-codec h264` with low-latency
  `--video-codec-options` (operating-rate, bitrate-mode, i-frame-interval,
  intra-refresh-period), plus `--no-mipmaps`, `--no-power-on`, `--no-cleanup`,
  `--print-fps`; render driver stays `opengl` on Linux
- Disable SDL render vsync (`SDL_RENDER_VSYNC=0`) so high-refresh monitors don't
  drop frames against the 60 Hz stream
- More resistant ADB detection — retries with `kill-server` + `start-server`
  between attempts to recover a stuck adb server
- Best-effort scrcpy process priority via `os.setpriority` (Linux nice;
  ignored without privileges) instead of the Windows HIGH_PRIORITY_CLASS
- Rebuilt the wireless connection dialog in customtkinter
- Shared UI constants moved to their own module; Thor-specific hardcoded
  constants removed from `scrcpy_manager` so geometry is profile-driven
- Windows-only APIs shimmed for Linux: screenshots via `mss` (was dxcam),
  Tk clipboard (was win32clipboard), no-op dark titlebar (was windll); the
  File Transfer drive list shows mount points instead of drive letters
- Build bundles as `--onedir` instead of `--onefile` for faster relaunches

### Removed
- The pygame control panel (`src/ui_pygame.py`) and the `pygame` dependency

### Bugfixes
- Thread-safe Tk updates — background results (listings, transfers, wireless,
  scan) are marshalled onto the Tk thread via queues, fixing intermittent
  "main thread is not in main loop" crashes on Linux
- File Transfer panels scroll over their rows; folder navigation uses a real
  double-click event instead of fragile timing

## 0.3.0 - 18-03-2026
### Added
- Wireless connection dialog with Quick Connect and Android 11+ pairing-code flow
- Support for legacy TCP/IP wireless mode
- Automatic wireless connection prompt when no USB device detected
- Connection settings persistence in config
- Network scanner — auto-discovers ADB devices on the local subnet
- X11 window docking via `X11DockManager` using python-xlib reparenting
- `StatelessDockManager` as a no-op fallback for Wayland sessions
- Abstract `DockManager` base class — platform backends swapped in at runtime
- Swap screens toggle — switch which display is top/bottom, persisted to config
- Layout mode switching (`DUAL` / `TOP` / `BOTTOM`) with dynamic container resize
- Automatic `adb`/`scrcpy` installation via `pkexec` on first launch (pacman and apt-get supported)
- SIGINT / Ctrl+C signal handling with clean shutdown
- Platform-conditional requirements — `pywin32-ctypes` Windows-only, `python-xlib` Linux-only
### Changed
- `--window-borderless` scrcpy flag now only applied on Windows; Linux keeps window decorations
- Loading screen skipped on Linux to avoid Pygame display-init race condition
- Process force-kill falls back to `SIGKILL` on Linux instead of `taskkill`
- `show_fatal_error()` prints to console on Linux instead of Win32 MessageBox
- Windows binaries (`adb.exe`, `scrcpy.exe`, `.dll`, `.bat`) removed from repository
### Bugfixes
- Fixed issue where bottom screen displays incorrectly, causing non-transparency with screenshots
- Improved window handling to improve stability

## 0.2.0 - 31-01-2026
### Added
- Added ability to change Scrcpy Scale
- Better logging and error handling
### Bugfixes
- Fixed issue with Control Panel crashing on Windows 10 and improved Windows 10 Compatibility
- Updated codebase to become more refined
- Improved window management safeguards for Windows 10


## 0.1.1 - 28-01-2026
### Added
- Added incompatibility warning for Windows 10
- Add thread safety to window focus handling
- Improved dark mode support
### Bugfixes
- Fixed spacing on "DOCK WINDOWS" text 
- Debounce and throttle sync() calls


## 0.1.0 - 26-01-2026
### Added
- Dual-screen scrcpy docking
- Layout presets
- Screenshot capture
- Logging system
- PyInstaller build support
