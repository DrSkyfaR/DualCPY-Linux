# ThorCPY – File browser backend using ADB
# Copyright (C) 2026 the_swest

import os
import re
import time
import shlex
import shutil
import subprocess
import threading
import logging

logger = logging.getLogger(__name__)

_PCT_RE = re.compile(r"\[\s*(\d+)%\]")


class FileBrowserBackend:
    """Handles ADB file operations for the file browser overlay.

    All public methods run on a daemon thread and report results through
    callbacks. Callbacks are invoked from that worker thread, so the UI layer
    must marshal the results back onto its own thread before touching state.
    """

    def __init__(self, adb_bin, serial):
        self.adb_bin = adb_bin
        self.serial = serial

    def _adb(self, *args):
        return [self.adb_bin, "-s", self.serial, *args]

    # ── Listing ──────────────────────────────────────────────────────────
    def list_device_dir(self, path, callback):
        """List device directory async. Calls callback(entries, error).

        Uses ``ls -laL`` so symlinks are dereferenced to their target type and
        the path is shell-quoted so names containing spaces work correctly.
        """
        def _run():
            try:
                result = subprocess.run(
                    self._adb("shell", f"ls -laL {shlex.quote(path)}"),
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode != 0:
                    err = (result.stderr or result.stdout).strip()
                    callback(None, err or "Permission denied")
                    return
                callback(_parse_ls_output(result.stdout), None)
            except subprocess.TimeoutExpired:
                callback(None, "Timeout listing directory")
            except Exception as e:
                callback(None, str(e))
        threading.Thread(target=_run, daemon=True).start()

    # ── Transfers (with live progress) ───────────────────────────────────
    def pull_file(self, device_path, local_dir, callback, progress=None):
        """Pull file/folder from device to local_dir. callback(success, message)."""
        name = device_path.rstrip("/").split("/")[-1]

        def _run():
            self._transfer(
                self._adb("pull", device_path, local_dir.rstrip("/") + "/"),
                callback, progress, ok_msg=f"Saved: {name}", fail_msg="Pull failed",
            )
        threading.Thread(target=_run, daemon=True).start()

    def push_file(self, local_path, device_dir, callback, progress=None):
        """Push local file/folder to device_dir. callback(success, message)."""
        def _run():
            self._transfer(
                self._adb("push", local_path, device_dir.rstrip("/") + "/"),
                callback, progress, ok_msg="Upload complete", fail_msg="Push failed",
            )
        threading.Thread(target=_run, daemon=True).start()

    def _transfer(self, cmd, callback, progress, ok_msg, fail_msg):
        """Run an adb pull/push, streaming its ``[ NN%]`` progress output.

        adb only prints incremental progress when its stdout is a terminal, so
        on POSIX we attach a pseudo-terminal to get a live percentage. Where
        that is unavailable (e.g. Windows) we fall back to a plain pipe, which
        still yields the final result but no intermediate progress.
        """
        if progress is not None and hasattr(os, "openpty"):
            self._transfer_pty(cmd, callback, progress, ok_msg, fail_msg)
        else:
            self._transfer_pipe(cmd, callback, progress, ok_msg, fail_msg)

    def _emit_lines(self, buf, last_line, progress):
        """Split a buffer on CR/LF, parse percentages, return (tail, last_line)."""
        parts = re.split(r"[\r\n]", buf)
        tail = parts.pop()
        for line in parts:
            line = line.strip()
            if not line:
                continue
            last_line = line
            m = _PCT_RE.search(line)
            if m and progress:
                progress(int(m.group(1)))
        return tail, last_line

    def _transfer_pty(self, cmd, callback, progress, ok_msg, fail_msg):
        import pty
        master, slave = pty.openpty()
        try:
            proc = subprocess.Popen(cmd, stdout=slave, stderr=slave,
                                    stdin=slave, close_fds=True)
        except Exception as e:
            os.close(master)
            os.close(slave)
            callback(False, str(e)[:80])
            return
        os.close(slave)

        start = time.time()
        buf = ""
        last_line = ""
        try:
            while True:
                try:
                    data = os.read(master, 1024)
                except OSError:          # EIO once the child closes the pty
                    data = b""
                if not data:
                    if proc.poll() is not None:
                        break
                    if time.time() - start > 600:
                        proc.kill()
                        callback(False, "Transfer timed out")
                        return
                    continue
                buf += data.decode(errors="replace")
                buf, last_line = self._emit_lines(buf, last_line, progress)
            rc = proc.wait()
        except Exception as e:
            callback(False, str(e)[:80])
            return
        finally:
            os.close(master)

        if rc == 0:
            progress(100)
            callback(True, ok_msg)
        else:
            callback(False, last_line[:80] or fail_msg)

    def _transfer_pipe(self, cmd, callback, progress, ok_msg, fail_msg):
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
        except Exception as e:
            callback(False, str(e)[:80])
            return
        try:
            out, _ = proc.communicate(timeout=600)
        except subprocess.TimeoutExpired:
            proc.kill()
            callback(False, "Transfer timed out")
            return
        last_line = (out or "").strip().splitlines()[-1:] or [""]
        if proc.returncode == 0:
            if progress:
                progress(100)
            callback(True, ok_msg)
        else:
            callback(False, last_line[0][:80] or fail_msg)

    # ── File operations ──────────────────────────────────────────────────
    def delete_device(self, path, callback):
        """Recursively delete a device path. callback(success, message)."""
        self._simple_async(
            self._adb("shell", f"rm -rf {shlex.quote(path)}"),
            callback, "Deleted", "Delete failed")

    def rename_device(self, old_path, new_path, callback):
        """Rename/move a device path. callback(success, message)."""
        self._simple_async(
            self._adb("shell", f"mv {shlex.quote(old_path)} {shlex.quote(new_path)}"),
            callback, "Renamed", "Rename failed")

    def mkdir_device(self, path, callback):
        """Create a directory on the device. callback(success, message)."""
        self._simple_async(
            self._adb("shell", f"mkdir -p {shlex.quote(path)}"),
            callback, "Folder created", "Could not create folder")

    def exists_device(self, path, callback):
        """Check whether a device path already exists. callback(bool)."""
        def _run():
            try:
                r = subprocess.run(
                    self._adb("shell", f"[ -e {shlex.quote(path)} ] && echo Y || echo N"),
                    capture_output=True, text=True, timeout=10,
                )
                callback(r.stdout.strip().endswith("Y"))
            except Exception:
                callback(False)
        threading.Thread(target=_run, daemon=True).start()

    def _simple_async(self, cmd, callback, ok_msg, fail_msg):
        def _run():
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    callback(True, ok_msg)
                else:
                    callback(False, (r.stderr or r.stdout).strip()[:80] or fail_msg)
            except subprocess.TimeoutExpired:
                callback(False, "Operation timed out")
            except Exception as e:
                callback(False, str(e)[:80])
        threading.Thread(target=_run, daemon=True).start()


# ── Local filesystem helpers ─────────────────────────────────────────────
def list_local_dir(path):
    """List local directory. Returns list of (name, is_dir, size_str)."""
    entries = []
    with os.scandir(path) as it:
        for entry in it:
            try:
                is_dir = entry.is_dir(follow_symlinks=True)
                size = "" if is_dir else _format_size(entry.stat().st_size)
                entries.append((entry.name, is_dir, size))
            except OSError:
                entries.append((entry.name, False, "?"))
    entries.sort(key=lambda x: (not x[1], x[0].lower()))
    return entries


def list_local_dir_async(path, callback):
    """List a local directory off the UI thread. callback(entries, error)."""
    def _run():
        try:
            callback(list_local_dir(path), None)
        except PermissionError:
            callback(None, "Permission denied")
        except Exception as e:
            callback(None, str(e))
    threading.Thread(target=_run, daemon=True).start()


def local_op_async(fn, callback, ok_msg, fail_msg):
    """Run a blocking local fs operation off the UI thread. callback(ok, msg)."""
    def _run():
        try:
            fn()
            callback(True, ok_msg)
        except Exception as e:
            callback(False, str(e)[:80] or fail_msg)
    threading.Thread(target=_run, daemon=True).start()


def delete_local(path):
    """Remove a local file or directory tree."""
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


# ── ls -la parsing ───────────────────────────────────────────────────────
def _parse_ls_output(output):
    """Parse 'adb shell ls -laL' output into (name, is_dir, size_str) tuples."""
    entries = []
    for line in output.splitlines():
        line = line.rstrip()
        if not line or line.startswith("total") or line.startswith("//"):
            continue
        parts = line.split(None, 7)
        if len(parts) < 8:
            # Fallback: at least recover the name from the end of the line
            if parts:
                name = parts[-1]
                if name not in (".", ".."):
                    entries.append((name, False, ""))
            continue
        perms = parts[0]
        if perms[:1] in ("c", "b"):
            # Character/block device: size column is "major, minor" (two tokens),
            # which shifts every following field one position to the right.
            shifted = line.split(None, 8)
            name = shifted[8] if len(shifted) > 8 else parts[7]
            size = ""
        else:
            size = parts[4]
            name = parts[7]
        if name in (".", ".."):
            continue
        if " -> " in name:                      # dangling symlink not dereferenced
            name = name.split(" -> ")[0]
        is_dir = perms.startswith("d")
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
