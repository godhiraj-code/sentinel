"""
Action Executor - Reliable UI Interactions.

Wraps all actions in waitless quiescence logic to ensure
the page is fully stable before and after each action.
"""

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING
import time

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement
    from sentinel.layers.sense.dom_mapper import ElementNode
    from sentinel.layers.intelligence.decision_engine import Decision


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    action: str
    target: str
    duration_ms: float
    error: Optional[str] = None
    screenshot_path: Optional[str] = None


class ActionExecutor:
    """
    Execute actions with guaranteed stability.
    
    All actions are wrapped with:
    - Pre-action stability wait (via waitless if available)
    - Automatic scrolling to element
    - Retry logic for transient failures
    - Post-action stability wait
    
    Example:
        >>> executor = ActionExecutor(driver)
        >>> result = executor.click(element_node)
        >>> if result.success:
        ...     print("Click successful!")
    """
    
    # Default retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY_MS = 500
    
    def __init__(
        self,
        driver: "WebDriver",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the action executor.
        
        Args:
            driver: Selenium WebDriver (optionally wrapped with waitless)
            timeout: Default timeout for actions in seconds
            max_retries: Maximum retry attempts for failed actions
        """
        self.driver = driver
        self.timeout = timeout
        self.max_retries = max_retries
        self._has_waitless = self._check_waitless_support()
    
    def _check_waitless_support(self) -> bool:
        """Check if driver has waitless stability features."""
        # Check for waitless wrapper markers
        return hasattr(self.driver, "_waitless_wrapped")
    
    def execute(self, decision: "Decision") -> bool:
        """
        Execute a decision from the intelligence layer.
        
        Args:
            decision: Decision object with action and target
        
        Returns:
            True if action succeeded, False otherwise
        """
        action = decision.action.lower()
        target = decision.target
        
        if action == "click":
            return self.click_selector(target)
        elif action == "type":
            text = decision.metadata.get("text", "") if hasattr(decision, "metadata") else ""
            return self.type_text_selector(target, text)
        elif action == "scroll":
            return self.scroll_to_selector(target)
        elif action == "wait":
            duration = decision.metadata.get("duration", 1) if hasattr(decision, "metadata") else 1
            return self.wait(duration)
        elif action == "navigate":
            return self.navigate(target)
        elif action == "goal_achieved":
            return True  # Signal that goal is complete
        else:
            return False
    
    def click(self, element_node: "ElementNode") -> ActionResult:
        """
        Click an element with automatic stability wait.
        
        Args:
            element_node: ElementNode from DOM mapper
        
        Returns:
            ActionResult with success status
        """
        start_time = time.time()
        
        try:
            element = self._resolve_element(element_node)
            if element is None:
                return ActionResult(
                    success=False,
                    action="click",
                    target=element_node.selector,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="Element not found",
                )
            
            # Scroll element into view
            self._scroll_into_view(element)
            
            # Wait for stability
            self._wait_for_stability()
            
            # Perform click with retries
            for attempt in range(self.max_retries):
                try:
                    element.click()
                    
                    # Post-click stability wait
                    self._wait_for_stability()
                    
                    return ActionResult(
                        success=True,
                        action="click",
                        target=element_node.selector,
                        duration_ms=(time.time() - start_time) * 1000,
                    )
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise e
                    time.sleep(self.RETRY_DELAY_MS / 1000)
                    
        except Exception as e:
            return ActionResult(
                success=False,
                action="click",
                target=element_node.selector,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )
    
    def click_selector(self, selector: str) -> bool:
        """
        Click an element by CSS selector.
        
        Args:
            selector: CSS selector or shadow path
        
        Returns:
            True if click succeeded
        """
        start_time = time.time()
        
        try:
            element = self._find_element(selector)
            if element is None:
                return False
            
            self._scroll_into_view(element)
            self._wait_for_stability()
            
            for attempt in range(self.max_retries):
                try:
                    element.click()
                    self._wait_for_stability()
                    return True
                except Exception:
                    if attempt == self.max_retries - 1:
                        return False
                    time.sleep(self.RETRY_DELAY_MS / 1000)
            
            return False
        except Exception:
            return False
    
    def type_text(self, element_node: "ElementNode", text: str, clear_first: bool = True) -> ActionResult:
        """
        Type text into an element.
        
        Args:
            element_node: ElementNode from DOM mapper
            text: Text to type
            clear_first: Whether to clear the field first
        
        Returns:
            ActionResult with success status
        """
        start_time = time.time()
        
        try:
            element = self._resolve_element(element_node)
            if element is None:
                return ActionResult(
                    success=False,
                    action="type",
                    target=element_node.selector,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="Element not found",
                )
            
            self._scroll_into_view(element)
            self._wait_for_stability()
            
            if clear_first:
                element.clear()
            
            element.send_keys(text)
            
            self._wait_for_stability()
            
            return ActionResult(
                success=True,
                action="type",
                target=element_node.selector,
                duration_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action="type",
                target=element_node.selector,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )
    
    def type_text_selector(self, selector: str, text: str, clear_first: bool = True, submit: bool = True) -> bool:
        """
        Type text into an element by selector.
        
        Args:
            selector: CSS selector
            text: Text to type
            clear_first: Clear the field before typing
            submit: Press Enter after typing (for form fields)
        """
        try:
            from selenium.webdriver.common.keys import Keys
            
            element = self._find_element(selector)
            if element is None:
                return False
            
            self._scroll_into_view(element)
            self._wait_for_stability()
            
            # Click to focus
            element.click()
            
            if clear_first:
                element.clear()
            
            element.send_keys(text)
            
            # Press Enter to submit (common pattern for todo apps, search boxes, etc.)
            if submit:
                element.send_keys(Keys.RETURN)
            
            self._wait_for_stability()
            
            return True
        except Exception as e:
            import warnings
            warnings.warn(f"type_text_selector failed: {e}")
            return False
    
    def scroll_to(self, element_node: "ElementNode") -> ActionResult:
        """Scroll an element into view."""
        start_time = time.time()
        
        try:
            element = self._resolve_element(element_node)
            if element is None:
                return ActionResult(
                    success=False,
                    action="scroll",
                    target=element_node.selector,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="Element not found",
                )
            
            self._scroll_into_view(element)
            
            return ActionResult(
                success=True,
                action="scroll",
                target=element_node.selector,
                duration_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action="scroll",
                target=element_node.selector,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )
    
    def scroll_to_selector(self, selector: str) -> bool:
        """Scroll an element into view by selector."""
        try:
            element = self._find_element(selector)
            if element:
                self._scroll_into_view(element)
                return True
            return False
        except Exception:
            return False
    
    def wait(self, seconds: float) -> bool:
        """Wait for a specified duration."""
        time.sleep(seconds)
        return True
    
    def navigate(self, url: str) -> bool:
        """Navigate to a URL."""
        try:
            self.driver.get(url)
            self._wait_for_stability()
            return True
        except Exception:
            return False
    
    def _resolve_element(self, element_node: "ElementNode") -> Optional["WebElement"]:
        """
        Resolve an ElementNode to a Selenium WebElement.
        
        Handles both standard DOM and Shadow DOM elements.
        """
        # Try shadow path first (if available)
        if element_node.shadow_path and hasattr(self.driver, "find_shadow"):
            try:
                return self.driver.find_shadow(element_node.shadow_path, timeout=self.timeout)
            except Exception:
                pass
        
        # Fall back to CSS selector
        return self._find_element(element_node.selector)
    
    def _find_element(self, selector: str) -> Optional["WebElement"]:
        """Find an element by selector."""
        try:
            # Check if it's a shadow path (contains >>)
            if ">>" in selector and hasattr(self.driver, "find_shadow"):
                return self.driver.find_shadow(selector, timeout=self.timeout)
            
            # Standard CSS selector
            return self.driver.find_element("css selector", selector)
        except Exception:
            return None
    
    def _scroll_into_view(self, element: "WebElement") -> None:
        """Scroll an element into the viewport."""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            time.sleep(0.3)  # Brief pause for scroll animation
        except Exception:
            pass
    
    def _wait_for_stability(self, timeout: float = 5.0) -> None:
        """
        Wait for page to reach a stable state.
        
        Uses waitless if available, otherwise falls back to simple heuristics.
        """
        if self._has_waitless:
            # Waitless handles stability automatically
            return
        
        # Simple stability heuristics
        try:
            # Wait for document ready
            for _ in range(int(timeout * 2)):
                ready_state = self.driver.execute_script("return document.readyState")
                if ready_state == "complete":
                    break
                time.sleep(0.5)
            
            # Brief additional wait for JavaScript
            time.sleep(0.2)
        except Exception:
            pass
