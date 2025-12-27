"""
Visual Analyzer - UI State Detection.

Uses visual-guard concepts to detect if the UI is in a "blocked" state
(e.g., modal overlays, loading spinners, error screens) without requiring
an LLM for visual analysis.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


@dataclass
class VisualState:
    """Represents the current visual state of the page."""
    is_blocked: bool
    reason: str
    blocking_element_selector: Optional[str] = None
    page_ready: bool = True
    has_overlay: bool = False
    has_spinner: bool = False
    has_error: bool = False


class VisualAnalyzer:
    """
    Detects visual UI states that might block exploration.
    
    This analyzer uses DOM heuristics and CSS analysis to detect
    blocking states, avoiding the need for expensive LLM vision.
    
    Example:
        >>> analyzer = VisualAnalyzer(driver)
        >>> is_blocked, reason = analyzer.is_blocked()
        >>> if is_blocked:
        ...     print(f"UI blocked: {reason}")
    """
    
    # Common overlay/modal selectors
    OVERLAY_SELECTORS = [
        ".modal",
        ".overlay",
        ".popup",
        "[role='dialog']",
        "[role='alertdialog']",
        ".lightbox",
        ".modal-backdrop",
        ".modal-overlay",
        "[data-modal]",
        ".ReactModal__Overlay",
        ".MuiDialog-root",
        ".ant-modal-mask",
    ]
    
    # Common loading indicator selectors
    SPINNER_SELECTORS = [
        ".spinner",
        ".loading",
        ".loader",
        "[role='progressbar']",
        ".progress",
        ".sk-spinner",
        ".lds-ring",
        ".loading-indicator",
        "[data-loading]",
        ".MuiCircularProgress-root",
        ".ant-spin",
    ]
    
    # Common error indicator selectors
    ERROR_SELECTORS = [
        ".error",
        ".alert-danger",
        ".alert-error",
        "[role='alert']",
        ".error-message",
        ".notification-error",
        ".toast-error",
    ]
    
    # Captcha indicator patterns
    CAPTCHA_PATTERNS = [
        "captcha",
        "recaptcha",
        "hcaptcha",
        "challenge",
        "verify you're human",
        "prove you're not a robot",
        "security check",
    ]
    
    def __init__(self, driver: "WebDriver"):
        """
        Initialize the visual analyzer.
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self._guard = self._init_visual_guard()
        self.visual_agent = self._init_visual_agent()
    
    def _init_visual_guard(self):
        """Try to initialize visual-guard if available."""
        try:
            from visual_guard import VisualGuard
            return VisualGuard(self.driver)
        except ImportError:
            return None

    def _init_visual_agent(self):
        """Initialize the VisualAgent bridge."""
        from .visual_agent import VisualAgent
        return VisualAgent()
    
    def is_blocked(self) -> Tuple[bool, str]:
        """
        Check if UI interaction is currently blocked.
        
        Returns:
            Tuple of (is_blocked: bool, reason: str)
        """
        # Check for modal overlays
        overlay_result = self._has_modal_overlay()
        if overlay_result[0]:
            return overlay_result
        
        # Check for loading spinners
        spinner_result = self._has_loading_spinner()
        if spinner_result[0]:
            return spinner_result
        
        # Check for captcha challenges
        captcha_result = self._has_captcha()
        if captcha_result[0]:
            return captcha_result
        
        # Check for page load state
        if not self._is_page_ready():
            return True, "Page still loading"
        
        return False, "Ready"
    
    def get_visual_state(self) -> VisualState:
        """Get detailed visual state information."""
        overlay_blocked, overlay_reason = self._has_modal_overlay()
        spinner_blocked, spinner_reason = self._has_loading_spinner()
        error_detected = self._has_error_message()
        
        is_blocked = overlay_blocked or spinner_blocked
        reason = overlay_reason if overlay_blocked else (spinner_reason if spinner_blocked else "Ready")
        
        return VisualState(
            is_blocked=is_blocked,
            reason=reason,
            page_ready=self._is_page_ready(),
            has_overlay=overlay_blocked,
            has_spinner=spinner_blocked,
            has_error=error_detected,
        )
    
    def _has_modal_overlay(self) -> Tuple[bool, str]:
        """Check for visible modal overlays using a single fast JavaScript query."""
        try:
            # Combined check in single JavaScript execution for speed
            script = """
            const selectors = ['.modal', '.overlay', '.popup', '[role="dialog"]', 
                              '[role="alertdialog"]', '.lightbox', '.modal-backdrop',
                              '.modal-overlay', '[data-modal]', '.ReactModal__Overlay',
                              '.MuiDialog-root', '.ant-modal-mask'];
            
            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                for (const el of elements) {
                    if (el.offsetParent !== null) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 100 && rect.height > 100) {
                            return {blocked: true, reason: 'Modal overlay: ' + selector};
                        }
                    }
                }
            }
            
            // Quick check for full-screen fixed overlays
            const fixed = document.querySelectorAll('[style*="position: fixed"], [style*="position:fixed"]');
            for (const el of fixed) {
                const rect = el.getBoundingClientRect();
                if (rect.width > window.innerWidth * 0.8 && rect.height > window.innerHeight * 0.8) {
                    const style = window.getComputedStyle(el);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        return {blocked: true, reason: 'Full-screen overlay'};
                    }
                }
            }
            
            return {blocked: false, reason: ''};
            """
            result = self.driver.execute_script(script)
            if result and result.get('blocked'):
                return True, result.get('reason', 'Modal overlay detected')
        except Exception:
            pass
        
        return False, ""
    
    def _has_loading_spinner(self) -> Tuple[bool, str]:
        """Check for visible loading indicators using a single fast JavaScript query."""
        try:
            script = """
            const selectors = ['.spinner', '.loading', '.loader', '[role="progressbar"]',
                              '.progress', '.sk-spinner', '.lds-ring', '.loading-indicator',
                              '[data-loading]', '.MuiCircularProgress-root', '.ant-spin'];
            
            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                for (const el of elements) {
                    if (el.offsetParent !== null) {
                        return {blocked: true, reason: 'Spinner: ' + selector};
                    }
                }
            }
            
            return {blocked: false, reason: ''};
            """
            result = self.driver.execute_script(script)
            if result and result.get('blocked'):
                return True, result.get('reason', 'Loading spinner detected')
        except Exception:
            pass
        
        return False, ""
    
    def _has_captcha(self) -> Tuple[bool, str]:
        """Check for captcha challenges."""
        try:
            page_source = self.driver.page_source.lower()
            
            for pattern in self.CAPTCHA_PATTERNS:
                if pattern in page_source:
                    return True, f"Captcha detected ({pattern})"
            
            # Check for iframe-based captchas
            iframes = self.driver.find_elements("tag name", "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src") or ""
                title = iframe.get_attribute("title") or ""
                
                for pattern in self.CAPTCHA_PATTERNS:
                    if pattern in src.lower() or pattern in title.lower():
                        return True, f"Captcha iframe detected ({pattern})"
        except Exception:
            pass
        
        return False, ""
    
    def _has_error_message(self) -> bool:
        """Check for visible error messages."""
        for selector in self.ERROR_SELECTORS:
            try:
                elements = self.driver.find_elements("css selector", selector)
                for elem in elements:
                    if elem.is_displayed():
                        return True
            except Exception:
                continue
        
        return False
    
    def _is_page_ready(self) -> bool:
        """Check if the page has finished loading."""
        try:
            # Check document ready state
            ready_state = self.driver.execute_script("return document.readyState")
            if ready_state != "complete":
                return False
            
            # Check for pending AJAX requests (jQuery)
            try:
                jquery_active = self.driver.execute_script(
                    "return typeof jQuery !== 'undefined' ? jQuery.active : 0"
                )
                if jquery_active > 0:
                    return False
            except Exception:
                pass
            
            return True
        except Exception:
            return True  # Assume ready if we can't check
    
    def capture_state_snapshot(self, name: str) -> Optional[str]:
        """
        Capture current UI state as a screenshot.
        
        Args:
            name: Name for the snapshot
        
        Returns:
            Path to saved screenshot, or None if visual-guard not available
        """
        if self._guard:
            try:
                return self._guard.capture(name)
            except Exception:
                pass
        
        # Fallback to basic screenshot
        try:
            path = f"./screenshots/{name}.png"
            self.driver.save_screenshot(path)
            return path
        except Exception:
            return None
