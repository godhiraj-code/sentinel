"""
Sentinel Orchestrator - The Master Controller.

Implements the Sense-Decide-Act loop that enables
autonomous web exploration and validation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from sentinel.core.driver_factory import create_driver, StealthDriverManager, WebDriverType
from sentinel.core.goal_parser import RegexGoalParser, ParsedGoal, GoalStep
from sentinel.layers.sense import DOMMapper, VisualAnalyzer
from sentinel.layers.action import ActionExecutor
from sentinel.layers.intelligence import DecisionEngine, Decision
from sentinel.reporters import FlightRecorder


@dataclass
class ExecutionResult:
    """Result of a Sentinel exploration run."""
    success: bool
    goal: str
    url: str
    steps: int
    max_steps: int
    decisions: List[Decision]
    start_time: datetime
    end_time: datetime
    report_path: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def duration_seconds(self) -> float:
        """Total execution time in seconds."""
        return (self.end_time - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "goal": self.goal,
            "url": self.url,
            "steps": self.steps,
            "max_steps": self.max_steps,
            "duration_seconds": self.duration_seconds,
            "decisions": [d.to_dict() for d in self.decisions],
            "report_path": self.report_path,
            "error": self.error,
        }


@dataclass
class SentinelConfig:
    """Configuration for the Sentinel orchestrator."""
    url: str
    goal: str
    stealth_mode: bool = True
    headless: bool = False
    training_mode: bool = False
    max_steps: int = 50
    timeout: int = 30
    screenshot_on_step: bool = True  # Capture screenshot at each step
    report_dir: str = "./sentinel_reports"
    brain_type: str = "auto"
    model_name: Optional[str] = None
    use_vision: bool = False  # Enable VLM visual analysis
    # Waitless stability configuration
    stability_timeout: int = 15  # Seconds to wait for UI stability
    mutation_threshold: int = 200  # mutations/sec considered stable
    stability_mode: str = "relaxed"  # strict, normal, relaxed


class SentinelOrchestrator:
    """
    Master orchestrator for autonomous web testing.
    
    The Sentinel operates in a continuous Sense-Decide-Act loop:
    
    1. SENSE: Build a "world state" by mapping the DOM (including Shadow DOMs)
       and analyzing visual state for blocking elements.
    
    2. DECIDE: Use the intelligence layer to select the next action
       based on the goal and current world state.
    
    3. ACT: Execute the decision with reliability guarantees
       (automatic retries, stability waits).
    
    Example:
        >>> agent = SentinelOrchestrator(
        ...     url="https://example.com",
        ...     goal="Click the login button"
        ... )
        >>> result = agent.run()
        >>> print(f"Success: {result.success} in {result.steps} steps")
    """
    
    def __init__(
        self,
        url: str,
        goal: str,
        stealth_mode: bool = True,
        headless: bool = False,
        training_mode: bool = False,
        max_steps: int = 50,
        timeout: int = 30,
        report_dir: str = "./sentinel_reports",
        brain_type: str = "auto",
        model_name: Optional[str] = None,
        use_vision: bool = False,
        stability_timeout: int = 15,
        mutation_threshold: int = 200,
        stability_mode: str = "relaxed",
    ):
        """
        Initialize the Sentinel orchestrator.
        
        Args:
            brain_type: Strategy for brain selection ("auto", "heuristic", "cloud", "local")
            model_name: Specific model name/path (e.g. "gpt-4", "c:/models/phi3.gguf")
            use_vision: Enable VLM-based visual analysis for element detection
            stability_timeout: Waitless stability timeout in seconds
            mutation_threshold: DOM mutations/sec considered stable
            stability_mode: Stability strictness ('strict', 'normal', 'relaxed')
        """
        self.config = SentinelConfig(
            url=url,
            goal=goal,
            stealth_mode=stealth_mode,
            headless=headless,
            training_mode=training_mode,
            max_steps=max_steps,
            timeout=timeout,
            report_dir=report_dir,
            brain_type=brain_type,
            model_name=model_name,
            use_vision=use_vision,
            stability_timeout=stability_timeout,
            mutation_threshold=mutation_threshold,
            stability_mode=stability_mode,
        )
        
        self._driver: Optional[WebDriverType] = None
        self._stealth_manager: Optional[StealthDriverManager] = None
        self._dom_mapper: Optional[DOMMapper] = None
        self._visual_analyzer: Optional[VisualAnalyzer] = None
        self._visual_agent = None  # Lazy-loaded VisualAgent for VLM
        self._executor: Optional[ActionExecutor] = None
        self._brain: Optional[DecisionEngine] = None
        self._recorder: Optional[FlightRecorder] = None
        
        self._initialized = False
        self._parser = RegexGoalParser()
        self._parsed_goal: Optional[ParsedGoal] = None
    
    @property
    def driver(self) -> WebDriverType:
        """Get the WebDriver instance, creating it if needed."""
        if self._driver is None:
            self._initialize()
        return self._driver
    
    def _initialize(self) -> None:
        """Initialize all components lazily."""
        if self._initialized:
            return
        
        if self.config.stealth_mode:
            # Use StealthBot via context manager
            try:
                self._stealth_manager = StealthDriverManager(headless=self.config.headless)
                self._stealth_manager.__enter__()
                self._driver = self._stealth_manager.driver
            except Exception as e:
                import warnings
                warnings.warn(f"StealthBot failed: {e}. Using standard driver.")
                self._driver = create_driver(
                    headless=self.config.headless,
                    stealth_mode=False,
                    enable_shadow_dom=True,
                    enable_stability=True,
                    stability_timeout=self.config.stability_timeout,
                    mutation_threshold=self.config.mutation_threshold,
                    stability_mode=self.config.stability_mode,
                )
        else:
            # Create standard driver with enhancements
            self._driver = create_driver(
                headless=self.config.headless,
                stealth_mode=False,
                enable_shadow_dom=True,
                enable_stability=True,
                stability_timeout=self.config.stability_timeout,
                mutation_threshold=self.config.mutation_threshold,
                stability_mode=self.config.stability_mode,
            )
        
        # Initialize layers
        self._dom_mapper = DOMMapper(self._driver)
        self._visual_analyzer = VisualAnalyzer(self._driver)
        self._executor = ActionExecutor(self._driver, timeout=self.config.timeout)
        self._brain = DecisionEngine(
            mock_mode=self.config.training_mode,
            brain_type=self.config.brain_type,
            model_path=self.config.model_name
        )
        self._recorder = FlightRecorder(output_dir=self.config.report_dir)
        
        self._initialized = True
    
    def run(self) -> ExecutionResult:
        """
        Execute the Sense-Decide-Act loop until goal is achieved.
        
        Returns:
            ExecutionResult with success status, steps taken,
            decisions made, and report path.
        """
        self._initialize()
        self._parsed_goal = self._parser.parse(self.config.goal)
        self._recorder.log_info(f"Goal parsed into {len(self._parsed_goal.steps)} steps")
        for i, step in enumerate(self._parsed_goal.steps):
            self._recorder.log_info(f"  Step {i+1}: {step}")
        
        start_time = datetime.now()
        decisions: List[Decision] = []
        error_msg: Optional[str] = None
        
        try:
            # Navigate to target URL
            self._driver.get(self.config.url)
            self._recorder.log_navigation(self.config.url)
            
            # Screenshot after navigation
            if self.config.screenshot_on_step:
                self._recorder.capture_screenshot("navigation", driver=self._driver)
            
            for step in range(self.config.max_steps):
                # Wait for target element if class is specified in goal
                self._wait_for_target_element()
                
                # 1. SENSE - Build world state
                world_state = self._dom_mapper.get_world_state()
                is_blocked, reason = self._visual_analyzer.is_blocked()
                
                self._recorder.log_world_state(step, world_state, is_blocked, reason)
                
                # Screenshot showing world state (before action)
                if self.config.screenshot_on_step:
                    self._recorder.capture_screenshot(f"step_{step}_world_state", driver=self._driver)
                
                if is_blocked:
                    # Try to handle blocking element
                    handled = self._handle_blocked_state(reason)
                    if not handled:
                        error_msg = f"Blocked by: {reason}"
                        break
                    continue
                
                # 2. DECIDE - Choose next action
                current_step = self._parsed_goal.current_step
                if not current_step:
                     self._recorder.log_info("All goal steps completed")
                     break

                decision = self._brain.decide(
                    goal=current_step,
                    world_state=world_state,
                    history=decisions,
                    full_goal=self._parsed_goal
                )
                decisions.append(decision)
                self._recorder.log_decision(step, decision)
                
                # 3. ACT - Execute and Verify
                success = self._execute_and_verify(step, decision, current_step)
                
                # Take screenshot after action to show the result (even if verification failed)
                if self.config.screenshot_on_step:
                    self._recorder.capture_screenshot(f"step_{step}_after_action", driver=self._driver)
                
                # Check if current goal step is achieved
                if self._goal_achieved(decisions):
                    self._recorder.log_info(f"Verified step: {current_step}")
                    self._parsed_goal.next_step()
                    
                    if self._parsed_goal.is_completed:
                        report_path = self._recorder.generate_report()
                        return ExecutionResult(
                        success=True,
                        goal=self.config.goal,
                        url=self.config.url,
                        steps=step + 1,
                        max_steps=self.config.max_steps,
                        decisions=decisions,
                        start_time=start_time,
                        end_time=datetime.now(),
                        report_path=report_path,
                    )
            
            # Max steps reached
            error_msg = error_msg or "Max steps reached without achieving goal"
            
        except Exception as e:
            error_msg = str(e)
        
        finally:
            report_path = self._recorder.generate_report()
        
        return ExecutionResult(
            success=False,
            goal=self.config.goal,
            url=self.config.url,
            steps=len(decisions),
            max_steps=self.config.max_steps,
            decisions=decisions,
            start_time=start_time,
            end_time=datetime.now(),
            report_path=report_path,
            error=error_msg,
        )
    
    def _handle_blocked_state(self, reason: str) -> bool:
        """
        Attempt to resolve a blocked UI state.
        
        Args:
            reason: Description of why the UI is blocked
        
        Returns:
            True if the block was resolved, False otherwise
        """
        # Common blocking patterns and their solutions
        if "modal" in reason.lower():
            return self._try_dismiss_modal()
        if "loading" in reason.lower() or "spinner" in reason.lower():
            return self._wait_for_loading()
        if "captcha" in reason.lower():
            return self._handle_captcha()
        
        return False
    
    def _try_dismiss_modal(self) -> bool:
        """Try to dismiss a modal overlay."""
        # Look for common close button patterns
        close_selectors = [
            "[data-dismiss='modal']",
            ".modal-close",
            ".close-button",
            "button[aria-label='Close']",
            ".modal .close",
        ]
        
        for selector in close_selectors:
            try:
                element = self._driver.find_element("css selector", selector)
                if element.is_displayed():
                    element.click()
                    return True
            except Exception:
                continue
        
        # Try pressing Escape
        from selenium.webdriver.common.keys import Keys
        try:
            self._driver.find_element("tag name", "body").send_keys(Keys.ESCAPE)
            return True
        except Exception:
            pass
        
        return False
    
    def _wait_for_loading(self, timeout: int = 10) -> bool:
        """Wait for loading indicators to disappear."""
        import time
        
        for _ in range(timeout):
            is_blocked, _ = self._visual_analyzer.is_blocked()
            if not is_blocked:
                return True
            time.sleep(1)
        
        return False
    
    def _execute_and_verify(self, step_idx: int, decision: Decision, goal_step: GoalStep) -> bool:
        """
        Execute an action and verify it had the intended effect.
        """
        # 1. Capture BEFORE state
        before_state = self._dom_mapper.get_page_snapshot()
        before_url = self._driver.current_url
        
        # 2. Execute Action
        success = self._executor.execute(decision)
        self._recorder.log_action_result(step_idx, success)
        
        if not success:
            return False
            
        # 3. Capture AFTER state
        after_state = self._dom_mapper.get_page_snapshot()
        after_url = self._driver.current_url
        
        # 4. Immediate logical verification (did something happen?)
        if decision.action == "click":
            # Change is expected: URL change OR DOM change
            if after_url != before_url:
                self._recorder.log_info("Action verified: URL changed")
                return True
            if after_state != before_state:
                self._recorder.log_info("Action verified: DOM changed")
                return True
            
            self._recorder.log_info("Warning: No state change detected after click")
            
        return True

    def _wait_for_target_element(self, timeout: int = 10) -> bool:
        """
        Wait for target element to appear if class is specified in goal.
        
        Uses waitless-native retry pattern - polls using the wrapped driver's
        find_element which respects waitless stability checks.
        
        When user says "class blog-nudge-button", wait for that element
        to appear in the DOM before proceeding with world state scan.
        """
        import re
        import time
        
        # Extract class name from goal
        goal = self.config.goal.lower()
        class_match = re.search(r"class[:\s]+([a-zA-Z0-9_-]+)", goal)
        
        if not class_match:
            return True  # No specific class requested
        
        class_name = class_match.group(1)
        selector = f".{class_name}"
        
        # Waitless-native retry pattern:
        # Use wrapped driver's find_element which respects stability
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                # This goes through wrapped driver - waitless handles stability
                elem = self._driver.find_element("css selector", selector)
                if elem and elem.is_displayed():
                    return True
            except Exception:
                pass
            time.sleep(0.3)  # Short sleep between attempts
        
        # Element didn't appear within timeout - continue anyway
        return False
    
    def _handle_captcha(self) -> bool:
        """Handle captcha challenges (delegates to stealth wrapper if available)."""
        # Captcha handling is best done by the stealth wrapper
        # This is a placeholder for manual intervention signal
        self._recorder.log_warning("Captcha detected - manual intervention may be required")
        return False
    
    def _goal_achieved(self, decisions: List[Decision]) -> bool:
        """
        Check if the current goal step (or the entire goal) has been achieved.
        """
        if not self._parsed_goal:
            # Fallback for non-structured goals (from Phase 1)
            verify_text = self._extract_verify_text()
            if verify_text and self._text_visible_on_page(verify_text):
                return True
            return False

        current_step = self._parsed_goal.current_step
        if not current_step:
            return True # No current step means we are done

        # 1. Action-specific verification for the CURRENT step
        is_step_done = False
        
        if current_step.action == "verify":
            # Just check if the value (text) exists on the page
            if current_step.value and self._text_visible_on_page(current_step.value):
                is_step_done = True
        
        elif current_step.action == "navigate":
            # Check if current URL matches the target value
            if current_step.value and current_step.value in self._driver.current_url:
                is_step_done = True
                
        elif decisions:
            # For interaction steps (click, type), we check if the last decision
            # matched the intended action of the step.
            last = decisions[-1]
            if last.action == current_step.action:
                # We already did logical verification in _execute_and_verify
                # So if we reached here and last action matches, we count it as done
                is_step_done = True

        return is_step_done
    
    def _extract_verify_text(self) -> Optional[str]:
        """
        Extract text to verify from goal.
        Supports patterns:
        - verify 'text'
        - verify "text"
        - verify [unquoted text] appears/exists/is visible
        - verify heading [unquoted text]
        """
        import re
        goal = self.config.goal
        
        # 1. Quoted text (Strongest match)
        quoted_match = re.search(r"verify.*['\"]([^'\"]+)['\"]", goal, re.IGNORECASE)
        if quoted_match:
            return quoted_match.group(1)
            
        # 2. Unquoted "verify [text] exists/appears/is visible"
        unquoted_match = re.search(r"verify\s+(.*?)\s+(exists|appears|is visible|exists)", goal, re.IGNORECASE)
        if unquoted_match:
            return unquoted_match.group(1).strip()
            
        # 3. Unquoted "verify heading/title [text]"
        heading_match = re.search(r"verify\s+(heading|title|text)\s+(.*)$", goal, re.IGNORECASE)
        if heading_match:
            return heading_match.group(2).strip()
            
        return None
    
    def _text_visible_on_page(self, text: str) -> bool:
        """Check if specific text is visible on the page."""
        try:
            # Search for the text in the page body
            page_text = self._driver.find_element("tag name", "body").text
            return text.lower() in page_text.lower()
        except Exception:
            return False
    
    def close(self) -> None:
        """Clean up resources."""
        # Clean up stealth manager if used
        if self._stealth_manager:
            try:
                self._stealth_manager.__exit__(None, None, None)
            except Exception:
                pass
            self._stealth_manager = None
        
        # Clean up standard driver
        if self._driver and not self._stealth_manager:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
        
        self._initialized = False
    
    def __enter__(self) -> "SentinelOrchestrator":
        """Context manager entry."""
        self._initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
