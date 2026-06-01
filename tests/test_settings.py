import sys
import os
import time
import json
import logging

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.launcher
from src.config import ConfigManager

# Mocking things
class MockUI:
    def __init__(self, launcher):
        self.l = launcher
        self.show_settings = False
    def render(self):
        pass
    def handle_event(self, event):
        pass

# The control panel UI is created lazily inside launch(); these tests never call
# launch(), so no UI patch is required.

import src.scrcpy_manager
class MockScrcpy:
    def __init__(self, scale=1.0, **kwargs):
        self.f_w1 = 100
        self.f_h1 = 100
        self.f_w2 = 100
        self.f_h2 = 100
        self.serial = None
        self.max_fps = 120
    def detect_device(self):
        return "mock_serial"
    def start_scrcpy(self, serial, swap_screens=False):
        print(f"Mock Scrcpy started with swap_screens={swap_screens}")
    def stop(self):
        print("Mock Scrcpy stopped")
    def is_running(self):
        return True

src.launcher.ScrcpyManager = MockScrcpy
src.scrcpy_manager.ScrcpyManager = MockScrcpy # Just in case

def test_settings_persistence():
    print("Testing Settings Persistence...")
    
    # Initialize Launcher
    # We need to suppress pygame init which might happen elsewhere?
    # Launcher init:
    # self.ui = PygameUI(self) -> MockUI(self)
    
    launcher = src.launcher.Launcher()
    
    # Check initial state (should be False by default)
    print(f"Initial swap_screens: {launcher.swap_screens}")
    
    # Change setting
    print("Saving swap_screens = True")
    launcher.save_swap_screens(True)
    
    if launcher.swap_screens:
        print("PASS: In-memory value updated")
    else:
        print("FAIL: In-memory value NOT updated")
        
    # Check config file (reload via launcher's config manager to be sure, or new instance)
    # Using launcher.config directly verifies the object state.
    # To verify persistence, we should reload.
    
    config = ConfigManager("config/config.json")
    saved_val = config.get("swap_screens")
    if saved_val:
        print("PASS: Config file updated")
    else:
        print(f"FAIL: Config file value is {saved_val}")
        
    # Test Restart Logic
    print("Testing Restart Logic...")
    launcher.restart_scrcpy()
    # verify output contains "Mock Scrcpy started with swap_screens=True"
    
    # Cleanup
    launcher.save_swap_screens(False) # Reset

if __name__ == "__main__":
    try:
        test_settings_persistence()
        print("\nTEST COMPLETED")
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
