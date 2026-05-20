# ThorCPY – File browser backend using ADB
# Copyright (C) 2026 the_swest

import os
import subprocess
import threading
import logging

logger = logging.getLogger(__name__)


class FileBrowserBackend:
    """Handles ADB file operations for the file browser overlay."""

    def __init__(self, adb_bin, serial):
        self.adb_bin = adb_bin
        self.serial = serial

    def list_device_dir(self, path, callback):
        """List device directory async. Calls callback(entries, error)."""
        def _run():
            try:
                result = subprocess.run(
                    [self.adb_bin, "-s", self.serial, "shell", "ls", "-la", path],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode != 0:
                    err = (result.stderr or result.stdout).strip()
                    callback(None, err or "Permission denied")
                    return
                entries = _parse_ls_output(result.stdout)
                callback(entries, None)
            except subprocess.TimeoutExpired:
                callback(None, "Timeout listing directory")
            except Exception as e:
                callback(None, str(e))
        threading.Thread(target=_run, daemon=True).start()

    def pull_file(self, device_path, local_dir, callback):
        """Pull file/folder from device to local_dir async. Calls callback(success, message)."""
        def _run():
            try:
                result = subprocess.run(
                    [self.adb_bin, "-s", self.serial, "pull", device_path, local_dir + "/"],
                    capture_output=True, text=True, timeout=120,
                )
                out = (result.stdout + result.stderr).strip()
                if result.returncode == 0:
                    name = device_path.rstrip("/").split("/")[-1]
                    callback(True, f"Saved: {name}")
                else:
                    callback(False, out[:80] or "Pull failed")
            except subprocess.TimeoutExpired:
                callback(False, "Transfer timed out")
            except Exception as e:
                callback(False, str(e)[:80])
        threading.Thread(target=_run, daemon=True).start()

    def push_file(self, local_path, device_dir, callback):
        """Push local file to device_dir async. Calls callback(success, message)."""
        def _run():
            try:
                result = subprocess.run(
                    [self.adb_bin, "-s", self.serial, "push", local_path, device_dir.rstrip("/") + "/"],
                    capture_output=True, text=True, timeout=120,
                )
                out = (result.stdout + result.stderr).strip()
                if result.returncode == 0:
                    callback(True, "Upload complete")
                else:
                    callback(False, out[:80] or "Push failed")
            except subprocess.TimeoutExpired:
                callback(False, "Transfer timed out")
            except Exception as e:
                callback(False, str(e)[:80])
        threading.Thread(target=_run, daemon=True).start()


def list_local_dir(path):
    """List local directory. Returns list of (name, is_dir, size_str)."""
    entries = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                    size = "" if is_dir else _format_size(entry.stat().st_size)
                    entries.append((entry.name, is_dir, size))
                except OSError:
                    entries.append((entry.name, False, "?"))
    except PermissionError:
        pass
    entries.sort(key=lambda x: (not x[1], x[0].lower()))
    return entries


def _parse_ls_output(output):
    """Parse 'adb shell ls -la' output into (name, is_dir, size_str) tuples."""
    entries = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("total") or line.startswith("//"):
            continue
        parts = line.split(None, 7)
        if len(parts) < 8:
            # Fallback: at least get the name from end
            if len(parts) >= 1:
                name = parts[-1]
                if name not in (".", ".."):
                    entries.append((name, False, ""))
            continue
        perms = parts[0]
        size  = parts[4] if len(parts) > 4 else ""
        name  = parts[7]
        if name in (".", ".."):
            continue
        # Strip symlink target
        if " -> " in name:
            name = name.split(" -> ")[0]
        is_dir = perms.startswith("d") or perms.startswith("l")
        entries.append((name, is_dir, _normalize_size(size)))
    entries.sort(key=lambda x: (not x[1], x[0].lower()))
    return entries


def _normalize_size(size_str):
    try:
        return _format_size(int(size_str))
    except (ValueError, TypeError):
        return size_str


def _format_size(n):
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}T"
