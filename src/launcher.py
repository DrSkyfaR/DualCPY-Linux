import threading
import time
import sys
import os
import logging

# Import signal flag from main module
try:
    import __main__ as main_module
except:
    main_module = None

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scrcpy_manager import (
    ScrcpyManager, TOP_SCREEN_WINDOW_TITLE, BOTTOM_SCREEN_WINDOW_TITLE, DEFAULT_MAX_FPS,
)
from src.presets import PresetStore
from src.config import ConfigManager
from src.custom_profile_store import CustomProfileStore
from src.device_profile import BUILTIN_PROFILES
from src.device_selector import show_device_selector

# Platform specific imports
if sys.platform == "win32":
    from src.win32_dock import Win32Dock as DockManagerImpl
    from src.win32_darkmode import enable_dark_titlebar
else:
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        if os.environ.get("DISPLAY"):
            # XWayland is present — force SDL to use X11 backend so both Pygame and
            # scrcpy (which inherits the env) render via XWayland. This enables
            # X11 window docking to work exactly as on a native X11 session.
            os.environ["SDL_VIDEODRIVER"] = "x11"
            print("[INFO] Wayland + XWayland detected. Forcing X11 backend for docking support.")
            from src.docking.x11 import X11DockManager as DockManagerImpl
        else:
            # Pure Wayland, no XWayland — window embedding not possible.
            print("[INFO] Pure Wayland detected (no XWayland). Using floating mode.")
            from src.docking.stateless import StatelessDockManager as DockManagerImpl
    else:
        from src.docking.x11 import X11DockManager as DockManagerImpl

    def enable_dark_titlebar(hwnd): pass

logger = logging.getLogger(__name__)

# Default layout positioning
TOP_SCREEN_DEFAULT_X = 0
TOP_SCREEN_DEFAULT_Y = 0
BOTTOM_SCREEN_DEFAULT_X = 0
BOTTOM_SCREEN_DEFAULT_Y = 0
DEFAULT_GLOBAL_SCALE = 0.6

# Container window initial position
DEFAULT_CONTAINER_X = 100
DEFAULT_CONTAINER_Y = 100

# Timing constants
SCRCPY_POLL_INTERVAL = 0.1
DOCKING_MONITOR_TIME_DELAY = 1.0 # Increased for Linux
UI_FPS = 60

# Selectable FPS caps offered in the control panel
ALLOWED_FPS_VALUES = (30, 60, 90, 120)

# Math constants
HALF = 0.5

# Default config
DEFAULT_LAYOUT = {"tx": TOP_SCREEN_DEFAULT_X, "ty": TOP_SCREEN_DEFAULT_Y,
                  "bx": BOTTOM_SCREEN_DEFAULT_X, "by": BOTTOM_SCREEN_DEFAULT_Y,
                  "global_scale": DEFAULT_GLOBAL_SCALE}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class LayoutMode:
    DUAL = "DUAL"
    TOP = "TOP"
    BOTTOM = "BOTTOM"


class Launcher:
    """
    Main window controller for ThorCPY
    Manages scrcpy instances, docking and undocking behabiour,
    UI rendering and event handling and configuration persistance
    """
    def __init__(self):
        """
        Sets up the launcher with default layouts and configurations
        Sets up scrcpy instance with saved scale
        forces the default layout on boot
        Manages windows docking
        """
        logger.info("Initializing Launcher")

        # Load config managers
        self.store = PresetStore("config/layout.json")
        self.config = ConfigManager("config/config.json")
        self.custom_profiles = CustomProfileStore("config/custom_profiles.json")

        # Load scale or use the default
        self.global_scale = self.config.get(
            "global_scale", DEFAULT_LAYOUT["global_scale"]
        )
        self.launch_scale = self.global_scale
        
        # Load layout mode
        self.layout_mode = self.config.get("layout_mode", LayoutMode.DUAL)
        logger.info(f"Initial Layout Mode: {self.layout_mode}")

        # Load swap screens preference
        self.swap_screens = self.config.get("swap_screens", False)
        logger.info(f"Swap Screens: {self.swap_screens}")

        # Load Discord audio routing preference (Linux only — harmless to store on any OS)
        discord_audio_routing = self.config.get("discord_audio_routing", True)

        # Load FPS cap preference (applies to the top window; bottom is capped to <=60)
        self.max_fps = int(self.config.get("max_fps", DEFAULT_MAX_FPS))
        logger.info(f"Max FPS: {self.max_fps}")

        # Initialize Scrcpy with the saved scale
        self.scrcpy = ScrcpyManager(scale=self.launch_scale,
                                    discord_audio_routing=discord_audio_routing,
                                    max_fps=self.max_fps)

        # Calculate the forced layout (Top at 0,0 - bottom centred underneath) with scaled dimensions
        w1, h1 = self.scrcpy.f_w1, self.scrcpy.f_h1
        w2, _ = self.scrcpy.f_w2, self.scrcpy.f_h2

        self.tx = TOP_SCREEN_DEFAULT_X
        self.ty = TOP_SCREEN_DEFAULT_Y
        self.by = int(h1)
        self.bx = int(w1 * HALF - w2 * HALF)

        logger.info(
            f"Layout Reset: Top(0,0), Bottom({self.bx}, {self.by}) at Scale {self.global_scale}"
        )

        # Initialise window management
        self.dock = DockManagerImpl()
        self.running = False
        self.docked = True
        self.hwnd_container = None
        self.dock_lock = threading.Lock()
        self._dock_monitor_stop = threading.Event()

        # Initialize on-demand attributes to avoid hasattr() race conditions
        self._dialog_connect_ip = None
        self._top_docked = False
        self._bottom_docked = False
        self._last_sync_params = None  # cache to skip redundant sync_layout calls
        self._scanning = False
        self._scan_results = []
        self._scan_progress = (0, 0)
        self._scan_thread = None
        self._quick_connecting = False
        self._quick_connect_thread = None

    def set_layout_mode(self, mode):
        """
        Updates the layout mode and resizes the container.
        """
        if mode not in [LayoutMode.DUAL, LayoutMode.TOP, LayoutMode.BOTTOM]:
            logger.warning(f"Invalid layout mode: {mode}")
            return
            
        logger.info(f"Switching layout mode to: {mode}")
        self.layout_mode = mode
        self._last_sync_params = None
        
        # Save preference
        self.config.set("layout_mode", self.layout_mode)
        
        # 1. Update Container Size
        if self.hwnd_container:
            self._update_container_size()
            
        # 2. Update Docking (Hide/Show windows)
        # We trigger a docking update by forcing a check in the monitor loop
        # But we also need to explicitly handle the visibility/docking state
        with self.dock_lock:
             # If we are switching modes, we might need to undock the window that is now hidden
             # or dock the one that is now visible.
             
             if mode == LayoutMode.TOP:
                 # Ensure Bottom is undocked/hidden
                 if self.dock.hwnd_bottom:
                     self.dock.undock_window(self.dock.hwnd_bottom)
                     self._bottom_docked = False

                 # Ensure Top is docked
                 if self.dock.hwnd_top and self.docked:
                     self.dock.dock_window(self.dock.hwnd_top, self.hwnd_container)
                     self._top_docked = True

             elif mode == LayoutMode.BOTTOM:
                 # Ensure Top is undocked/hidden
                 if self.dock.hwnd_top:
                     self.dock.undock_window(self.dock.hwnd_top)
                     self._top_docked = False

                 # Ensure Bottom is docked
                 if self.dock.hwnd_bottom and self.docked:
                     self.dock.dock_window(self.dock.hwnd_bottom, self.hwnd_container)
                     self._bottom_docked = True

             elif mode == LayoutMode.DUAL:
                 # Ensure Both are docked
                 if self.docked:
                     if self.dock.hwnd_top:
                         self.dock.dock_window(self.dock.hwnd_top, self.hwnd_container)
                         self._top_docked = True
                     if self.dock.hwnd_bottom:
                         self.dock.dock_window(self.dock.hwnd_bottom, self.hwnd_container)
                         self._bottom_docked = True

    def _update_container_size(self):
        """
        Resizes the container window based on current layout mode.
        """
        if not self.hwnd_container:
            return

        w1, h1 = self.scrcpy.f_w1, self.scrcpy.f_h1
        w2, h2 = self.scrcpy.f_w2, self.scrcpy.f_h2
        
        target_w = 0
        target_h = 0
        
        if self.layout_mode == LayoutMode.DUAL:
            target_w = max(w1, w2 + abs(self.bx))
            target_h = h1 + h2
        elif self.layout_mode == LayoutMode.TOP:
            target_w = w1
            target_h = h1
        elif self.layout_mode == LayoutMode.BOTTOM:
            target_w = w2
            target_h = h2
            
        logger.debug(f"Resizing container to {target_w}x{target_h} for mode {self.layout_mode}")
        
        # Use DockManager to resize if methods exist, otherwise we might need a generic method
        # The stateless dock manager controls the container size?
        # On Window, standard API. On Linux, X11 resize.
        
        # Since logic is platform specific, we might need to add `resize_container` to DockManager interface
        # For now, let's look at how container was created.
        
        # If Platform is Windows
        if sys.platform == "win32":
            import ctypes
            user32 = ctypes.windll.user32
            # SetWindowPos with SWP_NOMOVE | SWP_NOZORDER
            flags = 0x0002 | 0x0004 
            user32.SetWindowPos(self.hwnd_container, 0, 0, 0, int(target_w), int(target_h), flags)
            
        else: # Linux
            # Try to use the dock manager's implementation if available, or python-xlib directly
            if hasattr(self.dock, "resize_container"):
                self.dock.resize_container(self.hwnd_container, int(target_w), int(target_h))
            else:
                 # Fallback/Placeholder
                 logger.warning("Resize container not implemented for this platform/dock manager")


    def save_layout(self):
        """
        Saves current state and scale to config file
        Called during shutdown to keep settings
        """
        try:
            self.config.set("tx", self.tx)
            self.config.set("ty", self.ty)
            self.config.set("bx", self.bx)
            self.config.set("by", self.by)
            self.config.set("global_scale", self.global_scale)
            # layout_mode is saved instantly on change
            logger.info(f"Saved configuration (Scale: {self.global_scale})")
        except Exception as SaveConfigError:
            logger.error(f"Failed to save configuration: {SaveConfigError}")

    def save_scale(self):
        """Save only the global scale to config for when the scale changes in ui_pygame"""
        self.config.set("global_scale", self.global_scale)

    def _create_container_window(self):
        """
        Creates the main container window
        Handles both scrcpy windows as children
        """
        # Wait for the window dimensions
        while self.scrcpy.f_w1 == 0:
            time.sleep(SCRCPY_POLL_INTERVAL)
            if not self.running:
                return

        # Calculate container size to fit both stacked windows
        client_w = max(self.scrcpy.f_w1, self.scrcpy.f_w2 + abs(self.bx))
        client_h = self.scrcpy.f_h1 + self.scrcpy.f_h2
        
        # Check initial layout mode if we want to start in a specific mode, 
        # but defaulting to dual calculations for "max" size usually safer? 
        # Actually better to respect the mode from start.
        if self.layout_mode == LayoutMode.TOP:
            client_w = self.scrcpy.f_w1
            client_h = self.scrcpy.f_h1
        elif self.layout_mode == LayoutMode.BOTTOM:
             client_w = self.scrcpy.f_w2
             client_h = self.scrcpy.f_h2

        # Destroy the previous container if one exists (e.g. after reconnect)
        if self.hwnd_container:
            self.dock.destroy_container(self.hwnd_container)
            self.hwnd_container = None

        self.hwnd_container = self.dock.create_container(
            DEFAULT_CONTAINER_X, DEFAULT_CONTAINER_Y,
            int(client_w), int(client_h)
        )

        if self.hwnd_container:
            # Enable the dark titlebar if supported
            enable_dark_titlebar(self.hwnd_container)

    def _docking_monitor(self):
        """
        Background thread to continuously montor and dock windows.
        Searches for titles and automatically sets their parent to the container window and applies styling
        """
        while self.running and not self._dock_monitor_stop.is_set():
            if self._dock_monitor_stop.is_set():
                break
            with self.dock_lock:
                if self.hwnd_container and self.docked:
                    # Find scrcpy windows by their titles
                    # Note: We rely on the DockManager implementations to cache or efficiently find windows
                    
                    # TOP WINDOW
                    if not self.dock.hwnd_top:
                        top_id = self.dock.find_window(TOP_SCREEN_WINDOW_TITLE)
                        if top_id:
                            logger.info(f"Found Top Window: {top_id}")
                            self.dock.hwnd_top = top_id
                            self._top_docked = False  # New window — needs docking

                    # Dock once; don't re-reparent on every iteration (causes visual flicker on X11)
                    if self.dock.hwnd_top and not self._top_docked and self.layout_mode in [LayoutMode.DUAL, LayoutMode.TOP]:
                        self.dock.dock_window(self.dock.hwnd_top, self.hwnd_container)
                        self._top_docked = True
                        self._last_sync_params = None  # force position update after reparent

                    # BOTTOM WINDOW (only needed in DUAL or BOTTOM mode)
                    if not self.dock.hwnd_bottom and self.layout_mode in [LayoutMode.DUAL, LayoutMode.BOTTOM]:
                        bot_id = self.dock.find_window(BOTTOM_SCREEN_WINDOW_TITLE)
                        if bot_id:
                            logger.info(f"Found Bottom Window: {bot_id}")
                            self.dock.hwnd_bottom = bot_id
                            self._bottom_docked = False  # New window — needs docking

                    # Dock once; don't re-reparent on every iteration (causes visual flicker on X11)
                    if self.dock.hwnd_bottom and not self._bottom_docked and self.layout_mode in [LayoutMode.DUAL, LayoutMode.BOTTOM]:
                        self.dock.dock_window(self.dock.hwnd_bottom, self.hwnd_container)
                        self._bottom_docked = True
                        self._last_sync_params = None  # force position update after reparent
                                
            time.sleep(DOCKING_MONITOR_TIME_DELAY)

    @property
    def docking_supported(self):
        """True when a real X11/Win32 DockManager is active (not StatelessDockManager)."""
        return type(self.dock).__name__ != "StatelessDockManager"

    def toggle_dock(self):
        """
        Switches between docked and undocked mode
        Updates window styles and visibility
        """
        if not self.dock.hwnd_top or not self.dock.hwnd_bottom:
            logger.warning("Cannot toggle dock: windows not available")
            return

        with self.dock_lock:
            if self.docked:
                # Undock windows and hide the (now empty) container
                logger.info("Undocking windows")
                self.docked = False
                self._top_docked = False
                self._bottom_docked = False
                self.dock.undock_window(self.dock.hwnd_top)
                self.dock.undock_window(self.dock.hwnd_bottom)
                if self.hwnd_container:
                    self.dock.set_container_visible(self.hwnd_container, False)
                logger.info("Windows undocked successfully")
            else:
                # Show container then dock windows back into it
                logger.info("Docking windows")
                self.docked = True
                self._last_sync_params = None
                if self.hwnd_container:
                    self.dock.set_container_visible(self.hwnd_container, True)
                self._top_docked = False
                self._bottom_docked = False
                self.dock.dock_window(self.dock.hwnd_top, self.hwnd_container)
                self._top_docked = True
                self.dock.dock_window(self.dock.hwnd_bottom, self.hwnd_container)
                self._bottom_docked = True
                logger.info("Windows docked successfully")

    def _resolve_profile_for(self, serial):
        """Pick the DeviceProfile for a serial: remembered → auto-match/selector
        → AYN Thor fallback. Returns a DeviceProfile (never None)."""
        # 1. Previously remembered choice for this device
        remembered = self.config.get("device_profiles", {}).get(serial)
        if remembered:
            prof = self.custom_profiles.load_all().get(remembered) or BUILTIN_PROFILES.get(remembered)
            if prof:
                logger.info(f"Using remembered profile '{remembered}' for {serial}")
                return prof

        # 2. Auto-match against built-in/custom profiles (may prompt to create one
        #    for a genuinely unknown device with >=2 displays)
        try:
            prof = show_device_selector(
                adb_bin=self.scrcpy.adb_bin, serial=serial,
                custom_store=self.custom_profiles, parent_window=None,
            )
            if prof:
                return prof
        except Exception as e:
            logger.error(f"Device selector failed: {e}", exc_info=True)

        # 3. Fallback so the app always works on the primary target device
        logger.info("Falling back to built-in AYN Thor profile")
        return BUILTIN_PROFILES["ayn_thor"]

    def _apply_profile(self, profile):
        """Rebuild the scrcpy manager for a chosen profile (keeps scale/fps)."""
        self.scrcpy = ScrcpyManager(
            scale=self.launch_scale,
            discord_audio_routing=self.config.get("discord_audio_routing", True),
            max_fps=self.max_fps,
            profile=profile,
        )
        logger.info(f"Active device profile: {profile.name}")

    def launch(self):
        """
        Main application entry point (customtkinter UI).
        """
        self.running = True

        # NOTE: no standalone splash screen — customtkinter keeps global DPI/scaling
        # timers bound to the first CTk() root, and destroying a splash root before
        # creating the control-panel root leaves those timers firing on a dead
        # interpreter ("invalid command name"). The single control-panel root below
        # is the only CTk() we create.

        # Check for ADB/Scrcpy and install if missing
        if not self.scrcpy.adb_bin or not self.scrcpy.scrcpy_bin:
            logger.info("Dependencies (adb or scrcpy) not found. Attempting to install...")
            if sys.platform == "linux":
                if self.scrcpy.install_adb():
                    self.scrcpy.adb_bin = self.scrcpy._resolve_bin("adb")
                    self.scrcpy.scrcpy_bin = self.scrcpy._resolve_bin("scrcpy")
            if not self.scrcpy.adb_bin or not self.scrcpy.scrcpy_bin:
                logger.error("Required binaries not found and automatic installation failed/not supported.")

        # Try to detect device, but don't require it
        serial = self.scrcpy.detect_device()

        if serial:
            # Resolve the device profile (remembered / matched / fallback) and
            # rebuild the scrcpy manager so geometry matches the device.
            profile = self._resolve_profile_for(serial)
            self._apply_profile(profile)
            self.scrcpy.serial = serial
            # Recompute the centred default layout for the (possibly new) geometry.
            self.tx, self.ty = TOP_SCREEN_DEFAULT_X, TOP_SCREEN_DEFAULT_Y
            self.by = int(self.scrcpy.f_h1)
            self.bx = int(self.scrcpy.f_w1 * HALF - self.scrcpy.f_w2 * HALF)

            try:
                self.scrcpy.start_scrcpy(serial, swap_screens=self.swap_screens)
                logger.info(f"Started scrcpy with device: {serial}")

                self._create_container_window()
                self._dock_monitor_stop.set()
                time.sleep(0.1)
                self._dock_monitor_stop.clear()
                threading.Thread(target=self._docking_monitor, daemon=True).start()
            except Exception as StartError:
                logger.error(f"Failed to start scrcpy: {StartError}")
        else:
            logger.info("No device detected at startup. User can connect via the Wireless dialog.")
            print("\n[INFO] No device detected. Use the Wireless button in the UI to connect.\n")

        # Init the customtkinter control panel and run its event loop.
        try:
            from src.control_panel import CTkUI
            self.ui = CTkUI(self)
            self._tk_root = self.ui.window
        except Exception as e:
            logger.error(f"Failed to init control panel UI: {e}", exc_info=True)
            self.stop()
            return

        try:
            self.ui.run()   # CTk mainloop; per-frame work runs via tick()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received in main loop")
            print("\n[INFO] Shutting down ThorCPY...")
        finally:
            self.stop()

    def save_swap_screens(self, value):
        """
        Saves the swap_screens preference.
        """
        self.swap_screens = value
        self.config.set("swap_screens", self.swap_screens)
        logger.info(f"Saved swap_screens preference: {self.swap_screens}")

    def save_max_fps(self, value):
        """
        Saves the FPS cap preference and applies it to the scrcpy manager.
        Takes effect on the next scrcpy (re)start.
        """
        self.max_fps = int(value)
        self.config.set("max_fps", self.max_fps)
        if self.scrcpy:
            self.scrcpy.max_fps = self.max_fps
        logger.info(f"Saved max_fps preference: {self.max_fps}")

    # ── Adapter methods consumed by the customtkinter control panel ──────────
    def set_max_fps(self, value):
        """Alias used by the CTk UI; persists + applies the FPS cap."""
        self.save_max_fps(value)

    def restart_app(self):
        """Restart the scrcpy windows to apply scale/FPS changes."""
        self.restart_scrcpy()

    def get_default_layout(self):
        """Return the centred default tx/ty/bx/by for the current profile/scale."""
        w1, h1 = self.scrcpy.f_w1, self.scrcpy.f_h1
        w2 = self.scrcpy.f_w2
        return {
            "tx": TOP_SCREEN_DEFAULT_X,
            "ty": TOP_SCREEN_DEFAULT_Y,
            "by": int(h1),
            "bx": int(w1 * HALF - w2 * HALF),
        }

    def _sync_now(self):
        """Reposition docked scrcpy windows if the layout params changed."""
        if not (self.docked and (self.dock.hwnd_top or self.dock.hwnd_bottom)):
            return
        if self.layout_mode == LayoutMode.TOP:
            sp = (0, 0, 0, 0,
                  self.scrcpy.f_w1, self.scrcpy.f_h1,
                  self.scrcpy.f_w1, self.scrcpy.f_h1)
        elif self.layout_mode == LayoutMode.BOTTOM:
            sp = (0, 0, 0, 0,
                  self.scrcpy.f_w2, self.scrcpy.f_h2,
                  self.scrcpy.f_w2, self.scrcpy.f_h2)
        else:
            sp = (self.tx, self.ty, self.bx, self.by,
                  self.scrcpy.f_w1, self.scrcpy.f_h1,
                  self.scrcpy.f_w2, self.scrcpy.f_h2)
        if sp != self._last_sync_params:
            self.dock.sync_layout(*sp, is_docked=True)
            self._last_sync_params = sp

    def force_sync(self):
        """Force an immediate reposition (used after layout/preset changes)."""
        self._last_sync_params = None
        self._sync_now()

    def get_capture_region(self):
        """Absolute (x, y, w, h) of the docked container for screenshots, or None."""
        if not self.docked:
            return None
        return self.dock.get_container_geometry()

    def tick(self):
        """Per-frame backend work, driven by the CTk UI's after() timer."""
        if main_module and getattr(main_module, "_shutdown_requested", False):
            logger.info("Shutdown requested via signal")
            self.stop()
            return
        self.check_pending_connection()
        self.check_scan_status()
        self.dock.process_events()
        self._sync_now()

    def show_connection_dialog(self):
        """Open the customtkinter wireless dialog. Returns 'connected',
        'disconnected' or None."""
        try:
            from src.wireless_dialog import show_wireless_dialog
        except Exception as e:
            logger.error(f"Wireless dialog unavailable: {e}")
            return None
        parent = getattr(self, "_tk_root", None)
        result = show_wireless_dialog(parent, self.scrcpy, config=self.config)
        # On a fresh connection, hand the serial to check_pending_connection so
        # scrcpy starts + docks on the next UI tick.
        if result == "connected" and self.scrcpy.serial:
            self._dialog_connect_ip = self.scrcpy.serial
        return result

    def show_wireless_connection_dialog(self):
        """Open the pygame wireless overlay (no subprocess needed)."""
        if not hasattr(self, 'ui') or not self.ui:
            return
        # Pre-fill connect IP from quick IP field
        current_ip = self.ui.quick_ip.strip() if self.ui.quick_ip else ""
        if current_ip and ":" in current_ip:
            ip, port = current_ip.rsplit(":", 1)
            self.ui.wireless_fields["connect_ip"]   = ip
            self.ui.wireless_fields["connect_port"] = port
        elif current_ip:
            self.ui.wireless_fields["connect_ip"] = current_ip
        self.ui.show_wireless   = True
        self.ui.wireless_status = ""
    
    def check_pending_connection(self):
        """
        Check if a wireless connection was established and start scrcpy.
        """
        # Check for dialog connection
        if self._dialog_connect_ip:
            ip_port = self._dialog_connect_ip
            self._dialog_connect_ip = None
            
            logger.info(f"Processing dialog connection: {ip_port}")
            
            try:
                # Stop existing
                if self.scrcpy.processes:
                    self.scrcpy.stop()
                    with self.dock_lock:
                        self.docked = False
                        self.dock.hwnd_top = None
                        self.dock.hwnd_bottom = None
                        self._top_docked = False
                        self._bottom_docked = False

                # Start scrcpy
                serial = self.scrcpy.serial
                self.scrcpy.start_scrcpy(serial, swap_screens=self.swap_screens)

                # Re-enable docking and create a fresh container
                self.docked = True
                self._last_sync_params = None  # force sync_layout on next frame
                self._create_container_window()
                self._dock_monitor_stop.set()
                time.sleep(0.1)
                self._dock_monitor_stop.clear()
                threading.Thread(target=self._docking_monitor, daemon=True).start()

                if hasattr(self, 'ui') and self.ui:
                    self.ui.show_status(f"Connected to {ip_port}", "success", 5.0)
                    
            except Exception as e:
                logger.error(f"Failed to start scrcpy: {e}")
                if hasattr(self, 'ui') and self.ui:
                    self.ui.show_status(f"Failed: {e}", "error", 5.0)

    def connect_wireless_async(self, ip, port, callback):
        """Run adb connect in a background thread. Calls callback(success, message)."""
        def _run():
            try:
                import subprocess as _sp
                r = _sp.run(
                    [self.scrcpy.adb_bin, "connect", f"{ip}:{port}"],
                    capture_output=True, text=True, timeout=10
                )
                out = (r.stdout + r.stderr).lower()
                if ("connected" in out or "already connected" in out) \
                        and "unable" not in out and "failed" not in out:
                    self.scrcpy.serial         = f"{ip}:{port}"
                    self.scrcpy.connection_mode = "wireless"
                    self._dialog_connect_ip    = f"{ip}:{port}"
                    callback(True, f"Connected to {ip}:{port}")
                else:
                    callback(False, (r.stdout + r.stderr).strip()[:80] or "Connection failed")
            except Exception as e:
                callback(False, str(e)[:80])
        threading.Thread(target=_run, daemon=True).start()

    def pair_wireless_async(self, ip, port, code, callback):
        """Run adb pair in a background thread. Calls callback(success, message)."""
        def _run():
            try:
                import subprocess as _sp
                proc = _sp.Popen(
                    [self.scrcpy.adb_bin, "pair", f"{ip}:{port}"],
                    stdin=_sp.PIPE, stdout=_sp.PIPE, stderr=_sp.STDOUT, text=True
                )
                out, _ = proc.communicate(input=f"{code}\n", timeout=30)
                if proc.returncode == 0 and \
                        ("successfully paired" in out.lower() or "paired" in out.lower()):
                    callback(True, "Paired! Now use Quick Connect to connect.")
                else:
                    callback(False, out.strip()[:80] or "Pairing failed")
            except Exception as e:
                callback(False, str(e)[:80])
        threading.Thread(target=_run, daemon=True).start()

    def quick_connect_wireless(self, ip_port):
        """
        Quick connect to a wireless device using IP:Port string.
        Runs connection in background thread.
        
        Args:
            ip_port: String in format "IP:PORT" (e.g., "192.168.1.100:5555")
        """
        # Parse IP:Port
        if ':' in ip_port:
            parts = ip_port.rsplit(':', 1)
            if len(parts) != 2:
                logger.error(f"Invalid IP:port format: {ip_port}")
                if hasattr(self, 'ui') and self.ui:
                    self.ui.show_status("Invalid address format", "error", 3.0)
                return
            ip = parts[0]
            try:
                port = int(parts[1])
            except (ValueError, IndexError):
                port = 5555
        else:
            ip = ip_port
            port = 5555
        
        logger.info(f"Quick connect requested to {ip}:{port}")
        
        # Start connection in background thread
        self._quick_connecting = True
        self._quick_connect_thread = threading.Thread(
            target=self._quick_connect_thread_func,
            args=(ip, port),
            daemon=True
        )
        self._quick_connect_thread.start()
    
    def _quick_connect_thread_func(self, ip, port):
        """
        Background thread function for quick connect.
        """
        try:
            # Try to connect
            if self.scrcpy.connect_wireless(ip, port):
                serial = self.scrcpy.serial
                logger.info(f"Quick connect successful: {serial}")
                
                try:
                    # Stop existing processes before starting new ones
                    if self.scrcpy.processes:
                        self.scrcpy.stop()
                        with self.dock_lock:
                            self.docked = False
                            self.dock.hwnd_top = None
                            self.dock.hwnd_bottom = None
                            self._top_docked = False
                            self._bottom_docked = False

                    self.scrcpy.start_scrcpy(serial, swap_screens=self.swap_screens)
                    self.docked = True
                    self._create_container_window()
                    self._dock_monitor_stop.set()
                    time.sleep(0.1)
                    self._dock_monitor_stop.clear()
                    threading.Thread(target=self._docking_monitor, daemon=True).start()

                    if hasattr(self, 'ui') and self.ui:
                        self.ui.show_status(f"Connected to {serial}!", "success", 5.0)
                except Exception as e:
                    logger.error(f"Failed to start scrcpy after quick connect: {e}")
                    if hasattr(self, 'ui') and self.ui:
                        self.ui.show_status(f"Connection OK but scrcpy failed: {e}", "error", 5.0)
            else:
                logger.warning(f"Quick connect failed to {ip}:{port}")
                if hasattr(self, 'ui') and self.ui:
                    self.ui.show_status(f"Failed to connect to {ip}:{port}", "error", 5.0)
        except Exception as e:
            logger.error(f"Quick connect error: {e}")
            if hasattr(self, 'ui') and self.ui:
                self.ui.show_status(f"Connection error: {e}", "error", 5.0)
        finally:
            self._quick_connecting = False

    def scan_for_devices(self):
        """
        Scan the local network for Android devices.
        Returns immediately, results will be available via self._scan_results.
        """
        if self._scanning:
            logger.debug("Scan already in progress")
            return False
        
        self._scanning = True
        self._scan_results = []
        self._scan_progress = "Scanning network..."
        
        self._scan_thread = threading.Thread(target=self._scan_thread_func, daemon=True)
        self._scan_thread.start()
        return True
    
    def _scan_thread_func(self):
        """
        Background thread function for network scanning.
        """
        try:
            # Update progress
            self._scan_progress = "Detecting subnet..."
            
            def update_progress(current, total):
                """Callback to update scan progress."""
                percent = int((current / total) * 100)
                self._scan_progress = f"Scanning... {percent}%"
            
            # Scan for devices with progress callback
            devices = self.scrcpy.scan_network_for_devices(progress_callback=update_progress)
            
            self._scan_results = devices
            self._scan_progress = f"Found {len(devices)} device(s)" if devices else "No devices found"
            
            # Show status in UI
            if hasattr(self, 'ui') and self.ui:
                if devices:
                    device_list = ", ".join(devices)
                    self.ui.show_status(f"Found devices: {device_list}", "success", 10.0)
                else:
                    self.ui.show_status("No devices found on network", "warning", 5.0)
                    
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self._scan_progress = f"Scan failed: {e}"
            if hasattr(self, 'ui') and self.ui:
                self.ui.show_status(f"Scan failed: {e}", "error", 5.0)
        finally:
            self._scanning = False
    
    def check_scan_status(self):
        """
        Check if a scan is complete and update UI.
        Should be called from the main loop.
        """
        if self._scanning:
            # Update scan progress in UI if needed
            pass
        
        # Check if we have new scan results to display
        if hasattr(self, '_scan_results') and self._scan_results and hasattr(self, 'ui') and self.ui:
            # Results are available, UI can display them
            pass

    def restart_scrcpy(self):
        """
        Restarts the scrcpy instances with current settings.
        Useful when changing screen order or other core settings.
        """
        logger.info("Restarting scrcpy instances...")
        
        # 1. Stop existing instances
        if hasattr(self, 'scrcpy'):
            self.scrcpy.stop()
            
        # 2. Undock everything
        with self.dock_lock:
             self.docked = False # Temporarily undocked
             if self.dock.hwnd_top:
                 self.dock.undock_window(self.dock.hwnd_top)
             if self.dock.hwnd_bottom:
                 self.dock.undock_window(self.dock.hwnd_bottom)
             
             # Reset window handles
             self.dock.hwnd_top = None
             self.dock.hwnd_bottom = None
             self._top_docked = False
             self._bottom_docked = False

        # 3. Start new instances
        serial = self.scrcpy.detect_device()
        if serial:
            try:
                # Pass current swap_screens setting
                self.scrcpy.start_scrcpy(serial, swap_screens=self.swap_screens)
                self.docked = True # Re-enable docking
            except Exception as StartError:
                logger.error(f"Failed to restart scrcpy: {StartError}")
                # Try to recover or notify?
        else:
            logger.error("No device found during restart")

    def stop(self):
        """
        Cleanly shuts down the application
        """
        if not self.running:
            return
        self.running = False
        self.save_layout()

        # Stop scrcpy instances
        if hasattr(self, 'scrcpy'):
            self.scrcpy.stop() # This uses pkill/terminate now hopefully

        # Tear down the customtkinter UI (ends the mainloop)
        try:
            root = getattr(self, "_tk_root", None)
            if root is not None:
                root.quit()
                root.destroy()
        except Exception:
            pass

        # Exit
        sys.exit(0)

if __name__ == "__main__":
    try:
        app = Launcher()
        app.launch()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, exiting...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
