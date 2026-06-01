from Xlib import display, X, protocol, error as Xerror
from Xlib.protocol import event
from . import DockManager
import logging
import time

logger = logging.getLogger(__name__)

class X11DockManager(DockManager):
    """
    Linux X11 implementation of the DockManager.
    Uses python-xlib to manage window parenting and state.
    """
    def __init__(self):
        super().__init__()
        try:
            self.disp = display.Display()
            self.root = self.disp.screen().root
            logger.info("Connected to X Server")
        except Exception as e:
            logger.error(f"Failed to connect to X Server: {e}")
            raise

    def create_container(self, x, y, w, h):
        """Create a simple black window to act as container"""
        try:
            screen = self.disp.screen()
            window = screen.root.create_window(
                x, y, w, h, 0,
                screen.root_depth,
                X.InputOutput,
                X.CopyFromParent,
                background_pixel=screen.black_pixel,
                event_mask=X.StructureNotifyMask | X.ExposureMask
            )
            # Set title
            window.set_wm_name('DualCPY Container')
            window.set_wm_icon_name('DualCPY')
            
            # Map (show) it
            window.map()
            self.disp.sync()
            
            self.hwnd_container = window.id
            logger.info(f"Created X11 Container Window: {window.id}")
            return window.id
        except Exception as e:
            logger.error(f"Failed to create container window: {e}")
            return None

    def get_container_geometry(self):
        """Return the container's (x, y, w, h) in absolute root coordinates."""
        try:
            if not self.hwnd_container:
                return None
            win = self.disp.create_resource_object('window', self.hwnd_container)
            geom = win.get_geometry()
            abs_pos = self.root.translate_coords(win, 0, 0)
            return (abs_pos.x, abs_pos.y, geom.width, geom.height)
        except Exception as e:
            logger.debug(f"get_container_geometry failed: {e}")
            return None

    def process_events(self):
        """Consume X11 events to keep the container responsive"""
        try:
            while self.disp.pending_events():
                event = self.disp.next_event()
                # We can handle specific events here if needed, e.g. ConfigureNotify
        except Exception:
            pass


    def _get_window_name(self, window):
        """Get window name safely"""
        try:
            name = window.get_wm_name()
            if not name:
                # Try _NET_WM_NAME
                NET_WM_NAME = self.disp.intern_atom('_NET_WM_NAME')
                try:
                    name = window.get_full_property(NET_WM_NAME, 0).value
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                except:
                    pass
            return name
        except Exception:
            return None

    def find_window(self, title):
        """
        Find a window by title.
        Traverses the _NET_CLIENT_LIST if available, otherwise tree traversal.
        """
        try:
            NET_CLIENT_LIST = self.disp.intern_atom('_NET_CLIENT_LIST')
            windows = self.root.get_full_property(NET_CLIENT_LIST, X.AnyPropertyType)
            
            if windows:
                window_ids = windows.value
                for win_id in window_ids:
                    try:
                        win = self.disp.create_resource_object('window', win_id)
                        name = self._get_window_name(win)
                        if name and title.lower() in name.lower():
                            logger.info(f"Found window '{name}' with ID {win_id}")
                            return win_id
                    except Exception:
                        continue
            
            # Fallback: Tree traversal (expensive, but necessary if no client list)
            # Implemented simplified recursive search if needed, but client list usually works.
            logger.debug(f"Window '{title}' not found in _NET_CLIENT_LIST")
            return None

        except Exception as e:
            logger.error(f"Error finding window: {e}")
            return None

    def dock_window(self, window_id, parent_id):
        """
        Embed window_id into parent_id.
        Removes decorations and reparents.
        """
        try:
            if not window_id or not parent_id:
                return

            win = self.disp.create_resource_object('window', window_id)
            parent = self.disp.create_resource_object('window', parent_id)

            # Remove decorations (Motif hints)
            # MWM_HINTS_DECORATIONS = (1L << 1)
            # prop = struct.pack('LLLLL', 2, 0, 0, 0, 0) 
            # This is complex in python-xlib without struct, but let's try a simpler approach first
            # Or just rely on scrcpy --window-borderless which we already use!
            # The win32 version explicitly removed styles. Scrcpy is launched borderless, so we might be fine.
            # But we ensure it's mapped.

            # Reparent
            logger.info(f"Docking window {window_id} into {parent_id}")
            win.reparent(parent_id, 0, 0)
            win.map() # Ensure it's visible
            self.disp.sync()
            
            if window_id == self.hwnd_top:
                 pass # already tracked
            
            return True
        except Exception as e:
            logger.error(f"Error docking window: {e}")
            return False

    def undock_window(self, window_id):
        """
        Reparent back to root.
        """
        try:
            if not window_id:
                return

            win = self.disp.create_resource_object('window', window_id)
            logger.info(f"Undocking window {window_id} to root")
            
            win.reparent(self.root.id, 0, 0)
            win.map()
            self.disp.sync()
            return True
        except Exception as e:
            logger.error(f"Error undocking window: {e}")
            return False

    def sync_layout(self, tx, ty, bx, by, w1, h1, w2, h2, is_docked=True):
        """
        Resize/Move windows.
        """
        try:
            if self.hwnd_top:
                try:
                    top_win = self.disp.create_resource_object('window', self.hwnd_top)
                    top_win.configure(x=int(tx), y=int(ty), width=int(w1), height=int(h1))
                except Xerror.BadWindow:
                    logger.debug("Top window no longer valid, clearing hwnd_top")
                    self.hwnd_top = None

            if self.hwnd_bottom:
                try:
                    bot_win = self.disp.create_resource_object('window', self.hwnd_bottom)
                    bot_win.configure(x=int(bx), y=int(by), width=int(w2), height=int(h2))
                except Xerror.BadWindow:
                    logger.debug("Bottom window no longer valid, clearing hwnd_bottom")
                    self.hwnd_bottom = None

            self.disp.flush()

        except Exception as e:
            logger.error(f"Error syncing layout: {e}")

    def resize_container(self, container_id, w, h):
        """Resize the container window."""
        try:
            win = self.disp.create_resource_object('window', container_id)
            win.configure(width=int(w), height=int(h))
            self.disp.sync()
        except Exception as e:
            logger.error(f"Error resizing container: {e}")

    def destroy_container(self, container_id):
        """Destroy the container window so it no longer appears on screen."""
        try:
            win = self.disp.create_resource_object('window', container_id)
            win.destroy()
            self.disp.sync()
            logger.info(f"Destroyed container window {container_id}")
        except Exception as e:
            logger.error(f"Error destroying container: {e}")

    def set_container_visible(self, container_id, visible):
        """Map (show) or unmap (hide) the container window."""
        try:
            win = self.disp.create_resource_object('window', container_id)
            if visible:
                win.map()
            else:
                win.unmap()
            self.disp.sync()
        except Exception as e:
            logger.error(f"Error setting container visibility: {e}")

    def set_window_simple_focus(self, window_id):
        try:
            if not window_id: return
            win = self.disp.create_resource_object('window', window_id)
            win.set_input_focus(X.RevertToParent, X.CurrentTime)
            win.configure(stack_mode=X.Above)
            self.disp.sync()
        except Exception as e:
             logger.error(f"Error checking focus: {e}")
