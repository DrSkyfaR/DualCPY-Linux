from abc import ABC, abstractmethod

class DockManager(ABC):
    """
    Abstract base class for platform-specific window docking managers.
    Handles finding, embedding, sizing, and styling of external application windows.
    """

    def __init__(self):
        self.hwnd_container = None
        self.hwnd_top = None
        self.hwnd_bottom = None

    @abstractmethod
    def create_container(self, x, y, w, h):
        """
        Create a container window to hold the docked windows.
        Returns the window handle/ID.
        """
        pass

    @abstractmethod
    def process_events(self):
        """
        Process platform-specific window events (e.g. X11 events or Win32 messages).
        Should be called in the main loop.
        """
        pass

    @abstractmethod
    def find_window(self, title):
        """
        Find a window by its title.
        Returns a handle/ID to the window or None if not found.
        """
        pass

    @abstractmethod
    def dock_window(self, window_id, parent_id):
        """
        Embed a window into a parent window.
        Should remove decorations and set the parent.
        """
        pass

    @abstractmethod
    def undock_window(self, window_id):
        """
        Restore a window to its native state (floating, decorated).
        """
        pass

    @abstractmethod
    def sync_layout(self, tx, ty, bx, by, w1, h1, w2, h2, is_docked=True):
        """
        Update the positions of the top and bottom windows.
        
        Args:
            tx, ty: Top window x/y
            bx, by: Bottom window x/y
            w1, h1: Top window width/height
            w2, h2: Bottom window width/height
            is_docked: True if windows are currently docked in container
        """
        pass
    
    @abstractmethod
    def set_window_simple_focus(self, window_id):
        """
        Bring a window to the foreground/focus it.
        """
        pass

    def set_container_visible(self, container_id, visible):
        """
        Show or hide the container window.
        Default no-op — override on platforms that support it.
        """
        pass

    def destroy_container(self, container_id):
        """
        Destroy the container window entirely.
        Default no-op — override on platforms that support it.
        """
        pass

    def get_container_geometry(self):
        """
        Return the container's (x, y, w, h) in absolute screen coordinates,
        or None if unavailable. Default None — override where supported.
        """
        return None
