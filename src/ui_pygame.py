# ThorCPY – Dual-screen scrcpy docking and control UI for Windows
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

# src/ui_pygame.py

import pygame
import os
import time
import logging
import sys

from src.file_browser import FileBrowserBackend, list_local_dir

# Platform specific imports
if sys.platform == "win32":
    try:
        import tkinter as tk
        from ctypes import windll, byref, wintypes
    except ImportError:
        pass
else:
    # Linux specific imports if needed
    pass

from src.win32_darkmode import enable_dark_titlebar

# Setup logger for this module
logger = logging.getLogger(__name__)

# Colour Conversion Fallback
DEFAULT_HEX_COLOUR = (255,255,255)

# Loading screen configuration
LOADING_SCREEN_WIDTH = 400
LOADING_SCREEN_HEIGHT = 200
LOADING_SCREEN_FONT_SIZE = 36
LOADING_ANIMATION_FRAME_COUNT = 120
LOADING_SCREEN_COLOR = (18, 20, 24)
LOADING_SCREEN_X = 60
LOADING_SCREEN_Y = 80

# Control panel window configuration
CONTROL_PANEL_OFFSET_X = 460
CONTROL_PANEL_WIDTH = 450
CONTROL_PANEL_HEIGHT = 900

# Font sizes
LARGE_FONT_SIZE = 24
MEDIUM_FONT_SIZE = 16
SMALL_FONT_SIZE = 14

# Colour palette hex values
BG_HEX = "#121418"
PANEL_HEX = "#1e2128"
BORDER_HEX = "#2d3139"
TEXT_HEX = "#c8cdd8"
ACCENT_HEX = "#4a90e2"
TOP_HEX = "#e74c3c"
BOTTOM_HEX = "#3498db"
SUCCESS_HEX = "#2ecc71"
DANGER_HEX = "#e74c3c"
WARNING_HEX = "#f39c12"

# Status message config
INITIAL_STATUS_MESSAGE_TIME = 0
STATUS_MESSAGE_DURATION = 2.0
DEFAULT_STATUS_MESSAGE_TYPE = "info"

# Preset config
DEFAULT_PRESET_NAME = "NewPreset"
PRESET_CACHE_TIME = 0.5

# Slider dimensions and positioning
SLIDER_LABEL_X = 40
SLIDER_RECT_LEFT = 350
SLIDER_RECT_WIDTH = 60
SLIDER_RECT_HEIGHT = 25
SLIDER_BORDER_RADIUS = 3

SLIDER_TRACK_OFFSET_Y = 30
SLIDER_TRACK_RECT_LEFT = 40
SLIDER_TRACK_RECT_WIDTH = 370
SLIDER_TRACK_RECT_HEIGHT = 4
SLIDER_TRACK_BORDER_RADIUS = 2

SLIDER_HANDLE_FALLBACK_VALUE = 0.5
SLIDER_HANDLE_OFFSET_X = 8
SLIDER_HANDLE_OFFSET_Y = 6
SLIDER_HANDLE_WIDTH = 16
SLIDER_HANDLE_HEIGHT = 16

# Slider value constraints
SLIDER_DRAG_MINIMUM = 0.0
SLIDER_DRAG_MAXIMUM = 1.0

# Scale change detection threshold
SCALE_CHANGE_MIN_DETECTION = 0.01

# UI layout positions
TITLE_MARGIN_X = 20
TITLE_MARGIN_Y = 20
TITLE_SEPARATOR_Y = 60
TITLE_SEPARATOR_LEFT = 20
TITLE_SEPARATOR_RIGHT = 430

LAYOUT_HEADER_X = 20
LAYOUT_HEADER_Y = 80

# Layout Buttons
LAYOUT_BTN_Y = 115
LAYOUT_BTN_HEIGHT = 30
LAYOUT_BTN_WIDTH = 100
LAYOUT_BTN_SPACING = 140 # spacing between starts 20, 160, 300

# Global scale slider config
SLIDER_SCALE_Y = 160
GLOBAL_SCALE_MIN = 0.3
GLOBAL_SCALE_MAX = 1.0

RESTART_NOTIF_X = 40
RESTART_NOTIF_Y = 205

# Slider positions
SCREEN_MIN_POS = -500
SCREEN_MAX_POS = 1500
SLIDER_TOP_X_Y = 230
SLIDER_TOP_Y_Y = 290
SLIDER_BOTTOM_X_Y = 350
SLIDER_BOTTOM_Y_Y = 410

# Dock/Undock button
UNDOCK_BUTTON_X = 40
UNDOCK_BUTTON_Y = 460
UNDOCK_BUTTON_WIDTH = 180
UNDOCK_BUTTON_HEIGHT = 40

# Screenshot button
SCREENSHOT_BUTTON_HEIGHT = 40
SCREENSHOT_BUTTON_X = 40
SCREENSHOT_BUTTON_Y = 510
SCREENSHOT_BUTTON_WIDTH = 180

# Wireless Button
WIRELESS_BUTTON_X = 230
WIRELESS_BUTTON_Y = 510
WIRELESS_BUTTON_WIDTH = 115
WIRELESS_BUTTON_HEIGHT = 40

# Scan Button
SCAN_BUTTON_X = 355
SCAN_BUTTON_Y = 510
SCAN_BUTTON_WIDTH = 55
SCAN_BUTTON_HEIGHT = 40

# Disconnect Button (same position as scan, shown when connected)
DISCONNECT_BUTTON_X = 355
DISCONNECT_BUTTON_Y = 510
DISCONNECT_BUTTON_WIDTH = 55
DISCONNECT_BUTTON_HEIGHT = 40

# Quick Connect Input
QUICK_IP_X = 40
QUICK_IP_Y = 580
QUICK_IP_WIDTH = 250
QUICK_IP_HEIGHT = 30

QUICK_CONNECT_BTN_X = 300
QUICK_CONNECT_BTN_Y = 580
QUICK_CONNECT_BTN_WIDTH = 110
QUICK_CONNECT_BTN_HEIGHT = 30

# Settings Button (narrowed to make room for Files button)
SETTINGS_BUTTON_X = 40
SETTINGS_BUTTON_Y = 625
SETTINGS_BUTTON_WIDTH = 175
SETTINGS_BUTTON_HEIGHT = 35

# Files Button
FILES_BUTTON_X = 225
FILES_BUTTON_Y = 625
FILES_BUTTON_WIDTH = 185
FILES_BUTTON_HEIGHT = 35

# File Browser overlay layout
FB_PAD = 15
FB_PANEL_W = 200          # width of each panel
FB_DIVIDER_X = FB_PAD + FB_PANEL_W + FB_PAD // 2   # x of centre divider line
FB_RIGHT_X = FB_DIVIDER_X + 5                        # x start of right panel
FB_LIST_TOP = 110         # y where file rows start
FB_LIST_BOTTOM = 760      # y where file rows end
FB_ROW_H = 26             # height of each file row
FB_BTN_H = 34             # action button height
FB_BTN_Y = FB_LIST_BOTTOM + 8   # y of action buttons
FB_STATUS_Y = FB_BTN_Y + FB_BTN_H + 10
FB_CLOSE_Y = CONTROL_PANEL_HEIGHT - 55

STATUS_TEXT_X = 225
STATUS_TEXT_Y = 675

# Preset section layout
PRESET_DIVIDER_Y = 720
PRESET_INPUT_DIVIDER_Y = 793
PRESET_DIVIDER_LEFT = 20
PRESET_DIVIDER_RIGHT = 430

PRESET_HEADER_X = 20
PRESET_HEADER_Y = 770

PRESET_Y = 805
PRESET_HEIGHT = 35

PRESET_INPUT_X = 40
PRESET_INPUT_WIDTH = 250

PRESET_TEXT_PADDING_X = 10

PRESET_SAVE_BUTTON_X = 300
PRESET_SAVE_BUTTON_WIDTH = 110

PRESET_BORDER_RADIUS = 5

# Settings Menu Config
SETTINGS_ICON_SIZE = 24
SETTINGS_ICON_X = CONTROL_PANEL_WIDTH - 40
SETTINGS_ICON_Y = 20

SETTINGS_OVERLAY_COLOR = (18, 20, 24, 240) # Semi-transparent bg
SETTINGS_CLOSE_BTN_Y = 50

# Win32 SetWindowPos flags
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
# ... (existing constants)



# Text colors for buttons
WHITE_TEXT = (255, 255, 255)
BLACK_TEXT = (0, 0, 0)

# Preset list layout
# Preset list layout
PRESET_LIST_HEADER_X = 20
PRESET_LIST_HEADER_Y = 695
PRESET_LIST_Y_OFFSET = 730

PRESET_ROW_X = 30
PRESET_ROW_WIDTH = 390
PRESET_ROW_HEIGHT = 40
PRESET_NAME_X_OFFSET = 15

PRESET_LOAD_BUTTON_X = 260
PRESET_DELETE_BUTTON_X = 340
PRESET_BUTTON_Y_OFFSET = 5
PRESET_BUTTON_WIDTH = 70
PRESET_BUTTON_HEIGHT = 30
BUTTON_BORDER_RADIUS = 4

PRESET_ROW_SPACING = 45

# Error message durations
ERROR_STATUS_DURATION = 3.0
SLIDER_ERROR_STATUS_DURATION = 1.5

# Windows clipboard and GDI constants
CF_BITMAP = 2  # Clipboard format for bitmap images
SRCCOPY = 0x00CC0020  # BitBlt copy mode (straight pixel copy)
SW_SHOW = 5


def resource_path(rel):
    """
    Get absolute path to resource, works for python files and for PyInstaller

    PyInstaller bundles resources to a temporary folder (_MEIPASS).
    In development, resources are relative to the script location

    Args:
        rel: Relative path to resource

    Returns:
        Absolute path to resource
    """
    try:
        if hasattr(sys, "_MEIPASS"):
            path = os.path.join(sys._MEIPASS, rel)
            logger.debug(f"Resource path (PyInstaller): {path}")
            return path
        path = os.path.join(os.path.abspath("."), rel)
        logger.debug(f"Resource path (dev): {path}")
        return path
    except Exception as PathResolutionError:
        logger.error(f"Failed to resolve resource path for '{rel}': {PathResolutionError}")
        return rel

# Assets path
FONT_PATH = resource_path("assets/fonts/CalSans-Regular.ttf")
ICON_PATH = resource_path("assets/icon.png")


def hex_to_rgb(hex_color):
    """
    Convert hex color to RGB tuple

    Supports multiple formats:
    "#FF0000", "FF0000". "0xFF0000"

    Args:
        hex_color: Hex string (e.g., "#FF0000" or "FF0000") or int (0xFF0000)

    Returns:
        tuple: (r, g, b)
    """
    try:
        if isinstance(hex_color, int):
            hex_color = f"{hex_color:06x}"

        if isinstance(hex_color, str):
            hex_color = hex_color.lstrip("#")

        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        return rgb
    except Exception as HexConversionError:
        logger.error(f"Failed to convert hex color '{hex_color}': {HexConversionError}")
        return DEFAULT_HEX_COLOUR


# Loading Screen Manager
def show_loading_screen():
    """
    Shows a small startup screen for about 2 seconds.
    """
    logger.info("Initializing loading screen")

    try:
        pygame.init()
    except Exception as PygameInitError:
        logger.error(f"Failed to initialize pygame for loading screen: {PygameInitError}")
        return

    # Set window icon
    try:
        icon_surface = pygame.image.load(ICON_PATH)
        pygame.display.set_icon(icon_surface)
        logger.debug("Loading screen icon set successfully")
    except Exception as LoadingScreenInitError:
        logger.warning(f"Failed to load icon for loading screen: {LoadingScreenInitError}")

    # Initialize window
    try:
        screen = pygame.display.set_mode((LOADING_SCREEN_WIDTH, LOADING_SCREEN_HEIGHT))
        pygame.display.set_caption("ThorCPY Loading...")
        logger.debug("Loading screen window created")
    except Exception as LoadingScreenCreationError:
        logger.error(f"Failed to create loading screen window: {LoadingScreenCreationError}")
        return

    # Enable the dark titlebar for the window (Windows only)
    if sys.platform == "win32":
        try:
            info = pygame.display.get_wm_info()
            hwnd = info.get("window")
            if hwnd:
                enable_dark_titlebar(hwnd)
                logger.debug("Loading screen dark titlebar enabled")
        except Exception as DarkTitlebarEnableError:
            logger.warning(f"Failed to enable dark titlebar for loading screen: {DarkTitlebarEnableError}")

    # Setup font
    try:
        font = pygame.font.Font(FONT_PATH, LOADING_SCREEN_FONT_SIZE)
        logger.debug("Loading screen font loaded")
    except Exception as LoadingFontError:
        logger.warning(f"Failed to load custom font, using default: {LoadingFontError}")
        font = pygame.font.SysFont("Arial", LOADING_SCREEN_FONT_SIZE)

    # Animation loop
    clock = pygame.time.Clock()
    logger.debug(f"Starting loading screen animation ({LOADING_ANIMATION_FRAME_COUNT} frames)")
    for frame in range(LOADING_ANIMATION_FRAME_COUNT):
        try:
            screen.fill(LOADING_SCREEN_COLOR)
            txt = font.render("Starting ThorCPY...", True, (200, 200, 200))
            screen.blit(txt, (LOADING_SCREEN_X, LOADING_SCREEN_Y))
            pygame.display.flip()
            clock.tick(LOADING_ANIMATION_FRAME_COUNT/2)
        except Exception as LoadingScreenRenderError:
            logger.error(f"Error during loading screen render at frame {frame}: {LoadingScreenRenderError}")
            break

    # Cleanup
    try:
        pygame.display.quit()
        logger.info("Loading screen closed")
    except Exception as LoadingScreenCloseError:
        logger.warning(f"Error closing loading screen: {LoadingScreenCloseError}")


# Main Pygame UI class
class PygameUI:
    """
    Main controller UI
    Renders the control panel and manages user interaction
    """

    def __init__(self, launcher):
        """
        Initialize the control panel UI.

        Args:
            launcher: Reference to main Launcher instance for state access
        """
        logger.info("Initializing PygameUI")

        # Reference to the main launcher and controller object
        self.l = launcher

        try:
            pygame.init()
            logger.debug("Pygame initialized for UI")
        except Exception as PygameInitError:
            logger.error(f"Failed to initialize pygame: {PygameInitError}")
            raise

        # Set window icon
        try:
            icon_surface = pygame.image.load(ICON_PATH)
            pygame.display.set_icon(icon_surface)
            logger.debug("UI window icon set successfully")
        except Exception as IconLoadError:
            logger.warning(f"Failed to load UI icon: {IconLoadError}")

        # Position the UI on the far right of the screen
        try:
            # Platform specific screen width fetching
            sw = 1920 # Fallback
            if sys.platform == "win32":
                try:
                    root = tk.Tk()
                    sw = root.winfo_screenwidth()
                    root.destroy()
                except Exception:
                     pass
            else:
                 # On Linux/Pygame, we can try getting display info
                 try:
                     info = pygame.display.Info()
                     sw = info.current_w
                 except Exception:
                     pass

            x_pos = sw - CONTROL_PANEL_OFFSET_X
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x_pos},50"
            logger.debug(f"UI window position set to ({x_pos}, 50)")
        except Exception as ControlWindowPositionError:
            logger.warning(f"Failed to position UI window: {ControlWindowPositionError}")

        # Create window
        try:
            self.screen = pygame.display.set_mode((CONTROL_PANEL_WIDTH, CONTROL_PANEL_HEIGHT))
            pygame.display.set_caption("ThorCPY Control Panel")
            logger.debug("UI window created successfully")
        except Exception as UICreationError:
            logger.error(f"Failed to create UI window: {UICreationError}")
            raise

        # Enable the dark titlebar for the window (Windows only)
        if sys.platform == "win32":
            try:
                info = pygame.display.get_wm_info()
                hwnd = info.get("window")
                if hwnd:
                    enable_dark_titlebar(hwnd)
                    logger.debug("UI window dark titlebar enabled")
            except Exception as DarkTitlebarError:
                logger.warning(f"Failed to enable dark titlebar for UI window: {DarkTitlebarError}")
        else:
            # On Linux (especially Wayland), get_wm_info can cause crashes
            logger.debug("Skipping dark titlebar on non-Windows platform")

        # Load font
        try:
            self.font_lg = pygame.font.Font(FONT_PATH, LARGE_FONT_SIZE)
            self.font_md = pygame.font.Font(FONT_PATH, MEDIUM_FONT_SIZE)
            self.font_sm = pygame.font.Font(FONT_PATH, SMALL_FONT_SIZE)
            logger.debug("UI fonts loaded successfully")
        except Exception as UIFontLoadError:
            logger.warning(f"Failed to load custom fonts, using default: {UIFontLoadError}")
            self.font_lg = pygame.font.SysFont("Arial", LARGE_FONT_SIZE)
            self.font_md = pygame.font.SysFont("Arial", MEDIUM_FONT_SIZE)
            self.font_sm = pygame.font.SysFont("Arial", SMALL_FONT_SIZE)

        # Colors
        self.colors = {
            "bg": hex_to_rgb(BG_HEX),
            "panel": hex_to_rgb(PANEL_HEX),
            "border": hex_to_rgb(BORDER_HEX),
            "text": hex_to_rgb(TEXT_HEX),
            "accent": hex_to_rgb(ACCENT_HEX),
            "top": hex_to_rgb(TOP_HEX),
            "bot": hex_to_rgb(BOTTOM_HEX),
            "success": hex_to_rgb(SUCCESS_HEX),
            "danger": hex_to_rgb(DANGER_HEX),
            "warning": hex_to_rgb(WARNING_HEX),
        }

        # Slider interaction
        self.dragging = None  # Currently dragged slider
        self.m_locked = False  # If mouse has been released
        self.pressed_button = None  # Track which button was pressed

        # Status message
        self.status_msg = ""
        self.status_time = INITIAL_STATUS_MESSAGE_TIME
        self.status_duration = STATUS_MESSAGE_DURATION
        self.status_type = DEFAULT_STATUS_MESSAGE_TYPE

        # Preset input
        self.preset_name = DEFAULT_PRESET_NAME
        self.active_input = False

        # Slider input
        self.active_slider_input = None
        self.input_buffer = ""

        # Quick IP input
        self.quick_ip = self._load_quick_ip()
        self.active_quick_ip = False
        self.quick_ip_selection_start = 0  # For text selection
        self.quick_ip_selection_end = 0

        # Cached presets
        self._preset_cache = None
        self._preset_cache_time = 0

        # Track scale changes
        self._scale_changed = False
        self._original_scale = self.l.global_scale

        # Settings Menu State
        self.show_settings = False

        # Wireless Overlay State
        self.show_wireless = False
        self.wireless_tab = "connect"   # "connect" or "pair"
        self.wireless_fields = {
            "connect_ip": "",
            "connect_port": "5555",
            "pair_ip": "",
            "pair_port": "42055",
            "pair_code": "",
        }
        self.wireless_active_field = None
        self.wireless_status = ""
        self.wireless_status_color = None
        self.wireless_busy = False

        # File Browser Overlay State
        self.show_filebrowser = False
        self.fb_device_path = "/sdcard"
        self.fb_local_path = os.path.expanduser("~")
        self.fb_device_entries = []   # list of (name, is_dir, size_str)
        self.fb_local_entries = []
        self.fb_device_selected = None   # index into fb_device_entries
        self.fb_local_selected = None    # index into fb_local_entries
        self.fb_device_scroll = 0
        self.fb_local_scroll = 0
        self.fb_loading = False          # waiting for ADB ls result
        self.fb_transfer_busy = False
        self.fb_status = ""
        self.fb_status_color = None
        self._fb_backend = None          # FileBrowserBackend, created on first open

        logger.info("PygameUI initialization complete")

    def invalidate_preset_cache(self):
        """Force preset list to reload on the next access"""
        self._preset_cache = None
        logger.debug("Preset cache invalidated")

    def _load_quick_ip(self):
        """Load saved Quick IP from config."""
        try:
            if self.l.config:
                return self.l.config.get("quick_ip", "")
        except Exception:
            pass
        return ""

    def _save_quick_ip(self, ip):
        """Save Quick IP to config."""
        try:
            if self.l.config:
                self.l.config.set("quick_ip", ip)
                logger.debug(f"Saved Quick IP: {ip}")
        except Exception as e:
            logger.warning(f"Failed to save Quick IP: {e}")

    def get_presets(self):
        """
        Get preset list with caching to reduce file I/O.
        Cache is invalidated after PRESET_CACHE_TIME seconds or manually via invalidate_preset_cache().

        Returns:
            dict: Preset name -> preset data mapping
        """
        current_time = time.time()

        if self._preset_cache is None or (current_time - self._preset_cache_time) > PRESET_CACHE_TIME:
            self._preset_cache = self.l.store.load_all()
            self._preset_cache_time = current_time
            logger.debug(
                f"Preset cache refreshed with {len(self._preset_cache)} presets"
            )

        return self._preset_cache

    def show_status(self, msg, status_type=DEFAULT_STATUS_MESSAGE_TYPE,
                    duration=STATUS_MESSAGE_DURATION):
        """
        Display a status message at the bottom of the UI

        Args:
            msg: Message to display
            status_type: Type of message (info, success, error, warning)
            duration: How long to show the message in seconds
        """
        logger.debug(f"Showing status: [{status_type}] {msg}")
        self.status_msg = msg
        self.status_type = status_type
        self.status_time = time.time()
        self.status_duration = duration

    def take_screenshot(self):
        """
        Takes a screenshot of both windows and copies it to the clipboard

        Uses windows GDI to get the container window's client area
        Only works when windows are docked
        """
        if sys.platform != "win32":
            self._take_screenshot_linux()
            return

        logger.info("Taking screenshot of docked windows")
        try:
            user32 = windll.user32
            gdi32 = windll.gdi32
        except Exception:
             self.show_status("Win32 API unavailable", "error")
             return

        try:
            if not self.l.hwnd_container or not self.l.docked:
                logger.warning(
                    "Screenshot aborted: container not available or not docked"
                )
                self.show_status("Must be docked to screenshot", "warning")
                return

            # Get container window area
            rect = wintypes.RECT()
            if not user32.GetClientRect(self.l.hwnd_container, byref(rect)):
                logger.error("Failed to get container client rect")
                self.show_status("Screenshot failed", "error")
                return

            w = rect.right - rect.left
            h = rect.bottom - rect.top
            logger.debug(f"Container dimensions: {w}x{h}")

            # Get Device Contexts
            hwnd_dc = user32.GetDC(self.l.hwnd_container)
            if not hwnd_dc:
                logger.error("Failed to get container DC")
                self.show_status("Screenshot failed", "error")
                return

            mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
            if not mem_dc:
                logger.error("Failed to create compatible DC")
                user32.ReleaseDC(self.l.hwnd_container, hwnd_dc)
                self.show_status("Screenshot failed", "error")
                return

            bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
            if not bitmap:
                logger.error("Failed to create compatible bitmap")
                gdi32.DeleteDC(mem_dc)
                user32.ReleaseDC(self.l.hwnd_container, hwnd_dc)
                self.show_status("Screenshot failed", "error")
                return

            # Copy pixels to bitmap
            old_bitmap = gdi32.SelectObject(mem_dc, bitmap)
            success = gdi32.BitBlt(mem_dc, 0, 0, w, h, hwnd_dc, 0, 0, SRCCOPY)

            if not success:
                logger.error("BitBlt failed during screenshot")
                self.show_status("Screenshot failed", "error")
            else:
                # Copy the bitmap to clipboard
                user32.OpenClipboard(0)
                user32.EmptyClipboard()
                user32.SetClipboardData(CF_BITMAP, bitmap)
                user32.CloseClipboard()
                logger.info("Screenshot copied to clipboard successfully")
                self.show_status("Screenshot copied to clipboard", "success")

            # Cleanup GDI objects
            gdi32.SelectObject(mem_dc, old_bitmap)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(self.l.hwnd_container, hwnd_dc)

        except Exception as ScreenshotErrot:
            logger.error(f"Screenshot error: {ScreenshotErrot}", exc_info=True)
            self.show_status("Screenshot failed", "error")

    def _take_screenshot_linux(self):
        """
        Captures a screenshot from the device via ADB screencap and saves it to screenshots/.
        """
        import subprocess
        import time as _time

        adb = self.l.scrcpy.adb_bin
        serial = self.l.scrcpy.serial

        if not adb:
            self.show_status("ADB not found", "error")
            return
        if not serial:
            self.show_status("No device connected", "error")
            return

        try:
            shots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
            os.makedirs(shots_dir, exist_ok=True)

            stamp = _time.strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join(shots_dir, f"screenshot_{stamp}.png")

            result = subprocess.run(
                [adb, "-s", serial, "exec-out", "screencap", "-p"],
                capture_output=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout:
                with open(out_path, "wb") as f:
                    f.write(result.stdout)
                logger.info(f"Screenshot saved to {out_path}")
                self.show_status(f"Screenshot saved to screenshots/", "success")
            else:
                logger.error(f"screencap failed: {result.stderr}")
                self.show_status("Screenshot failed", "error")

        except subprocess.TimeoutExpired:
            logger.error("Screenshot timed out")
            self.show_status("Screenshot timed out", "error")
        except Exception as e:
            logger.error(f"Screenshot error: {e}", exc_info=True)
            self.show_status("Screenshot failed", "error")

    def draw_slider(self, label, y_pos, val, min_val, max_val, color, attr_name):
        """
        Draw a slider control with editable value box

        Args:
            label: Label text for the slider
            y_pos: Y position to draw at
            val: Current value
            min_val: Minimum value
            max_val: Maximum value
            color: Color for the slider
            attr_name: Attribute name (tx, ty, bx, by) for keyboard input
        """
        try:
            mx, my = pygame.mouse.get_pos()
            m_click = pygame.mouse.get_pressed()[0]

            # Draw label
            self.screen.blit(self.font_md.render(label, True, self.colors["text"]),
                             (SLIDER_LABEL_X, y_pos))

            # Value display box
            val_box = pygame.Rect(SLIDER_RECT_LEFT, y_pos, SLIDER_RECT_WIDTH, SLIDER_RECT_HEIGHT)
            box_hover = val_box.collidepoint(mx, my)
            box_active = self.active_slider_input == attr_name

            box_color = (
                self.colors["accent"]
                if box_active
                else (self.colors["border"] if box_hover else self.colors["panel"])
            )
            pygame.draw.rect(self.screen, box_color, val_box, border_radius=SLIDER_BORDER_RADIUS)

            # Format value text
            if box_active:
                val_text = self.input_buffer
            elif attr_name == "global_scale":
                val_text = f"{val:.2f}"
            else:
                val_text = str(int(val))

            val_render = self.font_sm.render(val_text, True, self.colors["text"])
            val_rect = val_render.get_rect(center=val_box.center)
            self.screen.blit(val_render, val_rect)

            # Activate keyboard input on click
            if m_click and box_hover and not self.m_locked:
                if not box_active:
                    self.active_slider_input = attr_name
                    if attr_name == "global_scale":
                        self.input_buffer = f"{val:.2f}"
                    else:
                        self.input_buffer = str(int(val))
                    self.active_input = False
                    logger.debug(f"Activated slider input for {attr_name}")
                self.m_locked = True

            # Draw slider Track
            track_y = y_pos + SLIDER_TRACK_OFFSET_Y
            track_rect = pygame.Rect(SLIDER_TRACK_RECT_LEFT, track_y, SLIDER_TRACK_RECT_WIDTH,
                                     SLIDER_TRACK_RECT_HEIGHT)
            pygame.draw.rect(
                self.screen, self.colors["border"], track_rect, border_radius=SLIDER_TRACK_BORDER_RADIUS
            )

            # Calculate handle position
            norm_val = ((val - min_val) / (max_val - min_val) if max_val != min_val else SLIDER_HANDLE_FALLBACK_VALUE)
            handle_x = SLIDER_LABEL_X + int(norm_val * SLIDER_TRACK_RECT_WIDTH)
            handle_rect = pygame.Rect(handle_x - SLIDER_HANDLE_OFFSET_X, track_y - SLIDER_HANDLE_OFFSET_Y,
                                      SLIDER_HANDLE_WIDTH, SLIDER_HANDLE_HEIGHT)
            handle_hover = handle_rect.collidepoint(mx, my)

            # Handle with hover feedback
            handle_color = (
                self.colors["text"]
                if handle_hover or self.dragging == attr_name
                else color
            )
            pygame.draw.circle(self.screen, handle_color, (handle_x, track_y + 2), 8)

            # Start drag on click
            if m_click and handle_hover and not self.m_locked and not self.dragging:
                self.dragging = attr_name
                logger.debug(f"Started dragging slider: {attr_name}")

            # Update value whilst dragging
            if self.dragging == attr_name and m_click:
                new_norm = max(SLIDER_DRAG_MINIMUM, min(SLIDER_DRAG_MAXIMUM,
                                                        (mx - SLIDER_TRACK_RECT_LEFT) / SLIDER_TRACK_RECT_WIDTH))
                new_val = min_val + new_norm * (max_val - min_val)
                setattr(self.l, attr_name, new_val)

                # Check to see if global scale has changed
                if (
                    attr_name == "global_scale"
                    and abs(new_val - self._original_scale) > SCALE_CHANGE_MIN_DETECTION
                ):
                    self._scale_changed = True

            # Save on drag release
            if not m_click and self.dragging == attr_name:
                logger.debug(f"Stopped dragging slider: {attr_name}")
                # Save scale separately when scale slider released
                if attr_name == "global_scale":
                    self.l.save_scale()
                else:
                    self.l.save_layout()
                self.dragging = None

        except Exception as SliderDrawError:
            logger.error(f"Error drawing slider '{label}': {SliderDrawError}", exc_info=True)

    def _draw_wl_field(self, screen, label, field_key, y, field_x, field_w, field_h, mx, my, m_click):
        """Draw a labelled wireless input field. Returns the field rect."""
        PAD = 25
        is_active = self.wireless_active_field == field_key
        field_rect = pygame.Rect(field_x, y, field_w, field_h)

        lbl_surf = self.font_sm.render(label, True, self.colors["text"])
        screen.blit(lbl_surf, (PAD, y + (field_h - lbl_surf.get_height()) // 2))

        border_col = self.colors["accent"] if is_active else self.colors["border"]
        pygame.draw.rect(screen, self.colors["panel"], field_rect, border_radius=3)
        pygame.draw.rect(screen, border_col, field_rect, 1, border_radius=3)

        text = self.wireless_fields[field_key]
        display = (text + "|") if is_active else text
        txt_surf = self.font_sm.render(display, True, self.colors["text"])
        screen.blit(txt_surf, (field_x + 6, y + (field_h - txt_surf.get_height()) // 2))

        if m_click and field_rect.collidepoint(mx, my) and not self.m_locked:
            self.wireless_active_field = field_key

        return field_rect

    def _on_wireless_connect(self, success, message):
        """Callback from background thread after connect attempt."""
        self.wireless_busy = False
        self.wireless_status = message
        self.wireless_status_color = self.colors["success"] if success else self.colors["danger"]
        if success:
            ip = self.wireless_fields["connect_ip"]
            port = self.wireless_fields["connect_port"]
            self.quick_ip = f"{ip}:{port}"
            self._save_quick_ip(self.quick_ip)

    def _on_wireless_pair(self, success, message):
        """Callback from background thread after pair attempt."""
        self.wireless_busy = False
        self.wireless_status = message
        self.wireless_status_color = self.colors["success"] if success else self.colors["danger"]
        if success:
            # Pre-fill Quick Connect fields with the paired IP
            self.wireless_fields["connect_ip"] = self.wireless_fields["pair_ip"]
            self.wireless_fields["connect_port"] = "5555"
            self.wireless_tab = "connect"

    def draw_wireless_overlay(self):
        """Draw the wireless connection overlay, replacing the full panel."""
        PAD = 25
        W = CONTROL_PANEL_WIDTH
        H = CONTROL_PANEL_HEIGHT
        FIELD_X = 140
        FIELD_W = W - FIELD_X - PAD
        FIELD_H = 30

        s = pygame.Surface((W, H), pygame.SRCALPHA)
        s.fill((18, 20, 24, 250))
        self.screen.blit(s, (0, 0))

        mx, my = pygame.mouse.get_pos()
        m_click = pygame.mouse.get_pressed()[0]

        # ── Title ────────────────────────────────────────────────────────
        title = self.font_lg.render("Wireless Connection", True, self.colors["text"])
        self.screen.blit(title, (PAD, 20))
        pygame.draw.line(self.screen, self.colors["border"], (PAD, 55), (W - PAD, 55))

        # ── Status ───────────────────────────────────────────────────────
        scrcpy = self.l.scrcpy
        if self.wireless_busy:
            st_text  = "Working..."
            st_color = self.colors["warning"]
        elif self.wireless_status:
            st_text  = self.wireless_status
            st_color = self.wireless_status_color or self.colors["text"]
        elif scrcpy.connection_mode == "wireless" and scrcpy.serial:
            st_text  = f"Connected (wireless): {scrcpy.serial}"
            st_color = self.colors["success"]
        elif scrcpy.serial:
            st_text  = f"Connected (USB): {scrcpy.serial}"
            st_color = self.colors["accent"]
        else:
            st_text  = "Not connected"
            st_color = self.colors["danger"]

        st_surf = self.font_sm.render(st_text, True, st_color)
        self.screen.blit(st_surf, (PAD, 65))
        pygame.draw.line(self.screen, self.colors["border"], (PAD, 90), (W - PAD, 90))

        # ── Tabs ─────────────────────────────────────────────────────────
        tab_y  = 100
        tab_h  = 34
        tab_w  = (W - PAD * 2) // 2 - 3
        tabs   = [("connect", "Quick Connect"), ("pair", "First Time Pairing")]

        for i, (tab_key, tab_label) in enumerate(tabs):
            tx       = PAD + i * (tab_w + 6)
            tab_rect = pygame.Rect(tx, tab_y, tab_w, tab_h)
            is_sel   = self.wireless_tab == tab_key
            bg_col   = self.colors["accent"] if is_sel else self.colors["panel"]
            pygame.draw.rect(self.screen, bg_col, tab_rect, border_radius=4)
            t_surf   = self.font_sm.render(tab_label, True, WHITE_TEXT)
            self.screen.blit(t_surf, t_surf.get_rect(center=tab_rect.center))

            if m_click and tab_rect.collidepoint(mx, my) and not self.m_locked:
                self.pressed_button = f"wl_tab_{tab_key}"
            if not m_click and self.pressed_button == f"wl_tab_{tab_key}":
                if tab_rect.collidepoint(mx, my):
                    self.wireless_tab          = tab_key
                    self.wireless_active_field = None
                    self.wireless_status       = ""
                self.pressed_button = None

        pygame.draw.line(self.screen, self.colors["border"], (PAD, tab_y + tab_h + 8), (W - PAD, tab_y + tab_h + 8))

        # ── Content ──────────────────────────────────────────────────────
        cy = tab_y + tab_h + 22

        if self.wireless_tab == "connect":
            self._draw_wl_field(self.screen, "IP Address:",  "connect_ip",   cy,              FIELD_X, FIELD_W, FIELD_H, mx, my, m_click)
            cy += FIELD_H + 12
            self._draw_wl_field(self.screen, "Port:",        "connect_port", cy,              FIELD_X, FIELD_W // 2, FIELD_H, mx, my, m_click)
            cy += FIELD_H + 20

            hint = self.font_sm.render("Developer Options → Wireless Debugging", True, self.colors["text"])
            self.screen.blit(hint, (PAD, cy))
            cy += 22

            action_btn = pygame.Rect(PAD, cy, W - PAD * 2, 42)
            btn_col    = self.colors["border"] if self.wireless_busy else self.colors["success"]
            a_hover    = action_btn.collidepoint(mx, my) and not self.wireless_busy
            if a_hover:
                btn_col = tuple(min(c + 25, 255) for c in btn_col)
            pygame.draw.rect(self.screen, btn_col, action_btn, border_radius=BUTTON_BORDER_RADIUS)
            btn_txt = self.font_md.render("Connecting..." if self.wireless_busy else "Connect", True, WHITE_TEXT)
            self.screen.blit(btn_txt, btn_txt.get_rect(center=action_btn.center))

            if m_click and a_hover and not self.m_locked:
                self.pressed_button = "wl_do_connect"
            if not m_click and self.pressed_button == "wl_do_connect":
                if a_hover and not self.wireless_busy:
                    ip   = self.wireless_fields["connect_ip"].strip()
                    port = self.wireless_fields["connect_port"].strip()
                    if ip and port:
                        self.wireless_busy   = True
                        self.wireless_status = ""
                        self.l.connect_wireless_async(ip, port, self._on_wireless_connect)
                    else:
                        self.wireless_status       = "Enter IP and port first"
                        self.wireless_status_color = self.colors["warning"]
                self.pressed_button = None

        else:  # pair tab
            hint = self.font_sm.render("Enable 'Wireless debugging' → 'Pair device with code'", True, self.colors["text"])
            self.screen.blit(hint, (PAD, cy))
            cy += 22

            self._draw_wl_field(self.screen, "IP Address:",   "pair_ip",   cy,              FIELD_X, FIELD_W, FIELD_H, mx, my, m_click)
            cy += FIELD_H + 12
            self._draw_wl_field(self.screen, "Pairing Port:", "pair_port", cy,              FIELD_X, FIELD_W // 2, FIELD_H, mx, my, m_click)
            cy += FIELD_H + 12
            self._draw_wl_field(self.screen, "6-digit Code:", "pair_code", cy,              FIELD_X, FIELD_W // 2, FIELD_H, mx, my, m_click)
            cy += FIELD_H + 20

            action_btn = pygame.Rect(PAD, cy, W - PAD * 2, 42)
            btn_col    = self.colors["border"] if self.wireless_busy else self.colors["accent"]
            a_hover    = action_btn.collidepoint(mx, my) and not self.wireless_busy
            if a_hover:
                btn_col = tuple(min(c + 25, 255) for c in btn_col)
            pygame.draw.rect(self.screen, btn_col, action_btn, border_radius=BUTTON_BORDER_RADIUS)
            btn_txt = self.font_md.render("Pairing..." if self.wireless_busy else "Pair", True, WHITE_TEXT)
            self.screen.blit(btn_txt, btn_txt.get_rect(center=action_btn.center))

            if m_click and a_hover and not self.m_locked:
                self.pressed_button = "wl_do_pair"
            if not m_click and self.pressed_button == "wl_do_pair":
                if a_hover and not self.wireless_busy:
                    ip   = self.wireless_fields["pair_ip"].strip()
                    port = self.wireless_fields["pair_port"].strip()
                    code = self.wireless_fields["pair_code"].strip()
                    if ip and port and code and len(code) == 6:
                        self.wireless_busy   = True
                        self.wireless_status = ""
                        self.l.pair_wireless_async(ip, port, code, self._on_wireless_pair)
                    else:
                        self.wireless_status       = "Fill in all fields (6-digit code)"
                        self.wireless_status_color = self.colors["warning"]
                self.pressed_button = None

        # ── Bottom bar ───────────────────────────────────────────────────
        bottom_y = H - 70
        pygame.draw.line(self.screen, self.colors["border"], (PAD, bottom_y - 8), (W - PAD, bottom_y - 8))

        disc_btn   = pygame.Rect(PAD, bottom_y, 150, 38)
        disc_hover = disc_btn.collidepoint(mx, my)
        disc_col   = self.colors["danger"] if disc_hover else self.colors["panel"]
        pygame.draw.rect(self.screen, disc_col, disc_btn, border_radius=BUTTON_BORDER_RADIUS)
        d_txt = self.font_sm.render("Disconnect", True, WHITE_TEXT)
        self.screen.blit(d_txt, d_txt.get_rect(center=disc_btn.center))

        if m_click and disc_hover and not self.m_locked:
            self.pressed_button = "wl_disconnect"
        if not m_click and self.pressed_button == "wl_disconnect":
            if disc_hover:
                if self.l.scrcpy.connection_mode == "wireless":
                    self.l.scrcpy.disconnect_wireless()
                    self.wireless_status       = "Disconnected"
                    self.wireless_status_color = self.colors["warning"]
                else:
                    self.wireless_status       = "No wireless connection active"
                    self.wireless_status_color = self.colors["warning"]
            self.pressed_button = None

        close_btn   = pygame.Rect(W - PAD - 110, bottom_y, 110, 38)
        close_hover = close_btn.collidepoint(mx, my)
        close_col   = (60, 65, 80) if close_hover else self.colors["panel"]
        pygame.draw.rect(self.screen, close_col, close_btn, border_radius=BUTTON_BORDER_RADIUS)
        c_txt = self.font_sm.render("Close", True, WHITE_TEXT)
        self.screen.blit(c_txt, c_txt.get_rect(center=close_btn.center))

        if m_click and close_hover and not self.m_locked:
            self.pressed_button = "wl_close"
        if not m_click and self.pressed_button == "wl_close":
            if close_hover:
                self.show_wireless         = False
                self.wireless_active_field = None
                self.wireless_status       = ""
            self.pressed_button = None

    def draw_settings_icon(self):
        """
        Draws the settings gear icon.
        """
        mx, my = pygame.mouse.get_pos()
        m_click = pygame.mouse.get_pressed()[0]
        
        icon_rect = pygame.Rect(SETTINGS_ICON_X, SETTINGS_ICON_Y, SETTINGS_ICON_SIZE, SETTINGS_ICON_SIZE)
        is_hover = icon_rect.collidepoint(mx, my)
        
        color = self.colors["accent"] if is_hover or self.show_settings else self.colors["text"]
        
        # Simple Gear Icon (Circle + Teeth)
        center = icon_rect.center
        radius = SETTINGS_ICON_SIZE // 2 - 2
        pygame.draw.circle(self.screen, color, center, radius, 2)
        pygame.draw.circle(self.screen, color, center, 4) # Inner axle
        
        # Interaction
        if m_click and is_hover and not self.m_locked:
            self.pressed_button = "settings_toggle"
            
        if not m_click and self.pressed_button == "settings_toggle":
            if is_hover:
                self.show_settings = not self.show_settings
                logger.debug(f"Toggled settings menu: {self.show_settings}")
            self.pressed_button = None

    def draw_settings_overlay(self):
        """
        Draws the settings overlay menu.
        """
        # Semi-transparent background
        s = pygame.Surface((CONTROL_PANEL_WIDTH, CONTROL_PANEL_HEIGHT), pygame.SRCALPHA)
        s.fill(SETTINGS_OVERLAY_COLOR)
        self.screen.blit(s, (0,0))
        
        mx, my = pygame.mouse.get_pos()
        m_click = pygame.mouse.get_pressed()[0]
        
        # Title
        title_surf = self.font_lg.render("Settings", True, self.colors["text"])
        self.screen.blit(title_surf, (20, 20))
        
        # Divider
        pygame.draw.line(self.screen, self.colors["border"], (20, 60), (CONTROL_PANEL_WIDTH - 20, 60))
        
        # --- Screen Swapping ---
        swap_y = 100
        
        # Label
        label_surf = self.font_md.render("Swap Screens (Top <-> Bottom)", True, self.colors["text"])
        self.screen.blit(label_surf, (40, swap_y))
        
        # Toggle Button
        toggle_x = 350
        toggle_w = 60
        toggle_h = 30
        toggle_rect = pygame.Rect(toggle_x, swap_y - 5, toggle_w, toggle_h)
        is_hover = toggle_rect.collidepoint(mx, my)
        
        is_on = self.l.swap_screens
        
        # Draw Toggle
        bg_col = self.colors["success"] if is_on else self.colors["panel"]
        if is_hover:
            # Lighten slightly
            bg_col = (min(bg_col[0]+20, 255), min(bg_col[1]+20, 255), min(bg_col[2]+20, 255))
            
        pygame.draw.rect(self.screen, bg_col, toggle_rect, border_radius=15)
        
        # Knob
        knob_x = toggle_rect.right - 25 if is_on else toggle_rect.left + 5
        pygame.draw.circle(self.screen, WHITE_TEXT, (knob_x + 10, toggle_rect.centery), 10)
        
        # Description / Warning
        warn_surf = self.font_sm.render("Requires restart to apply.", True, self.colors["warning"])
        self.screen.blit(warn_surf, (40, swap_y + 30))
        
        # Handle Toggle Click
        if m_click and is_hover and not self.m_locked:
            self.pressed_button = "swap_toggle"
            
        if not m_click and self.pressed_button == "swap_toggle":
            if is_hover:
                # Toggle value
                new_val = not self.l.swap_screens
                self.l.save_swap_screens(new_val)
            self.pressed_button = None

        # --- Restart Button ---
        restart_y = 200
        restart_btn = pygame.Rect(40, restart_y, 370, 45)
        r_hover = restart_btn.collidepoint(mx, my)
        
        col = self.colors["danger"] if r_hover else self.colors["panel"]
        pygame.draw.rect(self.screen, col, restart_btn, border_radius=BUTTON_BORDER_RADIUS)
        
        txt = self.font_md.render("Restart Scrcpy Now", True, WHITE_TEXT)
        txt_rect = txt.get_rect(center=restart_btn.center)
        self.screen.blit(txt, txt_rect)
        
        if m_click and r_hover and not self.m_locked:
            self.pressed_button = "restart_btn"
            
        if not m_click and self.pressed_button == "restart_btn":
            if r_hover:
                self.l.restart_scrcpy()
            self.pressed_button = None
            
        # --- Close Button ---
        # Reuse the settings icon area as close button logic is handled in draw_settings_icon toggle
        # But maybe add explicit back button?
        
        back_y = CONTROL_PANEL_HEIGHT - 60
        back_btn = pygame.Rect(40, back_y, 370, 40)
        b_hover = back_btn.collidepoint(mx, my)
        
        col = self.colors["accent"] if b_hover else self.colors["panel"]
        pygame.draw.rect(self.screen, col, back_btn, border_radius=BUTTON_BORDER_RADIUS)
        
        txt = self.font_md.render("Back", True, WHITE_TEXT)
        txt_rect = txt.get_rect(center=back_btn.center)
        self.screen.blit(txt, txt_rect)
        
        if m_click and b_hover and not self.m_locked:
            self.pressed_button = "back_btn"
            
        if not m_click and self.pressed_button == "back_btn":
            if b_hover:
                self.show_settings = False
            self.pressed_button = None

    # ── File Browser ────────────────────────────────────────────────────────

    def _fb_open(self):
        """Open the file browser overlay and initialise state."""
        adb  = self.l.scrcpy.adb_bin
        serial = self.l.scrcpy.serial
        if not adb or not serial:
            self.show_status("No device connected", "error", 3.0)
            return
        self._fb_backend = FileBrowserBackend(adb, serial)
        self.fb_device_path = "/sdcard"
        self.fb_local_path  = os.path.expanduser("~")
        self.fb_device_entries = []
        self.fb_local_entries  = list_local_dir(self.fb_local_path)
        self.fb_device_selected = None
        self.fb_local_selected  = None
        self.fb_device_scroll = 0
        self.fb_local_scroll  = 0
        self.fb_status = ""
        self.fb_transfer_busy = False
        self.show_filebrowser = True
        self._fb_load_device(self.fb_device_path)

    def _fb_load_device(self, path):
        """Trigger async ADB ls for the given device path."""
        self.fb_loading = True
        self.fb_device_entries = []
        self.fb_device_selected = None
        self.fb_device_scroll = 0

        def _cb(entries, error):
            self.fb_loading = False
            if error:
                self.fb_status = f"Error: {error}"
                self.fb_status_color = self.colors["danger"]
                self.fb_device_entries = []
            else:
                self.fb_device_entries = entries or []
                self.fb_status = ""

        self._fb_backend.list_device_dir(path, _cb)

    def _fb_navigate_device(self, name, is_dir):
        if is_dir:
            new_path = self.fb_device_path.rstrip("/") + "/" + name
            self.fb_device_path = new_path
            self._fb_load_device(new_path)
        else:
            # Toggle selection
            idx = next((i for i, e in enumerate(self.fb_device_entries) if e[0] == name), None)
            self.fb_device_selected = None if self.fb_device_selected == idx else idx

    def _fb_navigate_local(self, name, is_dir):
        if is_dir:
            new_path = os.path.join(self.fb_local_path, name)
            try:
                entries = list_local_dir(new_path)
                self.fb_local_path = new_path
                self.fb_local_entries = entries
                self.fb_local_selected = None
                self.fb_local_scroll = 0
            except Exception as e:
                self.fb_status = str(e)[:60]
                self.fb_status_color = self.colors["danger"]
        else:
            idx = next((i for i, e in enumerate(self.fb_local_entries) if e[0] == name), None)
            self.fb_local_selected = None if self.fb_local_selected == idx else idx

    def _fb_refresh_device(self):
        """Reload current device directory."""
        self._fb_load_device(self.fb_device_path)

    def _fb_refresh_local(self):
        """Reload current local directory."""
        self.fb_local_entries = list_local_dir(self.fb_local_path)
        self.fb_local_selected = None

    def _fb_back_device(self):
        parent = self.fb_device_path.rstrip("/").rsplit("/", 1)[0] or "/"
        self.fb_device_path = parent
        self._fb_load_device(parent)

    def _fb_back_local(self):
        parent = os.path.dirname(self.fb_local_path)
        if parent != self.fb_local_path:
            self.fb_local_path = parent
            self.fb_local_entries = list_local_dir(parent)
            self.fb_local_selected = None
            self.fb_local_scroll = 0

    def _fb_pull(self):
        """Download selected device file to current local directory."""
        if self.fb_device_selected is None or self.fb_transfer_busy:
            return
        name, is_dir, _ = self.fb_device_entries[self.fb_device_selected]
        device_path = self.fb_device_path.rstrip("/") + "/" + name
        local_dir   = self.fb_local_path
        self.fb_transfer_busy = True
        self.fb_status = f"Downloading {name}..."
        self.fb_status_color = self.colors["warning"]

        def _cb(success, msg):
            self.fb_transfer_busy = False
            self.fb_status = msg
            self.fb_status_color = self.colors["success"] if success else self.colors["danger"]
            if success:
                self.fb_local_entries = list_local_dir(self.fb_local_path)

        self._fb_backend.pull_file(device_path, local_dir, _cb)

    def _fb_push(self):
        """Upload selected local file to current device directory."""
        if self.fb_local_selected is None or self.fb_transfer_busy:
            return
        name, is_dir, _ = self.fb_local_entries[self.fb_local_selected]
        local_path  = os.path.join(self.fb_local_path, name)
        device_dir  = self.fb_device_path
        self.fb_transfer_busy = True
        self.fb_status = f"Uploading {name}..."
        self.fb_status_color = self.colors["warning"]

        def _cb(success, msg):
            self.fb_transfer_busy = False
            self.fb_status = msg
            self.fb_status_color = self.colors["success"] if success else self.colors["danger"]
            if success:
                self._fb_load_device(self.fb_device_path)

        self._fb_backend.push_file(local_path, device_dir, _cb)

    def _fb_draw_panel(self, x, w, path, entries, selected_idx, scroll,
                       loading, panel_id, mx, my, m_click):
        """
        Draw one file-browser panel. Returns (new_selected_idx, new_scroll, clicked_entry_idx).
        clicked_entry_idx is set on click release to trigger navigation / selection.
        """
        # Path breadcrumb bar
        path_surf = self.font_sm.render(path[-38:] if len(path) > 38 else path, True, self.colors["text"])
        crumb_rect = pygame.Rect(x, FB_LIST_TOP - 24, w, 20)
        pygame.draw.rect(self.screen, self.colors["panel"], crumb_rect, border_radius=2)
        self.screen.blit(path_surf, (x + 4, FB_LIST_TOP - 22))

        # Panel border
        panel_rect = pygame.Rect(x, FB_LIST_TOP, w, FB_LIST_BOTTOM - FB_LIST_TOP)
        pygame.draw.rect(self.screen, self.colors["border"], panel_rect, 1, border_radius=3)

        clicked_idx = None
        new_selected = selected_idx
        new_scroll   = scroll

        if loading:
            loading_surf = self.font_sm.render("Loading...", True, self.colors["warning"])
            self.screen.blit(loading_surf, (x + 8, FB_LIST_TOP + 12))
            return new_selected, new_scroll, clicked_idx

        if not entries:
            empty_surf = self.font_sm.render("(empty)", True, (100, 100, 100))
            self.screen.blit(empty_surf, (x + 8, FB_LIST_TOP + 12))
            return new_selected, new_scroll, clicked_idx

        visible_rows = (FB_LIST_BOTTOM - FB_LIST_TOP) // FB_ROW_H
        new_scroll = max(0, min(scroll, max(0, len(entries) - visible_rows)))

        clip_rect = pygame.Rect(x, FB_LIST_TOP, w, FB_LIST_BOTTOM - FB_LIST_TOP)
        self.screen.set_clip(clip_rect)

        for i, (name, is_dir, size) in enumerate(entries[new_scroll:new_scroll + visible_rows]):
            real_i = i + new_scroll
            ry = FB_LIST_TOP + i * FB_ROW_H
            row_rect = pygame.Rect(x, ry, w, FB_ROW_H)

            # Background
            if real_i == selected_idx:
                pygame.draw.rect(self.screen, self.colors["accent"], row_rect)
            elif row_rect.collidepoint(mx, my):
                pygame.draw.rect(self.screen, self.colors["border"], row_rect)

            # Icon
            icon = "/" if is_dir else " "
            icon_surf = self.font_sm.render(icon, True,
                                            self.colors["top"] if is_dir else self.colors["text"])
            self.screen.blit(icon_surf, (x + 4, ry + 5))

            # Name (truncated)
            max_name_w = w - 60
            display_name = name
            name_surf = self.font_sm.render(display_name, True, self.colors["text"])
            while name_surf.get_width() > max_name_w and len(display_name) > 4:
                display_name = display_name[:-2]
                name_surf = self.font_sm.render(display_name + "~", True, self.colors["text"])
            self.screen.blit(name_surf, (x + 16, ry + 5))

            # Size (right-aligned)
            if size:
                size_surf = self.font_sm.render(size, True, (120, 120, 130))
                self.screen.blit(size_surf, (x + w - size_surf.get_width() - 4, ry + 5))

            # Click detection
            if m_click and row_rect.collidepoint(mx, my) and not self.m_locked:
                self.pressed_button = f"fb_{panel_id}_{real_i}"
            if not m_click and self.pressed_button == f"fb_{panel_id}_{real_i}":
                if row_rect.collidepoint(mx, my):
                    clicked_idx = real_i
                self.pressed_button = None

        self.screen.set_clip(None)

        # Scrollbar
        total = len(entries)
        if total > visible_rows:
            bar_h = max(20, int((visible_rows / total) * (FB_LIST_BOTTOM - FB_LIST_TOP)))
            bar_y = FB_LIST_TOP + int((new_scroll / max(1, total - visible_rows))
                                      * (FB_LIST_BOTTOM - FB_LIST_TOP - bar_h))
            pygame.draw.rect(self.screen, self.colors["border"],
                             pygame.Rect(x + w - 5, bar_y, 4, bar_h), border_radius=2)

        return new_selected, new_scroll, clicked_idx

    def draw_filebrowser_overlay(self):
        """Draw the two-panel file browser overlay."""
        W = CONTROL_PANEL_WIDTH
        H = CONTROL_PANEL_HEIGHT
        PAD = FB_PAD

        # Background
        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        bg.fill((18, 20, 24, 252))
        self.screen.blit(bg, (0, 0))

        mx, my = pygame.mouse.get_pos()
        m_click = pygame.mouse.get_pressed()[0]

        # Title
        title = self.font_lg.render("File Browser", True, self.colors["text"])
        self.screen.blit(title, (PAD, 18))
        pygame.draw.line(self.screen, self.colors["border"], (PAD, 52), (W - PAD, 52))

        # Panel headers
        dev_hdr = self.font_sm.render("DEVICE", True, self.colors["top"])
        loc_hdr = self.font_sm.render("LOCAL PC", True, self.colors["bot"])
        self.screen.blit(dev_hdr, (PAD, 60))
        self.screen.blit(loc_hdr, (FB_RIGHT_X, 60))

        # Centre divider
        pygame.draw.line(self.screen, self.colors["border"],
                         (FB_DIVIDER_X, 55), (FB_DIVIDER_X, FB_LIST_BOTTOM + 5))

        # Draw panels
        (self.fb_device_selected,
         self.fb_device_scroll,
         dev_clicked) = self._fb_draw_panel(
            PAD, FB_PANEL_W,
            self.fb_device_path, self.fb_device_entries,
            self.fb_device_selected, self.fb_device_scroll,
            self.fb_loading, "dev", mx, my, m_click)

        (self.fb_local_selected,
         self.fb_local_scroll,
         loc_clicked) = self._fb_draw_panel(
            FB_RIGHT_X, W - FB_RIGHT_X - PAD,
            self.fb_local_path, self.fb_local_entries,
            self.fb_local_selected, self.fb_local_scroll,
            False, "loc", mx, my, m_click)

        # Refresh buttons — drawn over the right edge of each breadcrumb bar
        _crumb_y  = FB_LIST_TOP - 24
        _crumb_h  = 20
        _ref_w    = 30
        ref_dev_rect = pygame.Rect(FB_PAD + FB_PANEL_W - _ref_w, _crumb_y, _ref_w, _crumb_h)
        ref_loc_rect = pygame.Rect(
            FB_RIGHT_X + (CONTROL_PANEL_WIDTH - FB_RIGHT_X - FB_PAD) - _ref_w,
            _crumb_y, _ref_w, _crumb_h
        )

        for ref_rect, ref_key in ((ref_dev_rect, "fb_ref_dev"), (ref_loc_rect, "fb_ref_loc")):
            is_hov = ref_rect.collidepoint(mx, my)
            col = self.colors["accent"] if is_hov else (50, 55, 70)
            pygame.draw.rect(self.screen, col, ref_rect, border_radius=3)
            r_surf = self.font_sm.render("↺", True, WHITE_TEXT)
            self.screen.blit(r_surf, r_surf.get_rect(center=ref_rect.center))
            if m_click and is_hov and not self.m_locked:
                self.pressed_button = ref_key
            if not m_click and self.pressed_button == ref_key:
                if is_hov:
                    if ref_key == "fb_ref_dev":
                        self._fb_refresh_device()
                    else:
                        self._fb_refresh_local()
                self.pressed_button = None

        # Handle clicks → navigate or select
        if dev_clicked is not None and dev_clicked < len(self.fb_device_entries):
            name, is_dir, _ = self.fb_device_entries[dev_clicked]
            self._fb_navigate_device(name, is_dir)

        if loc_clicked is not None and loc_clicked < len(self.fb_local_entries):
            name, is_dir, _ = self.fb_local_entries[loc_clicked]
            self._fb_navigate_local(name, is_dir)

        # ── Action buttons ───────────────────────────────────────────────
        btn_y  = FB_BTN_Y
        bw_sm  = 80
        bw_mid = 110

        def _draw_btn(rect, label, color, text_col=None):
            tc = text_col or WHITE_TEXT
            is_hov = rect.collidepoint(mx, my)
            col = tuple(min(c + 25, 255) for c in color) if is_hov else color
            pygame.draw.rect(self.screen, col, rect, border_radius=BUTTON_BORDER_RADIUS)
            surf = self.font_sm.render(label, True, tc)
            self.screen.blit(surf, surf.get_rect(center=rect.center))
            return is_hov

        # Device: ← Back
        back_dev_rect = pygame.Rect(PAD, btn_y, bw_sm, FB_BTN_H)
        _draw_btn(back_dev_rect, "← Back", self.colors["panel"])
        if m_click and back_dev_rect.collidepoint(mx, my) and not self.m_locked:
            self.pressed_button = "fb_back_dev"
        if not m_click and self.pressed_button == "fb_back_dev":
            if back_dev_rect.collidepoint(mx, my):
                self._fb_back_device()
            self.pressed_button = None

        # Device → Local: ↓ Download
        has_dev_sel = self.fb_device_selected is not None and not self.fb_transfer_busy
        dl_color = self.colors["success"] if has_dev_sel else (50, 60, 50)
        dl_rect = pygame.Rect(PAD + bw_sm + 5, btn_y, bw_mid, FB_BTN_H)
        _draw_btn(dl_rect, "↓ To Local" if not self.fb_transfer_busy else "...",
                  dl_color)
        if has_dev_sel and m_click and dl_rect.collidepoint(mx, my) and not self.m_locked:
            self.pressed_button = "fb_pull"
        if not m_click and self.pressed_button == "fb_pull":
            if dl_rect.collidepoint(mx, my) and has_dev_sel:
                self._fb_pull()
            self.pressed_button = None

        # Local: ← Back
        back_loc_rect = pygame.Rect(FB_RIGHT_X, btn_y, bw_sm, FB_BTN_H)
        _draw_btn(back_loc_rect, "← Back", self.colors["panel"])
        if m_click and back_loc_rect.collidepoint(mx, my) and not self.m_locked:
            self.pressed_button = "fb_back_loc"
        if not m_click and self.pressed_button == "fb_back_loc":
            if back_loc_rect.collidepoint(mx, my):
                self._fb_back_local()
            self.pressed_button = None

        # Local → Device: ↑ Upload
        has_loc_sel = self.fb_local_selected is not None and not self.fb_transfer_busy
        ul_color = self.colors["accent"] if has_loc_sel else (40, 50, 70)
        ul_rect = pygame.Rect(FB_RIGHT_X + bw_sm + 5, btn_y,
                              W - FB_RIGHT_X - bw_sm - 5 - PAD, FB_BTN_H)
        _draw_btn(ul_rect, "↑ To Device" if not self.fb_transfer_busy else "...",
                  ul_color)
        if has_loc_sel and m_click and ul_rect.collidepoint(mx, my) and not self.m_locked:
            self.pressed_button = "fb_push"
        if not m_click and self.pressed_button == "fb_push":
            if ul_rect.collidepoint(mx, my) and has_loc_sel:
                self._fb_push()
            self.pressed_button = None

        # ── Status bar ───────────────────────────────────────────────────
        pygame.draw.line(self.screen, self.colors["border"],
                         (PAD, FB_STATUS_Y - 4), (W - PAD, FB_STATUS_Y - 4))
        if self.fb_status:
            col = self.fb_status_color or self.colors["text"]
            st_surf = self.font_sm.render(self.fb_status[:60], True, col)
            self.screen.blit(st_surf, st_surf.get_rect(center=(W // 2, FB_STATUS_Y + 8)))

        # ── Hint line ────────────────────────────────────────────────────
        hint = self.font_sm.render("Click folder to open  |  Click file to select", True, (80, 85, 100))
        self.screen.blit(hint, hint.get_rect(center=(W // 2, FB_STATUS_Y + 30)))

        # ── Close button ─────────────────────────────────────────────────
        pygame.draw.line(self.screen, self.colors["border"],
                         (PAD, FB_CLOSE_Y - 8), (W - PAD, FB_CLOSE_Y - 8))
        close_rect = pygame.Rect(W - PAD - 110, FB_CLOSE_Y, 110, 38)
        _draw_btn(close_rect, "Close", self.colors["panel"])
        if m_click and close_rect.collidepoint(mx, my) and not self.m_locked:
            self.pressed_button = "fb_close"
        if not m_click and self.pressed_button == "fb_close":
            if close_rect.collidepoint(mx, my):
                self.show_filebrowser = False
            self.pressed_button = None

        # Reset lock
        if not m_click:
            self.m_locked = False

    # ── End File Browser ─────────────────────────────────────────────────

    def render(self):
        """
        Main render loop for the UI
        Draws all UI elements and handles the mouse interactions
        """
        try:
            mx, my = pygame.mouse.get_pos()
            m_click = pygame.mouse.get_pressed()[0]

            self.screen.fill(self.colors["bg"])

            # Title
            title_txt = self.font_lg.render("ThorCPY Control Panel", True, self.colors["text"])
            self.screen.blit(title_txt, (TITLE_MARGIN_X, TITLE_MARGIN_Y))

            pygame.draw.line(self.screen, self.colors["border"], (TITLE_SEPARATOR_LEFT, TITLE_SEPARATOR_Y),
                             (TITLE_SEPARATOR_RIGHT, TITLE_SEPARATOR_Y))
            
            # Settings Icon
            self.draw_settings_icon()
            
            if self.show_settings:
                self.draw_settings_overlay()
                pygame.display.flip()
                return

            if self.show_wireless:
                self.draw_wireless_overlay()
                pygame.display.flip()
                return

            if self.show_filebrowser:
                self.draw_filebrowser_overlay()
                pygame.display.flip()
                return

            # Check if we need to deactivate Quick IP input (clicked outside)
            if self.active_quick_ip and m_click and not self.m_locked:
                ip_rect = pygame.Rect(QUICK_IP_X, QUICK_IP_Y, QUICK_IP_WIDTH, QUICK_IP_HEIGHT)
                if not ip_rect.collidepoint(mx, my):
                    self.active_quick_ip = False
                    self.input_buffer = ""
                    self.quick_ip_selection_start = 0
                    self.quick_ip_selection_end = 0
                    logger.debug("Quick IP deactivated (clicked outside)")

            # Layout controls header
            self.screen.blit(
                self.font_lg.render("Layout Controls", True, self.colors["text"]),
                (LAYOUT_HEADER_X, LAYOUT_HEADER_Y),
            )
            
            # Layout Buttons
            self.draw_layout_buttons()

            # Global Scale Slider
            scale_label = (
                f"GLOBAL SCALE - Active: {self.l.launch_scale:.2f}"
            )
            self.draw_slider(
                scale_label,
                SLIDER_SCALE_Y,
                self.l.global_scale,
                GLOBAL_SCALE_MIN,
                GLOBAL_SCALE_MAX,
                self.colors["accent"],
                "global_scale",
            )

            # Restart notification for if the scale has changed
            if hasattr(self, "_scale_changed") and self._scale_changed:
                restart_txt = self.font_sm.render(
                    "Restart ThorCPY to apply scale", True, self.colors["warning"]
                )
                self.screen.blit(restart_txt, (RESTART_NOTIF_X, RESTART_NOTIF_Y))

            # Sliders
            self.draw_slider(
                "TOP X", SLIDER_TOP_X_Y, self.l.tx, SCREEN_MIN_POS, SCREEN_MAX_POS,
                self.colors["top"], "tx"
            )
            self.draw_slider(
                "TOP Y", SLIDER_TOP_Y_Y, self.l.ty, SCREEN_MIN_POS, SCREEN_MAX_POS,
                self.colors["top"], "ty"
            )
            self.draw_slider(
                "BOTTOM X", SLIDER_BOTTOM_X_Y, self.l.bx, SCREEN_MIN_POS, SCREEN_MAX_POS,
                self.colors["bot"], "bx"
            )
            self.draw_slider(
                "BOTTOM Y", SLIDER_BOTTOM_Y_Y, self.l.by, SCREEN_MIN_POS, SCREEN_MAX_POS,
                self.colors["bot"], "by"
            )

            # Undock/Dock Button
            undock_btn = pygame.Rect(UNDOCK_BUTTON_X, UNDOCK_BUTTON_Y, UNDOCK_BUTTON_WIDTH, UNDOCK_BUTTON_HEIGHT)
            u_hover = undock_btn.collidepoint(mx, my)
            
            docking_supported = self.l.docking_supported

            # Dock Button Variables
            if not docking_supported:
                 btn_text = "FLOATING MODE"
                 btn_color = (60, 60, 60)
                 text_color = (150, 150, 150)
            else:
                 btn_text = "DOCK  WINDOWS" if not self.l.docked else "UNDOCK  WINDOWS"
                 btn_color = self.colors["panel"]
                 text_color = self.colors["text"]

            # Draw Dock Button
            pygame.draw.rect(self.screen, btn_color, undock_btn, border_radius=5)
            utxt = self.font_md.render(btn_text, True, text_color)
            text_rect = utxt.get_rect(center=undock_btn.center)
            self.screen.blit(utxt, text_rect)

            # Dock Button Interaction
            if m_click and u_hover and not self.m_locked and not self.dragging:
                self.pressed_button = "dock"

            if not m_click and self.pressed_button == "dock":
                if u_hover:
                    if not docking_supported:
                        self.show_status("Docking unavailable (no X11)", "info")
                    else:
                        self.l.toggle_dock()
                self.pressed_button = None

            # Screenshot button
            ss_btn = pygame.Rect(SCREENSHOT_BUTTON_X, SCREENSHOT_BUTTON_Y, SCREENSHOT_BUTTON_WIDTH, SCREENSHOT_BUTTON_HEIGHT)
            ss_hover = ss_btn.collidepoint(mx, my)

            # On Linux, ADB screencap works regardless of dock state — only needs a device.
            # On Windows, GDI capture requires the windows to be docked.
            if sys.platform == "win32":
                ss_available = self.l.docked
            else:
                ss_available = bool(self.l.scrcpy.serial)

            # Determine styling
            if not ss_available:
                 if sys.platform == "win32":
                     ss_text = "LOCKED (UNDOCKED)"
                 else:
                     ss_text = "NO DEVICE"
                 ss_color = (45, 48, 56)
                 ss_text_col = (100, 105, 115)
            else:
                 ss_text = "SCREENSHOT"
                 ss_color = self.colors["panel"]
                 ss_text_col = self.colors["text"]
                 if ss_hover:
                      ss_color = self.colors["border"]

            pygame.draw.rect(self.screen, ss_color, ss_btn, border_radius=5)
            ss_txt = self.font_md.render(ss_text, True, ss_text_col)
            ss_rect = ss_txt.get_rect(center=ss_btn.center)
            self.screen.blit(ss_txt, ss_rect)

            # Interaction
            can_click = ss_available
            
            if m_click and ss_hover and not self.m_locked and not self.dragging and can_click:
                 self.pressed_button = "screenshot"
                 
            if not m_click and self.pressed_button == "screenshot":
                if ss_hover and can_click:
                    self.take_screenshot()
                self.pressed_button = None
                
            # Wireless Connect Button with Scan
            wireless_btn = pygame.Rect(WIRELESS_BUTTON_X, WIRELESS_BUTTON_Y, WIRELESS_BUTTON_WIDTH, WIRELESS_BUTTON_HEIGHT)
            w_hover = wireless_btn.collidepoint(mx, my)
            
            # Check states
            dialog_open = hasattr(self.l, '_dialog_thread') and self.l._dialog_thread.is_alive()
            scanning = getattr(self.l, '_scanning', False)
            
            # Button color - pulsate when scanning or dialog is open
            if scanning or dialog_open:
                # Pulsating effect
                pulse = abs((time.time() * 3) % 2 - 1)
                w_color = (
                    int(self.colors["accent"][0] * pulse + self.colors["panel"][0] * (1 - pulse)),
                    int(self.colors["accent"][1] * pulse + self.colors["panel"][1] * (1 - pulse)),
                    int(self.colors["accent"][2] * pulse + self.colors["panel"][2] * (1 - pulse)),
                )
            elif self.l.scrcpy.connection_mode == 'wireless' and self.l.scrcpy.serial:
                w_color = self.colors["success"] if not w_hover else tuple(min(c + 25, 255) for c in self.colors["success"])
            elif w_hover:
                w_color = self.colors["accent"]
            else:
                w_color = self.colors["panel"]
            
            pygame.draw.rect(self.screen, w_color, wireless_btn, border_radius=5)
            
            # Button text based on state
            if scanning:
                w_text = "SCANNING..."
                w_text_col = self.colors["text"]
            elif dialog_open:
                w_text = "OPENING..."
                w_text_col = self.colors["text"]
            elif self.l.scrcpy.serial:
                w_text = "WIRELESS" if self.l.scrcpy.connection_mode == 'wireless' else "USB CONNECTED"
                w_text_col = WHITE_TEXT
            else:
                w_text = "CONNECT"
                w_text_col = self.colors["text"]
            
            w_txt = self.font_md.render(w_text, True, w_text_col)
            w_rect = w_txt.get_rect(center=wireless_btn.center)
            self.screen.blit(w_txt, w_rect)
            
            # Show scan results or status below button
            has_results = hasattr(self.l, '_scan_results') and self.l._scan_results is not None
            results = getattr(self.l, '_scan_results', None)
            
            if scanning:
                progress = getattr(self.l, '_scan_progress', 'Scanning...')
                status_txt = self.font_sm.render(progress, True, self.colors["warning"])
                self.screen.blit(status_txt, (WIRELESS_BUTTON_X, WIRELESS_BUTTON_Y + WIRELESS_BUTTON_HEIGHT + 3))
            elif has_results and results and not self.l.scrcpy.serial:
                # Show found devices
                devices = results
                if devices and len(devices) > 0:
                    devices_text = f"Found: {', '.join(devices)}"
                    if len(devices_text) > 35:
                        devices_text = devices_text[:32] + "..."
                    found_txt = self.font_sm.render(devices_text, True, self.colors["success"])
                    self.screen.blit(found_txt, (WIRELESS_BUTTON_X, WIRELESS_BUTTON_Y + WIRELESS_BUTTON_HEIGHT + 3))
                else:
                    # Empty results
                    status_txt = self.font_sm.render("Scan complete - no devices", True, self.colors["warning"])
                    self.screen.blit(status_txt, (WIRELESS_BUTTON_X, WIRELESS_BUTTON_Y + WIRELESS_BUTTON_HEIGHT + 3))
            elif has_results and results and len(results) == 0 and not self.l.scrcpy.serial:
                # Scan complete but no devices found
                status_txt = self.font_sm.render("No devices found", True, self.colors["warning"])
                self.screen.blit(status_txt, (WIRELESS_BUTTON_X, WIRELESS_BUTTON_Y + WIRELESS_BUTTON_HEIGHT + 3))
            elif dialog_open:
                status_txt = self.font_sm.render("Wireless dialog opening...", True, self.colors["warning"])
                self.screen.blit(status_txt, (WIRELESS_BUTTON_X, WIRELESS_BUTTON_Y + WIRELESS_BUTTON_HEIGHT + 3))
            
            # Wireless Button Interaction
            can_click = not scanning and not dialog_open
            if can_click and m_click and w_hover and not self.m_locked and not self.dragging:
                self.pressed_button = "wireless"
                
            if not m_click and self.pressed_button == "wireless":
                if w_hover and can_click:
                    # Open wireless connection dialog
                    self.l.show_wireless_connection_dialog()
                    self.show_status("Opening wireless connection dialog...", "info", 2.0)
                self.pressed_button = None
            
            # Scan Button
            scan_btn = pygame.Rect(SCAN_BUTTON_X, SCAN_BUTTON_Y, SCAN_BUTTON_WIDTH, SCAN_BUTTON_HEIGHT)
            scan_hover = scan_btn.collidepoint(mx, my)
            
            if scanning:
                pulse = abs((time.time() * 4) % 2 - 1)
                scan_color = (
                    int(self.colors["warning"][0] * pulse + self.colors["panel"][0] * (1 - pulse)),
                    int(self.colors["warning"][1] * pulse + self.colors["panel"][1] * (1 - pulse)),
                    int(self.colors["warning"][2] * pulse + self.colors["panel"][2] * (1 - pulse)),
                )
            elif scan_hover:
                scan_color = self.colors["warning"]
            else:
                scan_color = self.colors["panel"]
            
            pygame.draw.rect(self.screen, scan_color, scan_btn, border_radius=5)
            
            scan_txt = self.font_sm.render("SCAN" if not scanning else "...", True, self.colors["text"])
            scan_txt_rect = scan_txt.get_rect(center=scan_btn.center)
            self.screen.blit(scan_txt, scan_txt_rect)
            
            # Check connection state
            is_connected = self.l.scrcpy.serial and self.l.scrcpy.connection_mode == 'wireless'
            
            # Scan Button Interaction (only when not connected)
            if not is_connected:
                if not scanning and not dialog_open and m_click and scan_hover and not self.m_locked:
                    self.pressed_button = "scan"
                    self.m_locked = True
                
                if self.pressed_button == "scan" and not m_click:
                    if scan_hover and not scanning and not dialog_open:
                        if self.l.scan_for_devices():
                            self.show_status("Scanning network for devices...", "info", 3.0)
                    self.pressed_button = None
            
            # Disconnect Button (shown when connected wirelessly)
            if is_connected:
                # Draw over scan button area
                disc_btn = pygame.Rect(DISCONNECT_BUTTON_X, DISCONNECT_BUTTON_Y, DISCONNECT_BUTTON_WIDTH, DISCONNECT_BUTTON_HEIGHT)
                disc_hover = disc_btn.collidepoint(mx, my)
                disc_color = self.colors["danger"] if disc_hover else (80, 40, 40)
                pygame.draw.rect(self.screen, disc_color, disc_btn, border_radius=5)
                
                disc_txt = self.font_sm.render("X", True, WHITE_TEXT)
                disc_txt_rect = disc_txt.get_rect(center=disc_btn.center)
                self.screen.blit(disc_txt, disc_txt_rect)
                
                # Tooltip
                if disc_hover:
                    tooltip = self.font_sm.render("Disconnect", True, self.colors["text"])
                    self.screen.blit(tooltip, (DISCONNECT_BUTTON_X - 20, DISCONNECT_BUTTON_Y - 20))
                
                # Disconnect Button Interaction
                if m_click and disc_hover and not self.m_locked:
                    self.pressed_button = "disconnect"
                    self.m_locked = True
                
                if self.pressed_button == "disconnect" and not m_click:
                    if disc_hover:
                        # Stop scrcpy processes and reset dock state first
                        if self.l.scrcpy.processes:
                            self.l.scrcpy.stop()
                            with self.l.dock_lock:
                                self.l.docked = False
                                self.l.dock.hwnd_top = None
                                self.l.dock.hwnd_bottom = None
                                self.l._top_docked = False
                                self.l._bottom_docked = False
                        # Destroy the container window immediately on disconnect
                        if self.l.hwnd_container:
                            self.l.dock.destroy_container(self.l.hwnd_container)
                            self.l.hwnd_container = None
                        # Then disconnect wireless ADB
                        if self.l.scrcpy.disconnect_wireless():
                            self.show_status("Disconnected", "success", 2.0)
                        else:
                            self.show_status("Disconnect failed", "error", 2.0)
                    self.pressed_button = None
            
            # Quick IP Connect Section
            # Label
            self.screen.blit(
                self.font_sm.render("Quick IP:", True, self.colors["text"]),
                (QUICK_IP_X, QUICK_IP_Y - 18)
            )
            
            # IP Input Box
            ip_rect = pygame.Rect(QUICK_IP_X, QUICK_IP_Y, QUICK_IP_WIDTH, QUICK_IP_HEIGHT)
            ip_hover = ip_rect.collidepoint(mx, my)
            ip_active = self.active_quick_ip
            
            ip_color = (
                self.colors["accent"] if ip_active
                else (self.colors["border"] if ip_hover else self.colors["panel"])
            )
            pygame.draw.rect(self.screen, ip_color, ip_rect, border_radius=3)
            
            # IP Text
            if self.active_quick_ip:
                # Check if text is selected (Ctrl+A)
                has_selection = (self.quick_ip_selection_start != self.quick_ip_selection_end) and len(self.input_buffer) > 0
                
                if has_selection:
                    # Show selected text with different background
                    ip_text = self.input_buffer
                    # Draw highlight background for selected text
                    text_width = self.font_sm.size(self.input_buffer)[0]
                    highlight_rect = pygame.Rect(QUICK_IP_X + 8, QUICK_IP_Y + 5, text_width + 4, 20)
                    pygame.draw.rect(self.screen, (60, 80, 120), highlight_rect, border_radius=2)
                else:
                    ip_text = self.input_buffer + "|"  # Cursor anzeigen
                ip_txt_col = self.colors["text"]
            elif self.quick_ip:
                ip_text = self.quick_ip
                ip_txt_col = self.colors["text"]
            else:
                ip_text = "192.168.x.x:5555"
                ip_txt_col = (100, 100, 100)
            
            ip_txt = self.font_sm.render(ip_text, True, ip_txt_col)
            self.screen.blit(ip_txt, (QUICK_IP_X + 8, QUICK_IP_Y + 8))
            
            # Paste Button (small icon button next to input)
            paste_btn = pygame.Rect(QUICK_IP_X + QUICK_IP_WIDTH - 30, QUICK_IP_Y + 5, 25, 25)
            paste_hover = paste_btn.collidepoint(mx, my)
            paste_color = self.colors["accent"] if paste_hover else self.colors["border"]
            pygame.draw.rect(self.screen, paste_color, paste_btn, border_radius=2)
            paste_txt = self.font_sm.render("P", True, self.colors["text"])
            paste_txt_rect = paste_txt.get_rect(center=paste_btn.center)
            self.screen.blit(paste_txt, paste_txt_rect)
            
            # Paste Button Click
            if m_click and paste_hover and not self.m_locked:
                # Try to paste
                try:
                    import subprocess
                    clipboard = ""
                    try:
                        result = subprocess.run(['wl-paste'], capture_output=True, text=True, timeout=0.5)
                        if result.returncode == 0:
                            clipboard = result.stdout.strip()
                    except Exception:
                        try:
                            result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], capture_output=True, text=True, timeout=0.5)
                            if result.returncode == 0:
                                clipboard = result.stdout.strip()
                        except Exception:
                            pass
                    
                    if clipboard:
                        filtered = ''.join(c for c in clipboard if c.isdigit() or c in '.:')[:21]
                        if filtered:
                            self.input_buffer = filtered
                            self.active_quick_ip = True
                            self.show_status(f"Pasted: {filtered}", "info", 1.0)
                        else:
                            self.show_status("Invalid clipboard content", "warning", 1.0)
                    else:
                        self.show_status("Install wl-clipboard or xclip for paste", "warning", 3.0)
                except Exception as e:
                    self.show_status("Paste failed", "error", 1.0)
            
            # Activate input on click (deactivation is handled at top of render)
            if m_click and ip_hover and not self.m_locked and not ip_active:
                self.active_quick_ip = True
                self.input_buffer = self.quick_ip if self.quick_ip else ""
                self.active_input = False  # Deactivate preset input
                self.active_slider_input = None
                self.show_status("Enter IP:Port and press Enter", "info", 2.0)
                self.m_locked = True
            
            # Quick Connect Button
            qc_btn = pygame.Rect(QUICK_CONNECT_BTN_X, QUICK_CONNECT_BTN_Y, QUICK_CONNECT_BTN_WIDTH, QUICK_CONNECT_BTN_HEIGHT)
            qc_hover = qc_btn.collidepoint(mx, my)
            
            # Check if connecting
            is_connecting = hasattr(self.l, '_quick_connecting') and self.l._quick_connecting
            
            if is_connecting:
                # Pulsating effect
                pulse = abs((time.time() * 4) % 2 - 1)
                qc_color = (
                    int(self.colors["success"][0] * pulse + self.colors["panel"][0] * (1 - pulse)),
                    int(self.colors["success"][1] * pulse + self.colors["panel"][1] * (1 - pulse)),
                    int(self.colors["success"][2] * pulse + self.colors["panel"][2] * (1 - pulse)),
                )
            elif qc_hover:
                qc_color = self.colors["success"]
            else:
                qc_color = self.colors["panel"]
            
            pygame.draw.rect(self.screen, qc_color, qc_btn, border_radius=3)
            
            qc_text = "CONN..." if is_connecting else "CONNECT"
            qc_txt = self.font_sm.render(qc_text, True, self.colors["text"])
            qc_txt_rect = qc_txt.get_rect(center=qc_btn.center)
            self.screen.blit(qc_txt, qc_txt_rect)
            
            # Quick Connect Button Interaction
            if not is_connecting and m_click and qc_hover and not self.m_locked and not self.dragging:
                self.pressed_button = "quick_connect"
            
            if not m_click and self.pressed_button == "quick_connect":
                if qc_hover and not is_connecting:
                    # Use input_buffer if field is active, otherwise use saved quick_ip
                    if self.active_quick_ip:
                        ip_port = self.input_buffer.strip()
                    else:
                        ip_port = self.quick_ip.strip()
                    
                    if ip_port:
                        # Save the IP for future use
                        self.quick_ip = ip_port
                        self._save_quick_ip(ip_port)
                        self.l.quick_connect_wireless(ip_port)
                        self.show_status(f"Connecting to {ip_port}...", "info", 3.0)
                    else:
                        self.show_status("Please enter IP:Port", "warning", 2.0)
                self.pressed_button = None
            
            # Files Button
            files_btn = pygame.Rect(FILES_BUTTON_X, FILES_BUTTON_Y,
                                    FILES_BUTTON_WIDTH, FILES_BUTTON_HEIGHT)
            fb_hover = files_btn.collidepoint(mx, my)
            fb_has_device = bool(self.l.scrcpy.serial and self.l.scrcpy.adb_bin)
            if not fb_has_device:
                fb_color    = (45, 48, 56)
                fb_text_col = (100, 105, 115)
                fb_label    = "FILES (no device)"
            elif fb_hover:
                fb_color    = self.colors["accent"]
                fb_text_col = WHITE_TEXT
                fb_label    = "FILE BROWSER"
            else:
                fb_color    = self.colors["panel"]
                fb_text_col = self.colors["text"]
                fb_label    = "FILE BROWSER"
            pygame.draw.rect(self.screen, fb_color, files_btn, border_radius=5)
            fb_txt = self.font_md.render(fb_label, True, fb_text_col)
            self.screen.blit(fb_txt, fb_txt.get_rect(center=files_btn.center))

            if fb_has_device and m_click and fb_hover and not self.m_locked and not self.dragging:
                self.pressed_button = "filebrowser"
            if not m_click and self.pressed_button == "filebrowser":
                if fb_hover and fb_has_device:
                    self._fb_open()
                self.pressed_button = None

            # Status Messages
            if time.time() - self.status_time < self.status_duration:
                color_map = {
                    "success": self.colors["success"],
                    "error": self.colors["danger"],
                    "warning": self.colors["warning"],
                    "info": self.colors["text"],
                }
                msg_txt = self.font_md.render(
                    self.status_msg, True, color_map.get(self.status_type, self.colors["text"])
                )
                msg_rect = msg_txt.get_rect(center=(STATUS_TEXT_X, STATUS_TEXT_Y))
                self.screen.blit(msg_txt, msg_rect)

            # Preset Section Divider
            pygame.draw.line(self.screen, self.colors["border"], (PRESET_DIVIDER_LEFT, PRESET_DIVIDER_Y),
                             (PRESET_DIVIDER_RIGHT, PRESET_DIVIDER_Y))

            # Preset Header
            self.screen.blit(
                self.font_lg.render("Presets", True, self.colors["text"]),
                (PRESET_HEADER_X, PRESET_HEADER_Y),
            )
            pygame.draw.line(self.screen, self.colors["border"],
                             (PRESET_DIVIDER_LEFT, PRESET_INPUT_DIVIDER_Y),
                             (PRESET_DIVIDER_RIGHT, PRESET_INPUT_DIVIDER_Y))

            # Preset Input
            input_rect = pygame.Rect(PRESET_INPUT_X, PRESET_Y, PRESET_INPUT_WIDTH, PRESET_HEIGHT)
            input_hover = input_rect.collidepoint(mx, my)

            input_color = (
                self.colors["accent"]
                if self.active_input
                else (self.colors["border"] if input_hover else self.colors["panel"])
            )
            pygame.draw.rect(self.screen, input_color, input_rect, border_radius=PRESET_BORDER_RADIUS)

            # Draw input text
            txt_surf = self.font_md.render(self.preset_name, True, self.colors["text"])
            self.screen.blit(txt_surf, (PRESET_INPUT_X + PRESET_TEXT_PADDING_X, PRESET_Y + 7))

            # Input activation
            if m_click and input_hover and not self.m_locked:
                self.active_input = True
                self.active_slider_input = None
                self.m_locked = True
                logger.debug("Activated preset input field")
            elif m_click and not input_hover and not self.m_locked:
                # If clicking outside, deactivate
                 if self.active_input:
                     logger.debug("Deactivated preset input field")
                 self.active_input = False


            # Save Button
            save_btn = pygame.Rect(PRESET_SAVE_BUTTON_X, PRESET_Y, PRESET_SAVE_BUTTON_WIDTH, PRESET_HEIGHT)
            save_hover = save_btn.collidepoint(mx, my)

            s_btn_color = self.colors["panel"] if not save_hover else self.colors["accent"]
            pygame.draw.rect(self.screen, s_btn_color, save_btn, border_radius=PRESET_BORDER_RADIUS)
            
            save_txt = self.font_md.render("SAVE", True, self.colors["text"])
            save_rect = save_txt.get_rect(center=save_btn.center)
            self.screen.blit(save_txt, save_rect)

            if m_click and save_hover and not self.m_locked:
                if self.preset_name:
                    logger.info(f"Saving preset: {self.preset_name}")
                    if self.l.store.save(self.preset_name, {
                        "tx": self.l.tx, "ty": self.l.ty,
                        "bx": self.l.bx, "by": self.l.by,
                        "global_scale": self.l.global_scale
                    }):
                        self.show_status(f"Saved: {self.preset_name}", "success")
                        self.invalidate_preset_cache()
                    else:
                        self.show_status("Save failed", "error")
                self.m_locked = True


            # Preset List Header
            self.screen.blit(
                self.font_lg.render("Saved Layouts:", True, self.colors["text"]),
                (PRESET_LIST_HEADER_X, PRESET_LIST_HEADER_Y),
            )

            # Render Presets List
            presets = self.get_presets()
            y_off = PRESET_LIST_Y_OFFSET

            if not presets:
                no_pre_txt = self.font_md.render("No presets found", True, self.colors["text"])
                self.screen.blit(no_pre_txt, (PRESET_ROW_X, y_off))
            else:
                for name, data in presets.items():
                    # Draw Row Background
                    row_rect = pygame.Rect(PRESET_ROW_X, y_off, PRESET_ROW_WIDTH, PRESET_ROW_HEIGHT)
                    row_hover = row_rect.collidepoint(mx, my)
                    
                    if row_hover:
                         pygame.draw.rect(self.screen, self.colors["border"], row_rect, border_radius=BUTTON_BORDER_RADIUS)

                    # Draw Name
                    name_txt = self.font_md.render(name, True, self.colors["text"])
                    self.screen.blit(name_txt, (PRESET_ROW_X + PRESET_NAME_X_OFFSET, y_off + 10))

                    # Load Button
                    load_btn = pygame.Rect(PRESET_LOAD_BUTTON_X, y_off + PRESET_BUTTON_Y_OFFSET, 
                                           PRESET_BUTTON_WIDTH, PRESET_BUTTON_HEIGHT)
                    l_hover = load_btn.collidepoint(mx, my)
                    l_color = self.colors["panel"] if not l_hover else self.colors["success"]
                    
                    pygame.draw.rect(self.screen, l_color, load_btn, border_radius=BUTTON_BORDER_RADIUS)
                    l_txt = self.font_sm.render("LOAD", True, self.colors["text"])
                    l_rect = l_txt.get_rect(center=load_btn.center)
                    self.screen.blit(l_txt, l_rect)

                    if m_click and l_hover and not self.m_locked:
                        logger.info(f"Loading preset: {name}")
                        self.l.tx = data.get("tx", 0)
                        self.l.ty = data.get("ty", 0)
                        self.l.bx = data.get("bx", 0)
                        self.l.by = data.get("by", 0)
                        
                        # Handle old presets without scale
                        if "global_scale" in data:
                             self.l.global_scale = data["global_scale"]
                             
                        self.show_status(f"Loaded: {name}", "success")
                        self.m_locked = True


                    # Delete Button
                    del_btn = pygame.Rect(PRESET_DELETE_BUTTON_X, y_off + PRESET_BUTTON_Y_OFFSET,
                                          PRESET_BUTTON_WIDTH, PRESET_BUTTON_HEIGHT)
                    d_hover = del_btn.collidepoint(mx, my)
                    d_color = self.colors["panel"] if not d_hover else self.colors["danger"]

                    pygame.draw.rect(self.screen, d_color, del_btn, border_radius=BUTTON_BORDER_RADIUS)
                    d_txt = self.font_sm.render("DEL", True, self.colors["text"])
                    d_rect = d_txt.get_rect(center=del_btn.center)
                    self.screen.blit(d_txt, d_rect)

                    if m_click and d_hover and not self.m_locked:
                        logger.info(f"Deleting preset: {name}")
                        if self.l.store.delete(name):
                             self.show_status(f"Deleted: {name}", "success")
                             self.invalidate_preset_cache()
                        else:
                             self.show_status("Delete failed", "error")
                        self.m_locked = True

                    y_off += PRESET_ROW_SPACING


            # Reset mouse lock
            if not m_click:
                self.m_locked = False

            # Display Updates
            pygame.display.flip()

        except Exception as RenderError:
            logger.error(f"Render Loop Error: {RenderError}", exc_info=True)

    def draw_layout_buttons(self):
        """
        Draws the layout switching buttons.
        """
        mx, my = pygame.mouse.get_pos()
        m_click = pygame.mouse.get_pressed()[0]
        
        # Define buttons: (Label, Mode)
        buttons = [
            ("TOP", "TOP"),
            ("DUAL (1|2)", "DUAL"),
            ("BOTTOM", "BOTTOM") 
        ]
        
        start_x = 20
        
        for i, (label, mode) in enumerate(buttons):
            x = start_x + (i * LAYOUT_BTN_SPACING)
            btn_rect = pygame.Rect(x, LAYOUT_BTN_Y, LAYOUT_BTN_WIDTH, LAYOUT_BTN_HEIGHT)
            
            is_hover = btn_rect.collidepoint(mx, my)
            is_active = (self.l.layout_mode == mode)
            
            # Color logic
            if is_active:
                color = self.colors["accent"]
                text_col = BLACK_TEXT
            elif is_hover:
                color = self.colors["text"]
                text_col = BLACK_TEXT
            else:
                color = self.colors["panel"]
                text_col = self.colors["text"]
                
            pygame.draw.rect(self.screen, color, btn_rect, border_radius=BUTTON_BORDER_RADIUS)
            
            txt_surf = self.font_sm.render(label, True, text_col)
            txt_rect = txt_surf.get_rect(center=btn_rect.center)
            self.screen.blit(txt_surf, txt_rect)
            
            # Interaction
            if m_click and is_hover and not self.m_locked:
                 self.pressed_button = f"layout_{mode}"
                 
            if not m_click and self.pressed_button == f"layout_{mode}":
                 if is_hover:
                     self.l.set_layout_mode(mode)
                 self.pressed_button = None

    def handle_event(self, event):
        """
        Handle pygame events (keyboard entry)

        Args:
            event: Pygame event object
        """
        # File browser: Escape to close, mouse wheel to scroll panels
        if self.show_filebrowser:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.show_filebrowser = False
            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                visible_rows = (FB_LIST_BOTTOM - FB_LIST_TOP) // FB_ROW_H
                if mx < FB_DIVIDER_X:
                    # Left (device) panel
                    self.fb_device_scroll = max(
                        0, min(self.fb_device_scroll - event.y,
                               max(0, len(self.fb_device_entries) - visible_rows))
                    )
                else:
                    # Right (local) panel
                    self.fb_local_scroll = max(
                        0, min(self.fb_local_scroll - event.y,
                               max(0, len(self.fb_local_entries) - visible_rows))
                    )
            return

        # If settings are open, block most main UI events
        if self.show_settings:
            return

        # Route keyboard to wireless overlay fields
        if self.show_wireless:
            if event.type == pygame.KEYDOWN and self.wireless_active_field is not None:
                field = self.wireless_active_field
                _order = (
                    ["connect_ip", "connect_port"]
                    if self.wireless_tab == "connect"
                    else ["pair_ip", "pair_port", "pair_code"]
                )
                _allowed = {
                    "connect_ip":   lambda c: c.isdigit() or c == ".",
                    "connect_port": lambda c: c.isdigit(),
                    "pair_ip":      lambda c: c.isdigit() or c == ".",
                    "pair_port":    lambda c: c.isdigit(),
                    "pair_code":    lambda c: c.isdigit(),
                }
                _maxlen = {
                    "connect_ip": 15, "connect_port": 5,
                    "pair_ip": 15,    "pair_port": 5, "pair_code": 6,
                }
                if event.key in (pygame.K_RETURN, pygame.K_TAB):
                    if field in _order and _order.index(field) + 1 < len(_order):
                        self.wireless_active_field = _order[_order.index(field) + 1]
                    else:
                        self.wireless_active_field = None
                elif event.key == pygame.K_ESCAPE:
                    self.wireless_active_field = None
                elif event.key == pygame.K_BACKSPACE:
                    self.wireless_fields[field] = self.wireless_fields[field][:-1]
                else:
                    allowed_fn = _allowed.get(field, lambda c: True)
                    max_l = _maxlen.get(field, 20)
                    if event.unicode and allowed_fn(event.unicode) and len(self.wireless_fields[field]) < max_l:
                        self.wireless_fields[field] += event.unicode
            return

        # Track Ctrl key state for shortcuts
        ctrl_pressed = pygame.key.get_mods() & (pygame.KMOD_CTRL | pygame.KMOD_LCTRL | pygame.KMOD_RCTRL)
        
        if event.type == pygame.KEYDOWN:
            # Handle Quick IP input
            if self.active_quick_ip:
                if event.key == pygame.K_RETURN:
                    # Save and connect
                    self.quick_ip = self.input_buffer
                    self.active_quick_ip = False
                    self.quick_ip_selection_start = 0
                    self.quick_ip_selection_end = 0
                    self._save_quick_ip(self.quick_ip)
                    # Trigger connection
                    if self.quick_ip.strip():
                        self.l.quick_connect_wireless(self.quick_ip.strip())
                        self.show_status(f"Connecting to {self.quick_ip}...", "info", 3.0)
                elif event.key == pygame.K_ESCAPE:
                    self.active_quick_ip = False
                    self.input_buffer = ""
                    self.quick_ip_selection_start = 0
                    self.quick_ip_selection_end = 0
                elif ctrl_pressed and event.key == pygame.K_a:
                    # Select all (Ctrl+A) - just reset cursor to show we "selected"
                    self.quick_ip_selection_start = 0
                    self.quick_ip_selection_end = len(self.input_buffer)
                    self.show_status("Text selected (Ctrl+A)", "info", 0.5)
                elif ctrl_pressed and event.key == pygame.K_c:
                    # Copy (Ctrl+C) - would need clipboard integration
                    pass
                elif ctrl_pressed and event.key == pygame.K_v:
                    # Paste (Ctrl+V) - paste from clipboard
                    try:
                        clipboard = ""
                        # Try different clipboard methods
                        if sys.platform == "linux":
                            # Try wl-copy/wl-paste for Wayland, xclip for X11
                            import subprocess
                            try:
                                # Try wl-paste first (Wayland)
                                result = subprocess.run(['wl-paste'], capture_output=True, text=True, timeout=0.5)
                                if result.returncode == 0:
                                    clipboard = result.stdout
                            except Exception:
                                try:
                                    # Fallback to xclip (X11)
                                    result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], capture_output=True, text=True, timeout=0.5)
                                    if result.returncode == 0:
                                        clipboard = result.stdout
                                except Exception:
                                    pass
                        else:
                            # Windows/Mac - use tkinter
                            import tkinter as tk
                            root = tk.Tk()
                            root.withdraw()
                            clipboard = root.clipboard_get()
                            root.destroy()
                        
                        # Debug: Show what we got
                        print(f"[CLIPBOARD] Raw: '{clipboard}'")
                        
                        # Strip whitespace and newlines first
                        clipboard = clipboard.strip()
                        
                        # Filter valid chars only (digits, dots, colons)
                        filtered = ''.join(c for c in clipboard if c.isdigit() or c in '.:')[:21]
                        
                        print(f"[CLIPBOARD] Filtered: '{filtered}'")
                        
                        if filtered:
                            self.input_buffer = filtered
                            self.show_status(f"Pasted: {filtered}", "info", 1.0)
                        else:
                            self.show_status(f"Clipboard invalid: '{clipboard[:20]}...'", "warning", 2.0)
                    except Exception as e:
                        logger.warning(f"Paste failed: {e}")
                        print(f"[CLIPBOARD] Error: {e}")
                        self.show_status("Paste failed", "error", 1.0)
                elif event.key == pygame.K_BACKSPACE:
                    if self.quick_ip_selection_start != self.quick_ip_selection_end:
                        # Delete selection
                        self.input_buffer = ""
                        self.quick_ip_selection_start = 0
                        self.quick_ip_selection_end = 0
                    else:
                        self.input_buffer = self.input_buffer[:-1]
                elif event.key == pygame.K_DELETE:
                    self.input_buffer = ""
                else:
                    # Allow IP:port format (digits, dots, colon)
                    if len(self.input_buffer) < 21 and (event.unicode.isdigit() or event.unicode in '.:'):
                        # If text is "selected", replace it
                        if self.quick_ip_selection_start != self.quick_ip_selection_end:
                            self.input_buffer = event.unicode
                            self.quick_ip_selection_start = 0
                            self.quick_ip_selection_end = 0
                        else:
                            self.input_buffer += event.unicode

            # Handle preset name input
            elif self.active_input:
                if event.key == pygame.K_RETURN:
                    self.active_input = False
                    logger.debug(f"Finished preset input: {self.preset_name}")
                elif event.key == pygame.K_BACKSPACE:
                    self.preset_name = self.preset_name[:-1]
                else:
                    # Limit length
                    if len(self.preset_name) < 20: 
                        self.preset_name += event.unicode

            # Handle slider value input
            elif self.active_slider_input:
                if event.key == pygame.K_RETURN:
                     try:
                         val = float(self.input_buffer)
                         setattr(self.l, self.active_slider_input, val)
                         logger.debug(f"Applied slider input val {val} to {self.active_slider_input}")
                         
                         if self.active_slider_input == "global_scale":
                             self.l.save_scale()
                             self._scale_changed = True
                         else:
                             self.l.save_layout()
                             
                     except ValueError:
                         logger.warning(f"Invalid slider input: {self.input_buffer}")
                         self.show_status("Invalid number", "error", SLIDER_ERROR_STATUS_DURATION)
                     
                     self.active_slider_input = None
                     self.input_buffer = ""

                elif event.key == pygame.K_BACKSPACE:
                    self.input_buffer = self.input_buffer[:-1]
                elif event.key == pygame.K_ESCAPE:
                    self.active_slider_input = None
                    self.input_buffer = ""
                else:
                    # Allow digits, minus, and dot
                    if event.unicode.isdigit() or event.unicode in ".-":
                        if len(self.input_buffer) < 8:
                            self.input_buffer += event.unicode
