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
    metadata: Optional[dict] = None


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
        stealth_manager: Optional[Any] = None,
        recorder: Optional[Any] = None,
    ):
        """
        Initialize the action executor.
        
        Args:
            driver: Selenium WebDriver (optionally wrapped with waitless)
            timeout: Default timeout for actions in seconds
            max_retries: Maximum retry attempts for failed actions
            stealth_manager: Optional StealthDriverManager for advanced actions
            recorder: Optional FlightRecorder for logging
        """
        self.driver = driver
        self.timeout = timeout
        self.max_retries = max_retries
        self.stealth_manager = stealth_manager
        self.recorder = recorder
        self._has_waitless = self._check_waitless_support()
    
    def _check_waitless_support(self) -> bool:
        """Check if driver has waitless stability features."""
        # Check for waitless wrapper markers
        return hasattr(self.driver, "_waitless_wrapped")
    
    def execute(self, decision: "Decision", force_js: bool = False) -> bool:
        """
        Execute a decision from the intelligence layer.
        
        Args:
            decision: Decision object with action and target
            force_js: Whether to force JavaScript execution (bypass standard events)
        
        Returns:
            True if action succeeded, False otherwise
        """
        action = decision.action.lower()
        target = decision.target
        
        if action == "click":
            return self.click_selector(target, force_js=force_js)
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
    
    def click(self, element_node: "ElementNode", force_js: bool = False) -> ActionResult:
        """
        Click an element with automatic stability wait and self-healing.
        
        Args:
            element_node: ElementNode from DOM mapper
        
        Returns:
            ActionResult with success status
        """
        start_time = time.time()
        
        try:
            # 0. Strategy 0: StealthBot Smart Click (Priority if available)
            if self.stealth_manager and hasattr(self.stealth_manager, "smart_click"):
                if self.recorder:
                    self.recorder.log_info(f"Stealth: Using smart_click for {element_node.selector}")
                try:
                    self.stealth_manager.smart_click(element_node.selector)
                    self._wait_for_stability()
                    return ActionResult(
                        success=True,
                        action="click",
                        target=element_node.selector,
                        duration_ms=(time.time() - start_time) * 1000,
                        metadata={"strategy": "stealth_smart_click"}
                    )
                except Exception as e:
                    if self.recorder:
                        self.recorder.log_warning(f"Stealth smart_click failed: {e}. Falling back...")

            # 1. Resolve and Scroll
            element = self._resolve_element(element_node)
            if element is None:
                return ActionResult(
                    success=False,
                    action="click",
                    target=element_node.selector,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="Element not found",
                )
            
            self._scroll_into_view(element)
            self._wait_for_stability()
            
            # 2. Strategy 1: Standard Selenium Click (Skip if force_js requested)
            if not force_js:
                for attempt in range(self.max_retries):
                    try:
                        # Re-resolve if stale (Self-healing)
                        if attempt > 0:
                            element = self._resolve_element(element_node)
                            if not element: break
                            self._scroll_into_view(element)

                        # Store URL before click to detect navigation
                        url_before = self.driver.current_url
                        
                        element.click()
                        
                        # Wait for stability - but page navigation causes exceptions
                        try:
                            self._wait_for_stability()
                        except (Exception, StaleElementReferenceException) as stability_err:
                            # If page navigated or element became stale, it's often a success
                            url_after = self.driver.current_url
                            if url_before != url_after:
                                # Navigation occurred - absolute success
                                return ActionResult(
                                    success=True,
                                    action="click",
                                    target=element_node.selector,
                                    duration_ms=(time.time() - start_time) * 1000,
                                    metadata={"navigation": True}
                                )
                            # If no navigation but exception, it might be a real failure or 
                            # just a transient issue. We'll let the loop retry.
                            raise stability_err
                        
                        return ActionResult(
                            success=True,
                            action="click",
                            target=element_node.selector,
                            duration_ms=(time.time() - start_time) * 1000,
                        )
                    except Exception as e:
                        # Check if navigation happened even if click threw exception
                        try:
                            if self.driver.current_url != url_before:
                                 return ActionResult(
                                    success=True,
                                    action="click",
                                    target=element_node.selector,
                                    duration_ms=(time.time() - start_time) * 1000,
                                    metadata={"navigation": True, "error_suppressed": str(e)}
                                )
                        except: pass
                        
                        # If this is the last attempt, try Strategy 2 (JS Fallback)
                        if attempt == self.max_retries - 1:
                            break
                        time.sleep(self.RETRY_DELAY_MS / 1000)

            # 3. Strategy 2: JavaScript Fallback (Self-healing)
            try:
                # Re-resolve one last time for JS click
                element = self._resolve_element(element_node)
                if element:
                    url_before = self.driver.current_url
                    self.driver.execute_script("arguments[0].click();", element)
                    
                    # Wait for stability
                    try:
                        self._wait_for_stability()
                    except Exception:
                        # Success if URL changed
                        if self.driver.current_url != url_before:
                             return ActionResult(
                                success=True,
                                action="click",
                                target=element_node.selector,
                                duration_ms=(time.time() - start_time) * 1000,
                                metadata={"strategy": "js_fallback", "navigation": True}
                            )
                    
                    return ActionResult(
                        success=True,
                        action="click",
                        target=element_node.selector,
                        duration_ms=(time.time() - start_time) * 1000,
                        metadata={"strategy": "js_fallback"}
                    )
            except Exception as js_error:
                # One last check for navigation
                if self.driver.current_url != url_before:
                    return ActionResult(
                        success=True,
                        action="click",
                        target=element_node.selector,
                        duration_ms=(time.time() - start_time) * 1000,
                        metadata={"navigation": True}
                    )
                raise Exception(f"JS Click failed: {js_error}")

        except Exception as e:
            return ActionResult(
                success=False,
                action="click",
                target=element_node.selector,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )

    def click_selector(self, selector: str, force_js: bool = False) -> bool:
        """
        Click an element by CSS selector with self-healing.
        """
        try:
            # Mock an ElementNode for the main click logic
            from dataclasses import dataclass
            @dataclass
            class MockNode:
                selector: str
                shadow_path: Optional[str] = None
                
            node = MockNode(selector=selector)
            result = self.click(node, force_js=force_js)
            return result.success
        except Exception:
            return False

    def type_text(self, element_node: "ElementNode", text: str, clear_first: bool = True) -> ActionResult:
        """
        Type text into an element with self-healing.
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
            
            # Retry loop for type
            for attempt in range(self.max_retries):
                try:
                    if attempt > 0:
                        element = self._resolve_element(element_node)
                        if not element: break
                        self._scroll_into_view(element)

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
                    if attempt == self.max_retries - 1:
                        # Final Attempt: try JS value setting as fallback
                        try:
                            self.driver.execute_script("arguments[0].value = arguments[1];", element, text)
                            self._wait_for_stability()
                            return ActionResult(
                                success=True,
                                action="type",
                                target=element_node.selector,
                                duration_ms=(time.time() - start_time) * 1000,
                                metadata={"strategy": "js_fallback"}
                            )
                        except:
                            raise e
                    time.sleep(self.RETRY_DELAY_MS / 1000)

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
        Type text into an element by selector with self-healing.
        """
        try:
            from selenium.webdriver.common.keys import Keys
            
            # Use type_text for self-healing logic
            from dataclasses import dataclass
            @dataclass
            class MockNode:
                selector: str
                shadow_path: Optional[str] = None
            
            node = MockNode(selector=selector)
            result = self.type_text(node, text, clear_first=clear_first)
            
            if result.success and submit:
                # Trigger Enter key separately for simplicity if using self-healing helper
                element = self._find_element(selector)
                if element:
                    element.send_keys(Keys.RETURN)
                    self._wait_for_stability()
            
            return result.success
        except Exception:
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

    def _resolve_element(self, element_node: Any) -> Optional["WebElement"]:
        """
        Resolve an ElementNode to a Selenium WebElement.
        
        Handles both standard DOM and Shadow DOM elements.
        """
        # 1. Try shadow path first (if available)
        if hasattr(element_node, "shadow_path") and element_node.shadow_path and hasattr(self.driver, "find_shadow"):
            try:
                return self.driver.find_shadow(element_node.shadow_path, timeout=self.timeout)
            except Exception:
                pass
        
        # 2. Try selector (CSS)
        return self._find_element(element_node.selector)

    def _find_element(self, selector: str) -> Optional["WebElement"]:
        """
        Find an element by selector using waitless-native retry pattern.
        
        Uses the wrapped driver's find_element which respects waitless
        stability checks instead of bypassing with WebDriverWait.
        """
        import time

        try:
            # Check if it's a shadow path (contains >>)
            if ">>" in selector and hasattr(self.driver, "find_shadow"):
                return self.driver.find_shadow(selector, timeout=self.timeout)
            
            # Waitless-native retry pattern:
            # Use wrapped driver's find_element which respects stability
            end_time = time.time() + (self.timeout / 3)  # Faster timeout for find
            while time.time() < end_time:
                try:
                    # This goes through wrapped driver - waitless handles stability
                    elem = self.driver.find_element("css selector", selector)
                    if elem:
                        return elem
                except Exception:
                    pass
                time.sleep(0.2)  # Short sleep between attempts
            
            return None
        except Exception:
            return None

    def _scroll_into_view(self, element: "WebElement") -> None:
        """Scroll an element into the viewport."""
        try:
            # Check if element is already in view to avoid jarring jumps
            in_view = self.driver.execute_script("""
                var rect = arguments[0].getBoundingClientRect();
                return (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
                );
            """, element)
            
            if not in_view:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    element
                )
                time.sleep(0.3)
        except Exception:
            pass

    def _wait_for_stability(self, timeout: float = 5.0) -> None:
        """
        Wait for page to reach a stable state.
        """
        if self._has_waitless:
            # Waitless handles stability automatically
            return
        
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            
            # Wait for document ready
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Brief additional wait for animations
            time.sleep(0.2)
        except Exception:
            pass
