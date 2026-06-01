# DualCPY - Dual-screen scrcpy docking and control UI for Windows
# Copyright (C) 2026 the_swest
# Contact: Github issues
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# src/win32_dock.py

import sys
import time
import logging

try:
    import ctypes
    from ctypes import wintypes
except ImportError:
    pass

from src.docking import DockManager

# Setup logger for this module
logger = logging.getLogger(__name__)

# Constants (Placeholder definitions regarding safety)
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
WS_CLIPCHILDREN = 0x02000000
WS_CLIPSIBLINGS = 0x04000000
WS_OVERLAPPEDWINDOW = 0x00CF0000
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOCOPYBITS = 0x0100

# Platform specific initialization
if sys.platform == "win32":
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
    except AttributeError:
        logger.error("Failed to load user32/kernel32 dlls")
else:
    # Dummy objects to prevent ImportErrors/NameErrors if imported on Linux
    class DummyDLL:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    user32 = DummyDLL()
    kernel32 = DummyDLL()

# Timing constants
MIN_SYNC_INTERVAL = 0.016
THREAD_ATTACH_TIMEOUT = 0.5
DETACH_RETRY_DELAY = 0.01
MAX_DETACH_ATTEMPTS = 3


# Main Dock Manager Class
class Win32Dock(DockManager):
    """
    Handles embedding two windows (top/bottom) inside a container window,
    and synchronizes their position and size when docked/undocked.
    implementation of DockManager for Windows.
    """

    def __init__(self):
        """
        Initialize the window manager.
        """
        logger.info("Initializing Win32Dock")
        self.hwnd_container = None
        self.hwnd_top = None
        self.hwnd_bottom = None
        self._last_sync = 0
        self._min_sync_interval = MIN_SYNC_INTERVAL
        logger.debug("Win32Dock initialized")

    def create_container(self, x, y, w, h):
        """
        Create the main container window using Win32 API.
        Registers a window class, creates the window, and starts a message loop
        in a background thread. Returns the window handle.
        """
        import threading

        WS_OVERLAPPEDWINDOW = 0x00CF0000
        WS_VISIBLE = 0x10000000
        WS_EX_CONTROLPARENT = 0x00010000
        BLACK_BRUSH = 4
        SW_SHOW = 5

        try:
            LRESULT = ctypes.c_longlong
            WPARAM  = ctypes.c_ulonglong
            LPARAM  = ctypes.c_longlong
            WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM)

            WM_CLOSE   = 0x0010
            WM_DESTROY = 0x0002

            def _wndproc(hwnd, msg, wp, lp):
                if msg in (WM_CLOSE, WM_DESTROY):
                    return 0
                return user32.DefWindowProcW(hwnd, msg, wp, lp)

            self._wndproc_ref = WNDPROC(_wndproc)

            class WNDCLASSEX(ctypes.Structure):
                _fields_ = [
                    ("cbSize",        wintypes.UINT),
                    ("style",         wintypes.UINT),
                    ("lpfnWndProc",   ctypes.c_void_p),
                    ("cbClsExtra",    ctypes.c_int),
                    ("cbWndExtra",    ctypes.c_int),
                    ("hInstance",     wintypes.HINSTANCE),
                    ("hIcon",         wintypes.HANDLE),
                    ("hCursor",       wintypes.HANDLE),
                    ("hbrBackground", wintypes.HANDLE),
                    ("lpszMenuName",  wintypes.LPCWSTR),
                    ("lpszClassName", wintypes.LPCWSTR),
                    ("hIconSm",       wintypes.HANDLE),
                ]

            hinst = kernel32.GetModuleHandleW(None)

            wc = WNDCLASSEX()
            wc.cbSize        = ctypes.sizeof(WNDCLASSEX)
            wc.lpfnWndProc   = ctypes.cast(self._wndproc_ref, ctypes.c_void_p).value
            wc.lpszClassName = "DualCPYContainer"
            wc.hInstance     = hinst
            wc.hbrBackground = ctypes.windll.gdi32.GetStockObject(BLACK_BRUSH)
            user32.RegisterClassExW(ctypes.byref(wc))

            style = WS_OVERLAPPEDWINDOW | WS_VISIBLE | WS_CLIPCHILDREN | WS_CLIPSIBLINGS
            rect  = wintypes.RECT(0, 0, int(w), int(h))
            user32.AdjustWindowRectEx(ctypes.byref(rect), style, False, WS_EX_CONTROLPARENT)

            hwnd = user32.CreateWindowExW(
                WS_EX_CONTROLPARENT,
                "DualCPYContainer",
                "DualCPY",
                style,
                int(x), int(y),
                rect.right - rect.left,
                rect.bottom - rect.top,
                None, 0, ctypes.c_void_p(hinst), None,
            )

            if not hwnd:
                logger.error("CreateWindowExW returned null handle")
                return None

            self.hwnd_container = hwnd
            user32.ShowWindow(hwnd, SW_SHOW)
            logger.info(f"Created Win32 container window: {hwnd}")

            def _msg_loop():
                msg = wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))

            threading.Thread(target=_msg_loop, daemon=True).start()
            return hwnd

        except Exception as e:
            logger.error(f"Failed to create Win32 container window: {e}", exc_info=True)
            return None

    def find_window(self, title):
        """
        Find a window by title.
        """
        # Simple FindWindow wrapper
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
             return hwnd
        return None

    def dock_window(self, window_id, parent_id):
        """
        Dock a window into a parent.
        """
        if not window_id or not parent_id:
            return False
        
        apply_docked_style(window_id)
        result = user32.SetParent(window_id, parent_id)
        if not result:
             logger.warning(f"SetParent failed for {window_id}")
             return False
        return True

    def undock_window(self, window_id):
        """
        Undock a window.
        """
        if not window_id:
            return False
        apply_undocked_style(window_id)
        return True

    def sync_layout(self, tx, ty, bx, by, w1, h1, w2, h2, is_docked=True):
        """
        Sync layout of docked windows.
        """
        self.sync(tx, ty, bx, by, w1, h1, w2, h2, is_docked)

    def process_events(self):
        """
        Process platform specific events.
        Win32 message loop is usually handled by the UI framework or specific pumps.
        Here we might peek messages if needed.
        """
        pass
    
    def resize_container(self, container_id, w, h):
        """Resize the container window."""
        if not container_id:
            return
        flags = SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE
        user32.SetWindowPos(container_id, 0, 0, 0, int(w), int(h), flags)

    def set_window_simple_focus(self, window_id):
        """
        Set focus to a window.
        """
        return set_foreground_with_attach(window_id)

    def sync(self, tx, ty, bx, by, w1, h1, w2, h2, is_docked=True):
        """
        Moves and resizes both embedded windows
        """
        # Throttle rapid updates
        now = time.time()
        if now - self._last_sync < self._min_sync_interval:
            return
        self._last_sync = now

        if not (self.hwnd_top and self.hwnd_bottom):
            if not hasattr(self, "_sync_warning_logged"):
                logger.debug("Sync skipped: window handles not available yet")
                self._sync_warning_logged = True
            return

        try:
            flags = SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOCOPYBITS

            if is_docked:
                # Child windows are drawn relative to the container
                user32.SetWindowPos(self.hwnd_top, 0, int(tx), int(ty), int(w1), int(h1), flags)
                user32.SetWindowPos(self.hwnd_bottom, 0, int(bx), int(by), int(w2), int(h2), flags)

            else:
                # For undocked mode, offset is decided by container's screen position
                if self.hwnd_container:
                    rect = wintypes.RECT()
                    if user32.GetWindowRect(self.hwnd_container, ctypes.byref(rect)):
                        screen_tx = rect.left + int(tx)
                        screen_ty = rect.top + int(ty)
                        screen_bx = rect.left + int(bx)
                        screen_by = rect.top + int(by)

                        user32.SetWindowPos(self.hwnd_top, 0, screen_tx, screen_ty, int(w1), int(h1), flags)
                        user32.SetWindowPos(self.hwnd_bottom, 0, screen_bx, screen_by, int(w2), int(h2), flags)
                else:
                    pass

        except Exception as WindowSyncError:
            logger.error(f"Error during window sync: {WindowSyncError}", exc_info=True)


# Window Style Transformers
def apply_docked_style(hwnd):
    if sys.platform != "win32": return
    if not hwnd: return

    try:
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        if not style: return

        style &= ~(WS_BORDER | WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
        style |= WS_CHILD | WS_VISIBLE | WS_CLIPCHILDREN | WS_CLIPSIBLINGS

        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

    except Exception as e:
        logger.error(f"Error applying docked style: {e}")

    try:
        user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE)
    except Exception:
        pass


def apply_undocked_style(hwnd):
    if sys.platform != "win32": return
    if not hwnd: return

    try:
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        if not style: return

        style &= ~WS_CHILD
        style |= WS_OVERLAPPEDWINDOW

        user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        user32.SetParent(hwnd, None)
        
        user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE)
            
    except Exception as e:
        logger.error(f"Error applying undocked style: {e}")


# Focus / Input Manager
def set_foreground_with_attach(hwnd):
    if sys.platform != "win32": return False
    if not hwnd or not user32.IsWindow(hwnd): return False

    try:
        tid_cur = kernel32.GetCurrentThreadId()
        tid_target = user32.GetWindowThreadProcessId(hwnd, None)

        if tid_cur == tid_target:
            return bool(user32.SetForegroundWindow(hwnd))

        if not tid_target: return False

        try:
            if user32.SetForegroundWindow(hwnd): return True
        except: pass

        # Simplified focus logic for refactor brevity
        return False

    except Exception:
        return False