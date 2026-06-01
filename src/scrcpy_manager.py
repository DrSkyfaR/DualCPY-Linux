# DualCPY – Dual-screen scrcpy docking and control UI for Windows
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

# src/scrcpy_manager.py

import os
import subprocess
import time
import shutil
import logging
import sys
import signal
import re
import threading

# Setup logger for this module
logger = logging.getLogger(__name__)

# Process creation flags (Windows only)
if sys.platform == "win32":
    CREATE_NO_WINDOW = 0x08000000 
else:
    CREATE_NO_WINDOW = 0 # Ignored on Linux

# Default UI scaling
DEFAULT_UI_SCALING = 0.6

# Top screen base resolution
TOP_SCREEN_BASE_WIDTH = 1920
TOP_SCREEN_BASE_HEIGHT = 1080

# Resolution calculation factors for the bottom screen
# These are device-specific ratios for the AYN Thor
TOP_BOTTOM_SCALE_FACTOR = 5.23
BOTTOM_WIDTH_SCALE_FACTOR = 2.95
BOTTOM_HEIGHT_SCALE_FACTOR = 2.57

# Scrcpy startup retry config
SCRCPY_RETRY_COUNT = 2
SCRCPY_START_DELAY = 1.0

# ADB command timeouts
ADB_CAPTURE_OUTPUT = True
ADB_SERVER_TIMEOUT = 10
ADB_TASKKILL_TIMEOUT = 5
ADB_CONNECT_TIMEOUT = 10
ADB_TCPIP_TIMEOUT = 5
# How many times to (re)start the adb server before giving up on detection.
# On a flaky server a kill-server + start-server between attempts clears stuck state.
ADB_SERVER_START_RETRIES = 2
ADB_SERVER_RETRY_DELAY = 0.6

# Nice value applied to scrcpy children (POSIX). Negative = higher priority;
# requires CAP_SYS_NICE/root, so it is attempted best-effort and ignored if denied.
SCRCPY_NICE = -5

# Default wireless port
DEFAULT_WIRELESS_PORT = 5555

# Logging constants
LOG_MULT = 60 # Width of log separator lines
LOGFILE_ENCODING = "utf-8"

# Scrcpy default parameters
DEFAULT_MAX_FPS = "120"
DEFAULT_RENDER_DRIVER = "opengl"
DEFAULT_VIDEO_CODEC = "h264"

# MediaCodec encoder tuning passed via --video-codec-options. These bias the
# on-device H.264 encoder towards low latency over compression efficiency,
# which keeps the mirrored stream responsive (device-side, OS-agnostic).
SCRCPY_CODEC_OPTIONS = (
    "low-latency=1,"
    "priority=0,"
    "operating-rate=120,"
    "bitrate-mode=2,"
    "complexity=0,"
    "i-frame-interval=10,"
    "intra-refresh-period=60"
)

# Video bitrate calculation constants
BITRATE_CALC_SCALE_FACTOR = 1.5
TOP_BITRATE_MINIMUM = 8
TOP_BITRATE_SCALE = 32
BOTTOM_BITRATE_MINIMUM = 6
BOTTOM_BITRATE_SCALE = 24

# AYN Thor Screen Constants
TOP_SCREEN_DISPLAY_ID = "0"
TOP_SCREEN_WINDOW_TITLE = "DualCPY Top Screen"
BOTTOM_SCREEN_DISPLAY_ID = "4"
BOTTOM_SCREEN_WINDOW_TITLE = "DualCPY Bottom Screen"

# PipeWire/PulseAudio virtual device names for Discord audio routing (Linux only)
GAME_SINK_NAME = "dualcpy_game"
GAME_SINK_DESCRIPTION = "DualCPY_Game"
COMBINED_SINK_NAME = "dualcpy_mic"
COMBINED_SINK_DESCRIPTION = "DualCPY_Discord_Mic"
AUDIO_LOOPBACK_LATENCY_MS = 100

# Timing delays for process management
DISPLAY_INIT_DELAY = 1.2  # Wait for first display to initialize
SCRCPY_CREATION_DELAY = 0.3  # Check if process survives startup
SCRCPY_RETRY_DELAY = 0.7  # Wait between retry attempts

# Process termination timeouts
PROCESS_TERMINATE_TIMEOUT = 2
SCRCPY_TERMINATE_TIMEOUT = 3

class AudioRouter:
    """
    Routes scrcpy audio through PipeWire/PulseAudio so that:
      - Audio plays locally through speakers (loopback to default sink)
      - Discord captures it automatically without any Discord settings change

    Graph built on setup():
      scrcpy → GAME_SINK ──► speakers          (local playback)
                         └──► COMBINED_SINK ◄── real microphone
                                    │
                               default source  ← Discord reads this automatically

    On teardown() the original default source is restored and all modules are removed.
    """

    def __init__(self):
        self._module_ids = []
        self._original_default_source = None
        self._active = False

    @staticmethod
    def is_supported():
        return sys.platform == "linux" and shutil.which("pactl") is not None

    def _get_default_source(self):
        try:
            result = subprocess.run(["pactl", "info"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                if line.startswith("Default Source:"):
                    return line.split(":", 1)[1].strip()
        except Exception as e:
            logger.warning(f"Could not read default source: {e}")
        return None

    def _load_null_sink(self, name, description):
        """Create a null-sink, store module ID, return ID or None on failure."""
        result = subprocess.run(
            [
                "pactl", "load-module", "module-null-sink",
                f"sink_name={name}",
                f"sink_properties=device.description={description}",
            ],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            logger.error(f"Failed to create sink '{name}': {result.stderr.strip()}")
            return None
        mod_id = result.stdout.strip()
        self._module_ids.append(mod_id)
        logger.info(f"Null sink '{name}' created (module {mod_id})")
        return mod_id

    def _load_loopback(self, source, sink):
        """Create a loopback module, store module ID, return ID or None on failure."""
        result = subprocess.run(
            [
                "pactl", "load-module", "module-loopback",
                f"source={source}",
                f"sink={sink}",
                f"latency_msec={AUDIO_LOOPBACK_LATENCY_MS}",
            ],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            logger.warning(f"Loopback {source}→{sink} failed: {result.stderr.strip()}")
            return None
        mod_id = result.stdout.strip()
        self._module_ids.append(mod_id)
        logger.info(f"Loopback {source}→{sink} (module {mod_id})")
        return mod_id

    def setup(self):
        """
        Build the routing graph.
        Returns an env dict for scrcpy (PULSE_SINK + SDL_AUDIODRIVER), or None on failure.
        """
        if not self.is_supported():
            logger.warning("Audio routing unavailable: pactl not found")
            return None
        if self._active:
            return {"PULSE_SINK": GAME_SINK_NAME, "SDL_AUDIODRIVER": "pulseaudio"}

        try:
            self._original_default_source = self._get_default_source()
            logger.info(f"Saving default source: {self._original_default_source}")

            # 1. Game sink — scrcpy outputs here
            if not self._load_null_sink(GAME_SINK_NAME, GAME_SINK_DESCRIPTION):
                return None

            # 2. Game audio → speakers (local playback)
            self._load_loopback(f"{GAME_SINK_NAME}.monitor", "@DEFAULT_SINK@")

            # 3. Combined sink — mic + game mixed together
            if not self._load_null_sink(COMBINED_SINK_NAME, COMBINED_SINK_DESCRIPTION):
                return None

            # 4. Real microphone → combined (voice is preserved in Discord)
            if self._original_default_source and ".monitor" not in self._original_default_source:
                self._load_loopback(self._original_default_source, COMBINED_SINK_NAME)

            # 5. Game audio → combined (Discord also captures game audio)
            self._load_loopback(f"{GAME_SINK_NAME}.monitor", COMBINED_SINK_NAME)

            # 6. Set combined.monitor as default source — Discord picks it up automatically
            result = subprocess.run(
                ["pactl", "set-default-source", f"{COMBINED_SINK_NAME}.monitor"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                logger.warning(f"Could not set default source: {result.stderr.strip()}")
            else:
                logger.info(f"Default source → {COMBINED_SINK_NAME}.monitor (Discord auto-captures)")

            self._active = True
            # SDL_AUDIODRIVER=pulseaudio forces SDL to use the PulseAudio compat layer
            # so PULSE_SINK is honoured even on PipeWire
            return {"PULSE_SINK": GAME_SINK_NAME, "SDL_AUDIODRIVER": "pulseaudio"}

        except subprocess.TimeoutExpired:
            logger.error("Timeout during audio routing setup")
            self.teardown()
            return None
        except Exception as e:
            logger.error(f"Error setting up audio routing: {e}")
            self.teardown()
            return None

    def teardown(self):
        """Restore original default source and remove all created PipeWire modules."""
        if self._original_default_source:
            try:
                subprocess.run(
                    ["pactl", "set-default-source", self._original_default_source],
                    capture_output=True, timeout=5,
                )
                logger.info(f"Restored default source: {self._original_default_source}")
            except Exception as e:
                logger.warning(f"Failed to restore default source: {e}")

        for mod_id in reversed(self._module_ids):
            try:
                subprocess.run(
                    ["pactl", "unload-module", mod_id],
                    capture_output=True, timeout=5,
                )
                logger.info(f"Unloaded module {mod_id}")
            except Exception as e:
                logger.warning(f"Failed to unload module {mod_id}: {e}")

        self._module_ids = []
        self._original_default_source = None
        self._active = False


# Main ScrcpyManager class
class ScrcpyManager:
    """
    Manages scrcpy instances for controlling and displaying the Thor's screens
    Handles device detection, window launching, scaling, resolution and process management and shutdown
    """

    def __init__(self, scale=None, scrcpy_bin=None, adb_bin=None,
                 enable_audio_top=True, discord_audio_routing=True,
                 max_fps=int(DEFAULT_MAX_FPS), profile=None):
        """
        Initialize the scrcpy manager.

        Args:
            scale: float, scaling factor for window resolution (default: profile's)
            scrcpy_bin: optional custom path to scrcpy binary
            adb_bin: optional custom path to adb binary
            enable_audio_top: if True, enable audio on top window
            discord_audio_routing: if True (Linux only), route audio through a virtual
                PipeWire sink so Discord screen-share can capture it
            max_fps: int, FPS cap for the top window (bottom is capped to <=60)
            profile: DeviceProfile describing screen geometry/display IDs. Defaults
                to the built-in AYN Thor profile when not supplied.
        """
        from src.device_profile import BUILTIN_PROFILES
        self.profile = profile or BUILTIN_PROFILES["ayn_thor"]

        # Configurable FPS cap (top window). Falls back to the default if unset/invalid.
        try:
            self.max_fps = int(max_fps) if max_fps else int(DEFAULT_MAX_FPS)
        except (TypeError, ValueError):
            self.max_fps = int(DEFAULT_MAX_FPS)

        self.scale = scale if scale is not None else self.profile.default_ui_scale

        logger.info(f"Initializing ScrcpyManager (profile={self.profile.name}, scale={self.scale}, "
                    f"audio={enable_audio_top}, discord_audio_routing={discord_audio_routing}, "
                    f"max_fps={self.max_fps})")

        self.processes = [] # Track all scrcpy subprocess instances
        self._log_files = []  # Track open log file handles
        self.serial = None
        self.enable_audio_top = enable_audio_top

        # Audio routing for Discord screen-share (Linux only)
        self._audio_router = AudioRouter() if (discord_audio_routing and sys.platform == "linux") else None

        # Window resolutions derived from the device profile + scale.
        # Bottom is sized by the physical width ratio so both panels share a
        # consistent on-screen scale (matches the original DualCPY formula).
        self.f_w1 = int(self.profile.top_screen_width * self.scale)
        self.f_h1 = int(self.profile.top_screen_height * self.scale)
        logger.debug(f"Top window resolution: {self.f_w1}x{self.f_h1}")

        ratio = self.profile.get_screen_width_ratio()
        self.f_w2 = int(self.f_w1 * ratio)
        self.f_h2 = int(self.f_w2 * self.profile.bottom_screen_height / self.profile.bottom_screen_width)
        logger.debug(f"Bottom window resolution: {self.f_w2}x{self.f_h2}")

        # Locate scrcpy and adb binaries
        self.scrcpy_bin = scrcpy_bin or self._resolve_bin("scrcpy")
        self.adb_bin = adb_bin or self._resolve_bin("adb")

        if self.scrcpy_bin:
            logger.info(f"scrcpy binary found: {self.scrcpy_bin}")
        else:
            logger.warning("scrcpy binary not found")

        if self.adb_bin:
            logger.info(f"adb binary found: {self.adb_bin}")
        else:
            logger.warning("adb binary not found")

        # Retry config
        self.scrcpy_retry_count = SCRCPY_RETRY_COUNT
        self.scrcpy_start_delay = SCRCPY_START_DELAY
        logger.debug(f"Retry count: {self.scrcpy_retry_count}, Start delay: {self.scrcpy_start_delay}s")

        # Connection mode tracking (usb/wireless)
        self.connection_mode = None

    def _resolve_bin(self, name):
        """
        Finds binary in local ./bin folder or system path.

        Args:
            name: Binary name (e.g., "scrcpy" or "adb")

        Returns:
            Full path to binary or None if not found
        """
        logger.debug(f"Resolving binary: {name}")

        # Check local bin folder first
        local = os.path.join(os.getcwd(), "bin", f"{name}.exe" if sys.platform == "win32" else name)
        if os.path.exists(local):
            logger.info(f"Found {name} in local bin folder: {local}")
            return local

        # Fallback to system PATH
        found = shutil.which(name)
        if found:
            logger.info(f"Found {name} in system PATH: {found}")
            return found

        logger.warning(f"Binary '{name}' not found in local bin or system PATH")
        return None

    def install_adb(self):
        """
        Attempts to install ADB using the system package manager.
        Currently supports Arch Linux (pacman) and Debian/Ubuntu (apt).
        Uses pkexec for permission elevation.
        """
        logger.info("Attempting to install ADB...")
        
        if sys.platform != "linux":
            logger.warning("Automatic ADB installation is only supported on Linux.")
            return False

        install_cmd = None
        
        # Check for pacman (Arch Linux)
        if shutil.which("pacman"):
            logger.info("Detected pacman package manager")
            install_cmd = ["pkexec", "pacman", "-S", "--noconfirm", "android-tools", "scrcpy"]
        # Check for apt (Debian/Ubuntu)
        elif shutil.which("apt-get"):
            logger.info("Detected apt package manager")
            install_cmd = ["pkexec", "apt-get", "install", "-y", "android-tools-adb", "scrcpy"]
        
        if not install_cmd:
            logger.error("No supported package manager found (pacman, apt).")
            return False

        try:
            logger.info(f"Running install command: {' '.join(install_cmd)}")
            # usage of pkexec might open a GUI prompt
            result = subprocess.run(install_cmd, check=True)
            if result.returncode == 0:
                logger.info("ADB installation successful.")
                return True
            else:
                logger.error("ADB installation failed.")
                return False
        except subprocess.CalledProcessError as InstallError:
            logger.error(f"Installation command failed: {InstallError}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during ADB installation: {e}")
            return False


    def _is_wireless_serial(self, serial):
        """
        Check if serial is in IP:PORT format (wireless connection).
        
        Args:
            serial: Device serial string
            
        Returns:
            bool: True if wireless format, False otherwise
        """
        if not serial:
            return False
        return ':' in serial and re.match(r'\d+\.\d+\.\d+\.\d+:\d+', serial) is not None

    def detect_device(self):
        """
        Detect and return serial of first connected Android ADB device.

        Starts ADB server if needed, then queries for authorized devices.
        Ignores unauthorized devices to prevent connection issues.
        Detects both USB and wireless connections.

        Returns:
            Device serial string or None if no device found
        """
        logger.info("Starting ADB device detection")

        if self.serial:
            logger.debug(f"Device already detected: {self.serial}")
            return self.serial

        if not self.adb_bin:
            logger.error("Cannot detect device: ADB binary not found")
            return None

        # Detect with retries: on a flaky/stuck adb server a kill + restart
        # between attempts often recovers a device that didn't enumerate first time.
        for attempt in range(1, ADB_SERVER_START_RETRIES + 1):
            self._start_adb_server()
            serial = self._query_first_device()
            if serial:
                return serial
            if attempt < ADB_SERVER_START_RETRIES:
                logger.warning(
                    f"No device on attempt {attempt}/{ADB_SERVER_START_RETRIES}; "
                    "restarting adb server and retrying"
                )
                self._kill_adb_server()
                time.sleep(ADB_SERVER_RETRY_DELAY)

        logger.warning("No device detected after all adb attempts")
        return None

    def _start_adb_server(self):
        """Best-effort 'adb start-server'."""
        try:
            logger.debug("Starting ADB server")
            result = subprocess.run(
                [self.adb_bin, "start-server"],
                capture_output=ADB_CAPTURE_OUTPUT,
                text=True,
                timeout=ADB_SERVER_TIMEOUT,
            )
            if result.returncode != 0:
                logger.warning(f"ADB start-server returned code {result.returncode}")
            else:
                logger.debug("ADB server started successfully")
        except subprocess.TimeoutExpired:
            logger.error("ADB start-server timed out")
        except Exception as ADBStartError:
            logger.error(f"Failed to start ADB server: {ADBStartError}", exc_info=True)

    def _kill_adb_server(self):
        """Best-effort 'adb kill-server' to clear a stuck server before retrying."""
        try:
            subprocess.run(
                [self.adb_bin, "kill-server"],
                capture_output=ADB_CAPTURE_OUTPUT,
                text=True,
                timeout=ADB_SERVER_TIMEOUT,
            )
            logger.debug("ADB server killed")
        except Exception as ADBKillError:
            logger.warning(f"adb kill-server failed: {ADBKillError}")

    def _query_first_device(self):
        """Return the serial of the first authorized device, or None."""
        try:
            logger.debug("Querying connected devices")
            out = subprocess.check_output([self.adb_bin, "devices"], text=True, timeout=ADB_SERVER_TIMEOUT)
            logger.debug(f"ADB devices output:\n{out}")

            # Parse device list (skip header line)
            lines = out.strip().splitlines()[1:]
            devices = []
            for line in lines:
                if "device" in line and "unauthorized" not in line:
                    parts = line.split()
                    if parts:
                        devices.append(parts[0])

            if devices:
                self.serial = devices[0]
                # Determine connection mode
                if self._is_wireless_serial(self.serial):
                    self.connection_mode = 'wireless'
                    logger.debug(f"Wireless device detected: {self.serial}")
                else:
                    self.connection_mode = 'usb'
                    logger.debug(f"USB device detected: {self.serial}")

                if len(devices) > 1:
                    logger.info(
                        f"Multiple devices found ({len(devices)}), using first: {self.serial}"
                    )
                return self.serial

            logger.warning("No devices found in ADB device list")
        except subprocess.TimeoutExpired:
            logger.error("ADB devices command timed out")
        except subprocess.CalledProcessError as DeviceSearchError:
            logger.error(f"ADB devices command failed: {DeviceSearchError}", exc_info=True)
        except Exception as DeviceSearchException:
            logger.error(f"Unexpected error during device detection: {DeviceSearchException}", exc_info=True)

        return None

    def connect_wireless(self, ip_address, port=DEFAULT_WIRELESS_PORT):
        """
        Connect to a device wirelessly using adb connect.
        
        Args:
            ip_address: IP address of the device
            port: Port number (default: 5555)
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.adb_bin:
            logger.error("Cannot connect wireless: ADB binary not found")
            return False
        
        target = f"{ip_address}:{port}"
        logger.debug(f"Attempting wireless connection to {target}")
        
        try:
            result = subprocess.run(
                [self.adb_bin, "connect", target],
                capture_output=True,
                text=True,
                timeout=ADB_CONNECT_TIMEOUT
            )
            
            logger.debug(f"adb connect output: {result.stdout}")
            if result.stderr:
                logger.debug(f"adb connect stderr: {result.stderr}")
            
            if result.returncode == 0 and ("connected" in result.stdout.lower() or "already connected" in result.stdout.lower()):
                self.serial = target
                self.connection_mode = 'wireless'
                logger.debug(f"Successfully connected to {target}")
                return True
            else:
                logger.warning(f"Failed to connect to {target}: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Wireless connection to {target} timed out")
            return False
        except Exception as e:
            logger.error(f"Error during wireless connection: {e}", exc_info=True)
            return False

    def pair_wireless(self, ip_address, pairing_port, pairing_code):
        """
        Pair with a device for wireless debugging (Android 11+).
        
        Args:
            ip_address: IP address of the device
            pairing_port: Pairing port shown on device
            pairing_code: 6-digit pairing code shown on device
            
        Returns:
            bool: True if pairing successful, False otherwise
        """
        if not self.adb_bin:
            logger.error("Cannot pair wireless: ADB binary not found")
            return False
        
        target = f"{ip_address}:{pairing_port}"
        logger.debug(f"Attempting wireless pairing with {target}")
        
        try:
            # Start the pair process
            process = subprocess.Popen(
                [self.adb_bin, "pair", target],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Send the pairing code
            output, _ = process.communicate(input=f"{pairing_code}\n", timeout=ADB_CONNECT_TIMEOUT)
            
            logger.debug(f"adb pair output: {output}")
            
            if process.returncode == 0 and ("successfully paired" in output.lower() or "paired" in output.lower()):
                logger.debug(f"Successfully paired with {target}")
                return True
            else:
                logger.warning(f"Pairing failed: {output}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Wireless pairing with {target} timed out")
            try:
                process.kill()
                process.wait(timeout=5)
            except Exception:
                pass
            return False
        except Exception as e:
            logger.error(f"Error during wireless pairing: {e}", exc_info=True)
            return False

    def disconnect_wireless(self, target=None):
        """
        Disconnect a wireless ADB connection.
        
        Args:
            target: Target to disconnect (IP:PORT). If None, disconnects current serial.
            
        Returns:
            bool: True if disconnect successful or no connection to disconnect
        """
        if not self.adb_bin:
            logger.error("Cannot disconnect wireless: ADB binary not found")
            return False
        
        disconnect_target = target or self.serial
        
        if not disconnect_target or not self._is_wireless_serial(disconnect_target):
            logger.info("No wireless connection to disconnect")
            return True
        
        logger.debug(f"Disconnecting wireless connection: {disconnect_target}")
        
        try:
            result = subprocess.run(
                [self.adb_bin, "disconnect", disconnect_target],
                capture_output=True,
                text=True,
                timeout=ADB_CONNECT_TIMEOUT
            )
            
            logger.debug(f"adb disconnect output: {result.stdout}")
            
            if result.returncode == 0:
                logger.debug(f"Successfully disconnected {disconnect_target}")
                if self.serial == disconnect_target:
                    self.serial = None
                    self.connection_mode = None
                return True
            else:
                logger.warning(f"Disconnect returned non-zero: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Disconnect timed out")
            return False
        except Exception as e:
            logger.error(f"Error during disconnect: {e}", exc_info=True)
            return False

    def enable_wireless_mode(self, port=DEFAULT_WIRELESS_PORT):
        """
        Enable TCP/IP mode on a USB-connected device.
        This allows subsequent wireless connections.
        
        Args:
            port: Port to use for TCP/IP mode (default: 5555)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.adb_bin:
            logger.error("Cannot enable wireless mode: ADB binary not found")
            return False
        
        if not self.serial:
            logger.error("Cannot enable wireless mode: No device connected via USB")
            return False
        
        if self._is_wireless_serial(self.serial):
            logger.info("Device is already connected wirelessly")
            return True
        
        logger.debug(f"Enabling TCP/IP mode on {self.serial} port {port}")
        
        try:
            result = subprocess.run(
                [self.adb_bin, "-s", self.serial, "tcpip", str(port)],
                capture_output=True,
                text=True,
                timeout=ADB_TCPIP_TIMEOUT
            )
            
            if result.returncode == 0:
                logger.info(f"TCP/IP mode enabled on port {port}")
                return True
            else:
                logger.warning(f"Failed to enable TCP/IP mode: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Enable TCP/IP mode timed out")
            return False
        except Exception as e:
            logger.error(f"Error enabling TCP/IP mode: {e}", exc_info=True)
            return False

    def get_device_ip(self):
        """
        Get the IP address of the connected device (from wlan0 interface).
        
        Returns:
            str: IP address or None if not available
        """
        if not self.adb_bin or not self.serial:
            return None
        
        try:
            result = subprocess.run(
                [self.adb_bin, "-s", self.serial, "shell", "ip", "addr", "show", "wlan0"],
                capture_output=True,
                text=True,
                timeout=ADB_SERVER_TIMEOUT
            )
            
            if result.returncode == 0:
                # Parse IP from output: "inet 192.168.1.100/24"
                match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                if match:
                    ip = match.group(1)
                    logger.debug(f"Device IP address: {ip}")
                    return ip
                    
            logger.warning("Could not determine device IP address")
            return None
            
        except Exception as e:
            logger.error(f"Error getting device IP: {e}", exc_info=True)
            return None

    # Start Scrcpy Windows
    def get_displays(self, serial):
        """
        Parses scrcpy --list-displays checking for available displays.
        Returns a list of display IDs (strings).
        """
        if not self.scrcpy_bin:
            return []

        try:
            cmd = [self.scrcpy_bin, "-s", serial, "--list-displays"]
            logger.debug(f"Querying displays: {' '.join(cmd)}")
            # scrcpy output is often on stderr or stdout depending on version
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            output = result.stdout + result.stderr
            logger.debug(f"Display query output: {output}")
            
            # Parse output looking for --display-id=X
            # Example line: "--display-id=0 (1080x2400)"
            import re
            ids = re.findall(r"--display-id=(\d+)", output)
            
            # Remove duplicates and sort
            ids = sorted(list(set(ids)), key=int)
            logger.info(f"Detected displays: {ids}")
            return ids
            
        except Exception as e:
            logger.error(f"Failed to query displays: {e}")
            return []

    def start_scrcpy(self, serial=None, extra_top_args=None, extra_bottom_args=None, swap_screens=False):
        """
        Launches scrcpy instances for the detected displays.
        
        Args:
            serial: Device serial (optional if already detected)
            extra_top_args: List of additional args for top window
            extra_bottom_args: List of additional args for bottom window
            swap_screens (bool): If True, swaps the Top and Bottom displays.

        Returns:
            list: Popen objects for launched processes

        Raises:
            RuntimeError: If device serial missing or scrcpy binary not found
        """
        logger.info("=" * LOG_MULT)
        logger.info(f"Starting scrcpy instances (Swap Screens: {swap_screens})")
        logger.info("=" * LOG_MULT)

        if serial:
            self.serial = serial
            logger.debug(f"Using provided serial: {serial}")

        if not self.serial:
            logger.error("Cannot start scrcpy: No device serial provided")
            raise RuntimeError("No device serial provided to ScrcpyManager.start_scrcpy")

        if not self.scrcpy_bin:
            logger.error("Cannot start scrcpy: scrcpy binary not found")
            raise RuntimeError("scrcpy binary not found")

        logger.debug(f"Device serial: {self.serial}")
        logger.info(f"Scrcpy binary: {self.scrcpy_bin}")

        # Detect displays dynamically
        displays = self.get_displays(self.serial)
        if not displays:
            logger.warning("No displays detected via --list-displays. Falling back to default ID 0.")
            displays = ["0"]

        # Assign display IDs. Prefer the profile's configured IDs when both are
        # actually present on the device; otherwise fall back to positional
        # auto-detection from --list-displays.
        prof_top = str(self.profile.top_display_id)
        prof_bottom = str(self.profile.bottom_display_id)
        if prof_top in displays and prof_bottom in displays:
            top_id, bottom_id = prof_top, prof_bottom
            logger.info(f"Using profile display IDs: top={top_id}, bottom={bottom_id}")
        else:
            top_id = displays[0]
            bottom_id = displays[-1] if len(displays) > 1 else None

        # flipped_screens (profile) combined with the user's swap toggle.
        if (bool(self.profile.flipped_screens) ^ bool(swap_screens)) and bottom_id is not None:
            logger.info("Swapping screen order (profile.flipped_screens / user swap).")
            top_id, bottom_id = bottom_id, top_id

        if len(displays) == 1:
             logger.warning("Only one display detected. Dual screen mode might not work as expected.")

        # Set up PipeWire audio routing: game audio → speakers + Discord auto-capture
        scrcpy_env = None
        if self._audio_router:
            env_additions = self._audio_router.setup()
            if env_additions:
                scrcpy_env = {**os.environ, **env_additions}
                logger.info(f"Discord audio routing active ({env_additions})")

        # Base arguments (no --max-fps here — set per window below).
        # Codec tuning + low-latency flags are shared by both windows.
        base = [
            self.scrcpy_bin,
            "-s",
            self.serial,
            "--render-driver",
            DEFAULT_RENDER_DRIVER,
            "--video-codec",
            DEFAULT_VIDEO_CODEC,
            f"--video-codec-options={SCRCPY_CODEC_OPTIONS}",
            "--no-mipmaps",     # skip mipmap generation — sharper, less GPU work
            "--no-power-on",    # don't wake the device when mirroring starts
            "--no-cleanup",     # leave device display state untouched on exit
            "--print-fps",      # emit real on-screen FPS into the per-window log
        ]

        # Only add borderless if NOT on Linux (user requested window controls)
        if sys.platform == "win32":
             base.append("--window-borderless")

        # Enable all mouse bindings
        base.append("--mouse-bind=++++")

        # Calculate bitrates based on resolution
        bitrate_top = f"{max(TOP_BITRATE_MINIMUM, int(TOP_BITRATE_SCALE *
                                                      (self.scale**BITRATE_CALC_SCALE_FACTOR)))}M"
        bitrate_bottom = f"{max(BOTTOM_BITRATE_MINIMUM, int(BOTTOM_BITRATE_SCALE *
                                                            (self.scale**BITRATE_CALC_SCALE_FACTOR)))}M"
        logger.info(f"Video bitrates - Top: {bitrate_top}, Bottom: {bitrate_bottom}")

        # Top window arguments — user-configurable FPS for the main display
        top_fps = str(self.max_fps)
        bottom_fps = str(min(self.max_fps, 60))
        logger.info(f"FPS caps - Top: {top_fps}, Bottom: {bottom_fps}")
        top_args = base + [
            "--display-id",
            top_id,
            "--window-title",
            TOP_SCREEN_WINDOW_TITLE,
            "--window-width",
            str(self.f_w1),
            "--video-bit-rate",
            bitrate_top,
            "--max-fps",
            top_fps,
            "--gamepad=uhid",     # gamepad passthrough on the main screen
        ]

        # Audio only on the top window to avoid conflicts
        if not self.enable_audio_top:
            top_args += ["--no-audio"]
            logger.debug("Audio disabled for top window")
        else:
            logger.debug("Audio enabled for top window")

        # Per-profile extra launch args, then any caller-supplied extras.
        if self.profile.extra_scrcpy_args_top:
            top_args += list(self.profile.extra_scrcpy_args_top)
        if extra_top_args:
            top_args += extra_top_args
            logger.debug(f"Extra top args: {extra_top_args}")

        # Start top screen first
        logger.info(f"Starting TOP window ({TOP_SCREEN_WINDOW_TITLE}) on Display {top_id}")
        logger.debug(f"Top window command: {' '.join(top_args)}")
        p0 = self._start_with_retry(top_args, "top", env=scrcpy_env)

        # Bottom window logic
        if bottom_id and bottom_id != top_id:
            # Wait for top screen to initialise before starting bottom. Some
            # devices need extra settle time (profile.screen_launch_delay).
            bottom_delay = max(DISPLAY_INIT_DELAY, float(self.profile.screen_launch_delay or 0))
            logger.info(f"Waiting {bottom_delay}s before starting bottom window")
            time.sleep(bottom_delay)

            # Bottom window arguments (Always no audio)
            bottom_args = base + [
                "--display-id",
                bottom_id,
                "--window-title",
                BOTTOM_SCREEN_WINDOW_TITLE,
                "--window-width",
                str(self.f_w2),
                "--video-bit-rate",
                bitrate_bottom,
                "--no-audio",
                "--max-fps",
                bottom_fps,
                "--gamepad=disabled",   # gamepad handled by the top screen only
            ]

            # Per-profile extra launch args, then any caller-supplied extras.
            if self.profile.extra_scrcpy_args_bottom:
                bottom_args += list(self.profile.extra_scrcpy_args_bottom)
            if extra_bottom_args:
                bottom_args += extra_bottom_args
                logger.debug(f"Extra bottom args: {extra_bottom_args}")
            
            # Start bottom screen
            logger.info(f"Starting BOTTOM window ({BOTTOM_SCREEN_WINDOW_TITLE}) on Display {bottom_id}")
            logger.debug(f"Bottom window command: {' '.join(bottom_args)}")
            p1 = self._start_with_retry(bottom_args, "bottom", env=scrcpy_env)
            
            return [p for p in [p0, p1] if p]
        
        else:
             logger.info("Skipping bottom window (only 1 display found or same ID)")
             return [p0] if p0 else []

    def _start_with_retry(self, cmd, label, env=None):
        """
        Start a process and retry on failure.
        Logs to ./logs/ if possible.

        Args:
            cmd: Command list to execute
            label: Label for logging (e.g., "top" or "bottom")
            env: Optional environment dict for the subprocess

        Returns:
            Popen instance

        Raises:
            Exception: If all retry attempts fail
        """
        logger.debug(
            f"Starting scrcpy {label} window with {self.scrcpy_retry_count} retry attempts"
        )
        last_exc = None

        for attempt in range(1, self.scrcpy_retry_count + 1):
            try:
                logger.debug(
                    f"Attempt {attempt}/{self.scrcpy_retry_count} for {label} window"
                )

                # Create log file for subprocess output
                logfile = None
                try:
                    logs_dir = os.path.join(os.getcwd(), "logs")
                    os.makedirs(logs_dir, exist_ok=True)
                    stamp = time.strftime("%Y%m%d_%H%M%S")
                    log_path = os.path.join(logs_dir, f"scrcpy_{label}_{stamp}.log")
                    logfile = open(log_path, "w", encoding=LOGFILE_ENCODING)
                    self._log_files.append(logfile)
                    logger.debug(f"Scrcpy {label} output logging to: {log_path}")
                except Exception as LogFileCreationError:
                    logger.warning(f"Failed to create scrcpy log file: {LogFileCreationError}")
                    logfile = None

                # Redirect output to log file
                stdout = logfile if logfile else subprocess.DEVNULL
                stderr = logfile if logfile else subprocess.DEVNULL

                # Build child environment. Disable SDL2 vsync inside scrcpy:
                # with vsync on, SDL_RenderPresent blocks until the monitor's
                # refresh, which on high-refresh panels (144/165/240 Hz) misaligns
                # with the 60 Hz frame stream and causes dropped frames. Off, the
                # renderer presents each decoded frame immediately.
                child_env = dict(env) if env is not None else os.environ.copy()
                child_env["SDL_RENDER_VSYNC"] = "0"

                # Start process
                kwargs = {"env": child_env}
                if sys.platform == "win32":
                    kwargs['creationflags'] = CREATE_NO_WINDOW

                proc = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, **kwargs)

                # Best-effort priority bump so scrcpy stays smooth under load.
                # Negative nice needs privileges; ignore if the OS denies it.
                if hasattr(os, "setpriority"):
                    try:
                        os.setpriority(os.PRIO_PROCESS, proc.pid, SCRCPY_NICE)
                        logger.debug(f"Set scrcpy {label} nice to {SCRCPY_NICE}")
                    except (PermissionError, OSError) as NiceError:
                        logger.debug(f"Could not raise scrcpy {label} priority: {NiceError}")

                # Verify process didn't instantly crash
                time.sleep(SCRCPY_CREATION_DELAY)
                if proc.poll() is not None:
                    raise RuntimeError(
                        f"Scrcpy {label} process died immediately (exit code: {proc.poll()})"
                    )

                # Start process hidden
                self.processes.append(proc)
                logger.info(
                    f"Scrcpy {label} window started successfully (PID: {proc.pid})"
                )
                return proc

            except Exception as ScrcpyStartError:
                last_exc = ScrcpyStartError
                logger.warning(f"Scrcpy {label} start attempt "
                               f"{attempt}/{self.scrcpy_retry_count} failed: {ScrcpyStartError}")
                if attempt < self.scrcpy_retry_count:
                    logger.debug(f"Waiting {SCRCPY_RETRY_DELAY}s before retry...")
                    time.sleep(SCRCPY_RETRY_DELAY)

        # All attempts failed
        logger.error(f"All {self.scrcpy_retry_count} attempts to start scrcpy {label} window failed")
        raise last_exc

    # Check if process is alive
    def _check_process_alive(self):
        """
        Check if any processes that were tracked have died

        Returns the first process that is no longer alive or None if all are running.

        Returns:
            Popen object of dead process or None if all alive
        """
        for processName, process in enumerate(self.processes):
            try:
                if process.poll() is not None:
                    logger.warning(f"Process {processName} "
                                   f"(PID: {process.pid}) is no longer alive (exit code: {process.poll()})")
                    return process
            except Exception as ProcessCheckError:
                logger.error(f"Error checking process {processName} status: {ProcessCheckError}")
                return process
        return None

    # Stop Process
    def stop(self):
        """
        Stop and cleanup all scrcpy windows politely, then forcefully if needed.
        """
        logger.info("=" * LOG_MULT)
        logger.info("Stopping ScrcpyManager")
        logger.info("=" * LOG_MULT)

        # Tear down audio routing before killing processes
        if self._audio_router:
            self._audio_router.teardown()

        if not self.processes:
            logger.info("No scrcpy processes to stop")
            return

        logger.info(f"Stopping {len(self.processes)} scrcpy process(es)")

        # Attempt graceful termination
        for processName, process in enumerate(list(self.processes)):
            try:
                if process.poll() is None:
                    logger.debug(f"Terminating process {processName} (PID: {process.pid})")
                    process.terminate()
                else:
                    logger.debug(f"Process {processName} (PID: {process.pid}) already stopped")
            except Exception as TerminationError:
                logger.warning(f"Error terminating process {processName}: {TerminationError}")

        # Wait for graceful exit, then force-kill remaining processes
        logger.debug("Waiting for processes to terminate gracefully...")
        for processName, process in enumerate(list(self.processes)):
            try:
                if process.poll() is None:
                    process.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
                    logger.debug(f"Process {processName} (PID: {process.pid}) terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"Process {processName} (PID: {process.pid}) did not terminate, forcing kill"
                )
                try:
                    process.kill()
                    logger.debug(f"Process {processName} killed with p.kill()")
                except Exception as ProcessKillError:
                    logger.error(f"Failed to kill process {processName}: {ProcessKillError}")
                    # Last resort -> system kill command
                    if sys.platform == "win32":
                         try:
                             subprocess.run(
                                 ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                                 capture_output=ADB_CAPTURE_OUTPUT,
                                 timeout=ADB_TASKKILL_TIMEOUT,
                             )
                             logger.debug(f"Process {processName} killed with taskkill")
                         except Exception as TaskKillError:
                             logger.error(f"Taskkill also failed: {TaskKillError}")
                    else:
                        try:
                             os.kill(process.pid, signal.SIGKILL)
                             logger.debug(f"Process {processName} killed with SIGKILL")
                        except Exception as SigKillError:
                             logger.error(f"SIGKILL failed: {SigKillError}")

            except Exception as ProcessKillWaitingError:
                logger.error(f"Error waiting for process {processName}: {ProcessKillWaitingError}")

        # Clear process list
        process_count = len(self.processes)
        self.processes = []
        logger.info(f"Cleared {process_count} process(es) from tracking list")

        # Close log files
        for lf in self._log_files:
            try:
                lf.close()
            except Exception:
                pass
        self._log_files = []

        # Device-side cleanup (scrcpy server and app_process)
        if self.serial and self.adb_bin:
            logger.debug(f"Performing device-side cleanup for {self.serial}")

            # Kill scrcpy server
            try:
                logger.debug("Killing scrcpy-server on device")
                result = subprocess.run(
                    [
                        self.adb_bin,
                        "-s",
                        self.serial,
                        "shell",
                        "pkill",
                        "-f",
                        "scrcpy-server",
                    ],
                    capture_output=ADB_CAPTURE_OUTPUT,
                    timeout=SCRCPY_TERMINATE_TIMEOUT,
                )
                if result.returncode == 0:
                    logger.debug("scrcpy-server killed successfully")
                else:
                    logger.debug(f"pkill scrcpy-server returned {result.returncode} (may not have been running)")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout killing scrcpy-server")
            except Exception as ScrcpyKillError:
                logger.warning(f"Error killing scrcpy-server: {ScrcpyKillError}")

            # Kill app_process
            try:
                logger.debug("Killing app_process on device")
                result = subprocess.run(
                    [
                        self.adb_bin,
                        "-s",
                        self.serial,
                        "shell",
                        "pkill",
                        "-f",
                        "app_process",
                    ],
                    capture_output=ADB_CAPTURE_OUTPUT,
                    timeout=SCRCPY_TERMINATE_TIMEOUT,
                )
                if result.returncode == 0:
                    logger.debug("app_process killed successfully")
                else:
                    logger.debug(f"pkill app_process returned {result.returncode} (may not have been running)")
            except subprocess.TimeoutExpired:
                logger.warning("Timeout killing app_process")
            except Exception as AppProcessKillError:
                logger.warning(f"Error killing app_process: {AppProcessKillError}")

            # Remove port forwards
            try:
                logger.debug("Removing ADB port forwards")
                subprocess.run(
                    [self.adb_bin, "-s", self.serial, "forward", "--remove-all"],
                    capture_output=ADB_CAPTURE_OUTPUT,
                    timeout=SCRCPY_TERMINATE_TIMEOUT,
                )
                logger.debug("Port forwards removed")
            except Exception as PortForwardsKillError:
                logger.warning(f"Error removing port forwards: {PortForwardsKillError}")

            # Remove all reverse forwards
            try:
                logger.debug("Removing ADB reverse forwards")
                subprocess.run(
                    [self.adb_bin, "-s", self.serial, "reverse", "--remove-all"],
                    capture_output=ADB_CAPTURE_OUTPUT,
                    timeout=SCRCPY_TERMINATE_TIMEOUT,
                )
                logger.debug("Reverse forwards removed")
            except Exception as ReverseForwardsKillError:
                logger.warning(f"Error removing reverse forwards: {ReverseForwardsKillError}")

            logger.info("Device-side cleanup complete")
        else:
            if not self.serial:
                logger.debug("Skipping device cleanup: no serial")
            if not self.adb_bin:
                logger.debug("Skipping device cleanup: no ADB binary")

        logger.info("ScrcpyManager stopped successfully")
        logger.info("=" * LOG_MULT)

    def scan_network_for_devices(self, subnet=None, port=5555, timeout=0.5, progress_callback=None):
        """
        Scan the local network for Android devices with ADB wireless debugging enabled.
        
        Args:
            subnet: Subnet to scan (e.g., "192.168.1"). If None, auto-detects from default gateway.
            port: Port to check (default: 5555)
            timeout: Timeout for each connection attempt in seconds (default: 0.5 for speed)
            progress_callback: Optional callback function(current, total) for progress updates
            
        Returns:
            list: List of found device IPs
        """
        import socket
        
        if not subnet:
            # Try to auto-detect subnet from default gateway
            try:
                import subprocess
                result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'default' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'via' and i + 1 < len(parts):
                                gateway = parts[i + 1]
                                subnet = '.'.join(gateway.split('.')[:3])
                                logger.info(f"Auto-detected subnet: {subnet}.0/24")
                                break
                        break
            except Exception as e:
                logger.warning(f"Could not auto-detect subnet: {e}")
                subnet = "192.168.1"
        
        logger.info(f"Scanning network {subnet}.0/24 for ADB devices on port {port}...")
        found_devices = []
        checked_count = [0]  # Use list for mutable reference
        count_lock = threading.Lock()
        
        def check_ip(ip):
            """Check if a device is reachable at the given IP."""
            with count_lock:
                checked_count[0] += 1
                current = checked_count[0]
            if progress_callback and current % 10 == 0:
                progress_callback(current, 254)
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    sock.settimeout(timeout)
                    result = sock.connect_ex((ip, port))
                finally:
                    sock.close()
                if result == 0:
                    # Port is open, try to connect with adb
                    try:
                        if self.adb_bin:
                            result = subprocess.run(
                                [self.adb_bin, "connect", f"{ip}:{port}"],
                                capture_output=True,
                                text=True,
                                timeout=3
                            )
                            if "connected" in result.stdout.lower() or "already connected" in result.stdout.lower():
                                logger.debug(f"Found and connected to device: {ip}:{port}")
                                return ip
                    except Exception as e:
                        logger.debug(f"ADB connect to {ip} failed: {e}")
                return None
            except Exception as e:
                return None
        
        # Scan subnet using threads for faster results
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        ip_range = [f"{subnet}.{i}" for i in range(1, 255)]
        logger.info(f"Scanning {len(ip_range)} IPs...")
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ip = {executor.submit(check_ip, ip): ip for ip in ip_range}
            
            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    result = future.result()
                    if result:
                        found_devices.append(result)
                except Exception as e:
                    logger.debug(f"Error checking {ip}: {e}")
        
        logger.info(f"Scan complete. Found {len(found_devices)} device(s): {found_devices}")
        return found_devices
