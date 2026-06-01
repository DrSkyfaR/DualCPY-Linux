
import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_linux_port")

def check_imports():
    logger.info("Checking imports...")
    try:
        import src.launcher
        logger.info("src.launcher imported successfully")
    except ImportError as e:
        logger.error(f"Failed to import src.launcher: {e}")
        return False
    except Exception as e:
        logger.error(f"Error importing src.launcher: {e}")
        return False

    try:
        import src.control_panel
        logger.info("src.control_panel imported successfully")
    except ImportError as e:
        logger.error(f"Failed to import src.control_panel: {e}")
        return False
    except Exception as e:
        logger.error(f"Error importing src.control_panel: {e}")
        return False

    try:
        import src.scrcpy_manager
        logger.info("src.scrcpy_manager imported successfully")
    except ImportError as e:
        logger.error(f"Failed to import src.scrcpy_manager: {e}")
        return False
    except Exception as e:
        logger.error(f"Error importing src.scrcpy_manager: {e}")
        return False
        
    try:
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
             import src.docking.stateless
             logger.info("src.docking.stateless imported successfully (Wayland detected)")
        else:
             import src.docking.x11
             logger.info("src.docking.x11 imported successfully")
    except ImportError as e:
        if sys.platform.startswith("linux"):
            logger.error(f"Failed to import docking module: {e}")
            return False
        else:
            logger.warning(f"Failed to import src.docking.x11 (expected on non-Linux): {e}")
    except Exception as e:
        logger.error(f"Error importing src.docking.x11: {e}")
        return False
        
    # Check if win32 modules can be imported without crashing on Linux
    try:
        import src.win32_dock
        logger.info("src.win32_dock imported successfully (safe check)")
    except Exception as e:
        logger.error(f"src.win32_dock import failed: {e}")
        return False
        
    try:
        import src.win32_darkmode
        logger.info("src.win32_darkmode imported successfully (safe check)")
    except Exception as e:
        logger.error(f"src.win32_darkmode import failed: {e}")
        return False

    return True

def check_instantiation():
    logger.info("Checking class instantiation...")
    
    if sys.platform.startswith("linux"):
        try:
            if os.environ.get("XDG_SESSION_TYPE") == "wayland":
                from src.docking.stateless import StatelessDockManager
                dock = StatelessDockManager()
                logger.info("StatelessDockManager instantiated successfully")
            else:
                from src.docking.x11 import X11DockManager
                dock = X11DockManager()
                logger.info("X11DockManager instantiated successfully")

        except Exception as e:
            # It might fail if no X server is present, which is expected in some CI/headless envs
            # But we are likely in an environment with X or Xvfb if user is running Linux desktop tools
            if "DISPLAY" not in os.environ and os.environ.get("XDG_SESSION_TYPE") != "wayland":
                 logger.warning("DISPLAY not set, X11DockManager instantiation failure expected.")
            elif os.environ.get("XDG_SESSION_TYPE") == "wayland":
                 logger.error(f"StatelessDockManager instantiation failed: {e}")
                 return False
            else:
                 logger.error(f"X11DockManager instantiation failed: {e}")
                 return False

    try:
        from src.scrcpy_manager import ScrcpyManager
        mgr = ScrcpyManager()
        logger.info("ScrcpyManager instantiated successfully")
    except Exception as e:
        logger.error(f"ScrcpyManager instantiation failed: {e}")
        return False

    return True

if __name__ == "__main__":
    logger.info(f"Running on platform: {sys.platform}")
    if check_imports() and check_instantiation():
        logger.info("Verification PASSED")
        sys.exit(0)
    else:
        logger.error("Verification FAILED")
        sys.exit(1)
