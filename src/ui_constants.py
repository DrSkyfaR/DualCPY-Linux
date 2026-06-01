# ThorCPY Linux - Dual-screen scrcpy docking and control UI
# Copyright (C) 2026 the_swest
# Contact: Github issues
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# src/ui_constants.py

import os
import sys
import logging
import tkinter as tk
import customtkinter as ctk

logger = logging.getLogger(__name__)

# Colours
BG_COLOUR      = "#121418"
PANEL_COLOUR   = "#1e2128"
BORDER_COLOUR  = "#2d3139"
TEXT_COLOUR    = "#c8cdd8"
ACCENT_COLOUR  = "#4000D4"
ACCENT2_COLOUR = "#6A4BF4"
TOP_COLOUR     = "#A241ED"
BOTTOM_COLOUR  = "#936aad"
SUCCESS_COLOUR = "#2ecc71"
DANGER_COLOUR  = "#e74c3c"
WARNING_COLOUR = "#f39c12"

# Font / asset helpers
CALSANS_FAMILY = "Cal Sans"

# Tracks whether CalSans was successfully registered with the OS
_calsans_loaded = False


def resource_path(rel):
    """Resolve a resource path for both dev and PyInstaller contexts"""
    try:
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, rel)
        return os.path.join(os.path.abspath("."), rel)
    except Exception as e:
        logger.error(f"Failed to resolve resource path for '{rel}': {e}")
        return rel


ICON_PATH = resource_path("assets/icon.png")
FONT_PATH = resource_path("assets/fonts/CalSans-Regular.ttf")


def load_calsans():
    """Register CalSans-Regular with the OS.

    On Windows this uses GDI's AddFontResourceExW. On Linux/macOS the font would
    need to be installed system-wide; if it is not already available we simply
    fall back to customtkinter's default font (visually very close).
    """
    global _calsans_loaded
    if _calsans_loaded:
        return True

    if sys.platform == "win32":
        try:
            from ctypes import windll
            FR_PRIVATE = 0x10
            if windll.gdi32.AddFontResourceExW(FONT_PATH, FR_PRIVATE, 0) > 0:
                _calsans_loaded = True
                logger.info(f"CalSans loaded from {FONT_PATH}")
            else:
                logger.warning("AddFontResourceExW returned 0 - using CTK default font")
        except Exception as e:
            logger.warning(f"CalSans load failed: {e}: using CTK default font")
    else:
        # Use CalSans only if the system already has it; otherwise CTK default.
        try:
            import tkinter.font as tkfont
            if CALSANS_FAMILY in tkfont.families():
                _calsans_loaded = True
                logger.info("CalSans found among system fonts")
            else:
                logger.debug("CalSans not installed system-wide - using CTK default font")
        except Exception as e:
            logger.debug(f"Font enumeration failed: {e}: using CTK default font")

    return _calsans_loaded


def make_font(size, weight="normal"):
    """Return a CTkFont using CalSans if loaded, otherwise the CTK default"""
    if _calsans_loaded:
        return ctk.CTkFont(family=CALSANS_FAMILY, size=size, weight=weight)
    return ctk.CTkFont(size=size, weight=weight)


def apply_window_icon(window):
    """Apply the app icon to any CTk window or Toplevel"""
    try:
        img = tk.PhotoImage(file=ICON_PATH)
        window.iconphoto(True, img)
        window._icon_image = img
    except Exception:
        pass
