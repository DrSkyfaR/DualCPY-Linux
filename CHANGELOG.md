# Changelog

## [Unreleased]
### Changed
- **UI rewritten in customtkinter** for parity with the upstream Windows app —
  replaces the previous pygame control panel (`src/ui_pygame.py` removed).
  Native dark-themed control panel, sliders, presets, status, and dialogs
- **Device profiles** — multi-device support ported from upstream
  (`device_profile.py`, `custom_profile_store.py`); the scrcpy manager is now
  profile-driven (screen geometry, display IDs, flip, launch delay). On startup
  the connected device is auto-matched to a built-in/custom profile (AYN Thor
  fallback), with an "Edit Device Profiles" editor for custom devices
- customtkinter wireless dialog and device-profile dialogs (Linux-adapted:
  dark-titlebar/clipboard/screenshot shims replace win32clipboard/dxcam/windll)
- File browser re-implemented as a customtkinter window (`file_browser_ui.py`)
  on the existing ADB backend; screenshots now use `mss` and save a PNG
### Added
- Two-panel ADB file browser overlay (device <-> local PC) with transfer,
  create folder, rename, delete, double-click navigation, keyboard control and
  overwrite/delete confirmations
- Configurable Max FPS in Settings (persisted to config, applied to the top
  window; bottom window capped to <=60)
### Changed (ported from upstream DualCPY 0.4, adapted for Linux)
- Improved scrcpy launch parameters: explicit `--video-codec h264` with
  low-latency `--video-codec-options` (operating-rate, bitrate-mode,
  i-frame-interval, intra-refresh-period) plus `--no-mipmaps`, `--no-power-on`,
  `--no-cleanup`, `--print-fps`; render driver stays `opengl` on Linux
- Disable SDL render vsync (`SDL_RENDER_VSYNC=0`) so high-refresh monitors
  don't drop frames against the 60 Hz stream
- More resistant ADB device detection: retries with `kill-server` +
  `start-server` between attempts to recover a stuck adb server
- Best-effort scrcpy process priority bump via `os.setpriority` (Linux nice;
  silently ignored without privileges) instead of the Windows HIGH_PRIORITY_CLASS
- Build bundles as `--onedir` instead of `--onefile` for faster subsequent launches

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
