"""
Teleporter - Session and Context Management.

Uses selenium-teleport concepts to save/restore browser state
and navigate between complex window/iframe contexts.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import json
import os
from pathlib import Path

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


@dataclass
class SessionState:
    """Represents saved browser session state."""
    cookies: List[Dict[str, Any]]
    local_storage: Dict[str, str]
    session_storage: Dict[str, str]
    url: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "cookies": self.cookies,
            "local_storage": self.local_storage,
            "session_storage": self.session_storage,
            "url": self.url,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Create from dictionary."""
        return cls(
            cookies=data.get("cookies", []),
            local_storage=data.get("local_storage", {}),
            session_storage=data.get("session_storage", {}),
            url=data.get("url", ""),
        )


class Teleporter:
    """
    Save and restore browser state to skip login flows.
    
    This is particularly useful for:
    - Skipping authentication for repeated tests
    - Preserving state across test runs
    - Navigating complex multi-window applications
    
    Example:
        >>> teleporter = Teleporter(driver)
        >>> # After logging in...
        >>> teleporter.save_state("logged_in")
        >>> # In a new session...
        >>> teleporter.restore_state("logged_in")
    """
    
    def __init__(
        self,
        driver: "WebDriver",
        state_dir: str = "./.sentinel_states",
    ):
        """
        Initialize the teleporter.
        
        Args:
            driver: Selenium WebDriver instance
            state_dir: Directory to save state files
        """
        self.driver = driver
        self.state_dir = state_dir
        self._init_teleport_lib()
        
        # Ensure state directory exists
        os.makedirs(state_dir, exist_ok=True)
    
    def _init_teleport_lib(self) -> None:
        """Find selenium-teleport; each instance needs its own state file path."""
        try:
            from selenium_teleport import Teleport
            self._teleport = Teleport
            self._has_teleport = True
        except ImportError:
            self._teleport = None
            self._has_teleport = False
    
    def save_state(self, name: str) -> str:
        """
        Save current browser state.
        
        Args:
            name: Name for the saved state
        
        Returns:
            Path to the saved state file
        """
        state_path = self._state_path(name)
        if self._has_teleport:
            self._teleport(self.driver, state_path).save()
            return state_path
        
        # Fallback implementation
        state = self._capture_state()
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2)
        
        return state_path
    
    def restore_state(self, name: str) -> bool:
        """
        Restore a previously saved browser state.
        
        Args:
            name: Name of the saved state
        
        Returns:
            True if state was restored successfully
        """
        try:
            state_path = self._state_path(name)
        except ValueError:
            return False
        if not os.path.exists(state_path):
            return False
        
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if self._has_teleport and "metadata" in data:
                destination_url = data["metadata"]["source_url"]
                self._teleport(self.driver, state_path).load(destination_url)
                return True
            
            # Continue accepting states saved by the fallback implementation.
            state = SessionState.from_dict(data)
            self._apply_state(state)
            return True
        except Exception:
            return False
    
    def list_states(self) -> List[str]:
        """List all saved states."""
        states = []
        for file in os.listdir(self.state_dir):
            if file.endswith(".json"):
                states.append(file[:-5])  # Remove .json extension
        return states
    
    def delete_state(self, name: str) -> bool:
        """Delete a saved state."""
        try:
            state_path = self._state_path(name)
            os.remove(state_path)
            return True
        except Exception:
            return False

    def _state_path(self, name: str) -> str:
        """Keep named browser state files inside their configured directory."""
        if not isinstance(name, str) or not name or name in {".", ".."}:
            raise ValueError("State name must be a non-empty filename")
        if any(character in name for character in '/\\\x00:'):
            raise ValueError("State name must not contain path separators")
        root = Path(self.state_dir).resolve()
        path = root / f"{name}.json"
        if path.resolve().parent != root:
            raise ValueError("State file must remain inside the state directory")
        return str(path)
    
    def _capture_state(self) -> SessionState:
        """Capture current browser state."""
        # Get cookies
        cookies = self.driver.get_cookies()
        
        # Get local storage
        try:
            local_storage = self.driver.execute_script(
                "return Object.fromEntries(Object.entries(localStorage))"
            )
        except Exception:
            local_storage = {}
        
        # Get session storage
        try:
            session_storage = self.driver.execute_script(
                "return Object.fromEntries(Object.entries(sessionStorage))"
            )
        except Exception:
            session_storage = {}
        
        return SessionState(
            cookies=cookies,
            local_storage=local_storage or {},
            session_storage=session_storage or {},
            url=self.driver.current_url,
        )
    
    def _apply_state(self, state: SessionState) -> None:
        """Apply a saved state to the browser."""
        # Navigate to the URL first (cookies need matching domain)
        if state.url:
            self.driver.get(state.url)
        
        # Clear existing cookies
        self.driver.delete_all_cookies()
        
        # Add saved cookies
        for cookie in state.cookies:
            try:
                # Remove problematic fields that might cause issues
                cookie_copy = {k: v for k, v in cookie.items() 
                             if k not in ["sameSite", "expiry"]}
                self.driver.add_cookie(cookie_copy)
            except Exception:
                pass
        
        # Set local storage
        for key, value in state.local_storage.items():
            try:
                self.driver.execute_script(
                    "localStorage.setItem(arguments[0], arguments[1]);", key, value
                )
            except Exception:
                pass
        
        # Set session storage
        for key, value in state.session_storage.items():
            try:
                self.driver.execute_script(
                    "sessionStorage.setItem(arguments[0], arguments[1]);", key, value
                )
            except Exception:
                pass
        
        # Refresh to apply state
        self.driver.refresh()
    
    # Context switching methods
    
    def switch_to_frame(self, identifier) -> bool:
        """
        Switch to an iframe by name, index, or element.
        
        Args:
            identifier: Frame name, index, or WebElement
        
        Returns:
            True if switch was successful
        """
        try:
            self.driver.switch_to.frame(identifier)
            return True
        except Exception:
            return False
    
    def switch_to_parent_frame(self) -> bool:
        """Switch to the parent frame."""
        try:
            self.driver.switch_to.parent_frame()
            return True
        except Exception:
            return False
    
    def switch_to_default_content(self) -> bool:
        """Switch to the main document."""
        try:
            self.driver.switch_to.default_content()
            return True
        except Exception:
            return False
    
    def switch_to_window(self, handle: str) -> bool:
        """
        Switch to a window by handle.
        
        Args:
            handle: Window handle
        
        Returns:
            True if switch was successful
        """
        try:
            self.driver.switch_to.window(handle)
            return True
        except Exception:
            return False
    
    def get_window_handles(self) -> List[str]:
        """Get all window handles."""
        return self.driver.window_handles
    
    def get_current_window(self) -> str:
        """Get current window handle."""
        return self.driver.current_window_handle
    
    def open_new_window(self) -> str:
        """Open a new window and return its handle."""
        try:
            self.driver.execute_script("window.open()")
            handles = self.driver.window_handles
            return handles[-1]
        except Exception:
            return ""
    
    def close_current_window(self) -> bool:
        """Close the current window."""
        try:
            self.driver.close()
            # Switch to another window if available
            handles = self.driver.window_handles
            if handles:
                self.driver.switch_to.window(handles[0])
            return True
        except Exception:
            return False
