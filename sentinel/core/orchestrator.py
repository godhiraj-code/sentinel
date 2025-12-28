"""
Sentinel Orchestrator - The Master Controller.

Implements the Sense-Decide-Act loop that enables
autonomous web exploration and validation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import re

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
    stealth_mode: bool = False
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
        stealth_mode: bool = False,
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
        
        # Initialize FlightRecorder first so others can use it
        self._recorder = FlightRecorder(output_dir=self.config.report_dir)
        
        # Initialize layers
        self._dom_mapper = DOMMapper(self._driver)
        self._visual_analyzer = VisualAnalyzer(self._driver)
        self._executor = ActionExecutor(
            self._driver, 
            timeout=self.config.timeout,
            stealth_manager=self._stealth_manager,
            recorder=self._recorder
        )
        self._brain = DecisionEngine(
            mock_mode=self.config.training_mode,
            brain_type=self.config.brain_type,
            model_path=self.config.model_name
        )
        
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
        self._recorder.log_info(f"📍 Goal strategy established: {len(self._parsed_goal.steps)} logical steps identified.")
        for i, step in enumerate(self._parsed_goal.steps):
            self._recorder.log_info(f"   Step {i+1}: {step.description or step}")
        
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
                
                # 0. STABILIZE - Ensure world is ready before looking
                try:
                    self._wait_for_stability()
                except Exception:
                    # Proceed even if stability timeout (best effort)
                    pass
                
                # 1. SENSE - Build world state
                world_state = self._dom_mapper.get_world_state()
                is_blocked, reason = self._visual_analyzer.is_blocked()
                
                self._recorder.log_world_state(step, world_state, is_blocked, reason)
                
                # Screenshot showing world state (before action)
                if self.config.screenshot_on_step:
                    self._recorder.capture_screenshot(f"step_{step}_world_state", driver=self._driver)
                
                if is_blocked:
                    # 1.5 AUTO-STEALTH: If blocked by Captcha in standard mode, pivot to StealthBot
                    if "captcha" in reason.lower() and not self.config.stealth_mode:
                        if self._pivot_to_stealth():
                            is_blocked, reason = self._visual_analyzer.is_blocked() # Re-check
                    
                    if is_blocked:
                        # Try to handle blocking element (Captchas, Modals, etc.)
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

                # Maintain a blacklist for the current step to enable adaptive recovery
                if not hasattr(self, "_step_blacklist"):
                    self._step_blacklist = []

                decision = self._brain.decide(
                    goal=current_step,
                    world_state=world_state,
                    history=decisions,
                    full_goal=self._parsed_goal,
                    blacklist=self._step_blacklist
                )
                decisions.append(decision)
                self._recorder.log_decision(step, decision)
                
                # 3. ACT - Execute and Verify
                success = self._execute_and_verify(step, decision, current_step, before_state=(world_state, self._driver.current_url))
                
                # Adaptive Recovery: If action failed to change state, blacklist the specific target
                if not success and decision.target and decision.target != "body":
                    self._recorder.log_warning(f"Action failed verification. Blacklisting target: {decision.target}")
                    self._step_blacklist.append(decision.target)
                    # We don't increment step cycle but we do record the attempt
                    continue 

                # Take screenshot after action
                if self.config.screenshot_on_step:
                    self._recorder.capture_screenshot(f"step_{step}_after_action", driver=self._driver)
                
                # Check if current goal step is achieved
                if self._goal_achieved(decisions):
                    self._recorder.log_info(f"🎯 Step success: {current_step.description or str(current_step)}")
                    self._parsed_goal.next_step()
                    self._step_blacklist = [] # Clear blacklist for new step
                    
                    if self._parsed_goal.is_completed:
                        report_path = self._recorder.generate_report()
                        self._recorder.log_info("✨ Goal Achieved! Generating final report.")
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
    
    def _wait_for_stability(self) -> None:
        """
        Force the UI to reach absolute stability using waitless and explicit checkpoints.
        """
        try:
            # 1. Waitless intervention (if wrapped)
            if hasattr(self._driver, "wait_for_stability"):
                self._driver.wait_for_stability()
            else:
                # Trigger via find_element (Waitless intercepter)
                self._driver.find_element("tag name", "body")
            
            # 2. Additional "Hydration Grace"
            # Some sites (React/Next) stabilize their DOM but haven't finished 
            # binding event listeners. We add a short grace period.
            import time
            time.sleep(0.8)
            
            # 3. Final visual check if analyzer is available
            is_blocked, _ = self._visual_analyzer.is_blocked()
            if is_blocked:
                 self._recorder.log_info("Stability delayed by visual block (modal/spinner)")
                 self._wait_for_loading(5)
                 
        except Exception as e:
            self._recorder.log_warning(f"Stability check failed: {e}")
            import time
            time.sleep(1.0)

    def _execute_and_verify(self, step_idx: int, decision: Decision, goal_step: GoalStep, before_state: Optional[tuple] = None) -> bool:
        """
        Execute an action and verify it had the intended effect.
        """
        # 1. Capture BEFORE state (if not provided)
        if before_state:
             _, before_url = before_state
        else:
             before_url = self._driver.current_url
             
        before_dom_snapshot = self._dom_mapper.get_page_snapshot()
        
        # 2. Execute Action
        # Try standard execution first
        success = self._executor.execute(decision)
        self._recorder.log_action_result(step_idx, success)
        
        if not success:
            return False
            
        # 3. Verify Effect (Wait for stability)
        try:
            self._wait_for_stability()
        except Exception:
            pass
            
        # 4. Check for state change
        after_state = self._dom_mapper.get_page_snapshot()
        after_url = self._driver.current_url
        
        # If state didn't change and it was a click, RETRY with JS
        # 4. Immediate logical verification (did something happen?)
        if decision.action in ["click", "type"]:
            # Change is expected: URL change OR DOM change
            if after_url != before_url:
                self._recorder.log_info(f"Action verified: URL changed to {after_url}")
                return True
            
            if after_state != before_dom_snapshot:
                # We also check if the change was just a minor flicker or a real update
                # (handled by wait_for_stability, but we return True here to signal effect)
                self._recorder.log_info("Action verified: Measured DOM state change.")
                return True
            
            # If no change detected, check if we've already achieved the goal step
            # through some external side effect (unlikely but possible).
            if self._goal_achieved([decision]): 
                self._recorder.log_info("Action verified: Goal condition met despite no state change.")
                return True

            # If we reached here, both standard and JS actions failed to change state.
            # This triggers the Adaptive Recovery (Blacklisting) in the main loop.
            self._recorder.log_info(f"Action failed: No measurable state change after {decision.action}.")
            return False
            
        return True

    def _wait_for_target_element(self, timeout: int = 10) -> bool:
        """
        Wait for target element to appear if class is specified in goal.
        
        Uses waitless-native retry pattern - polls using the wrapped driver's
        find_element which respects waitless stability checks.
        
        When user says "class blog-nudge-button", wait for that element
        to appear in the DOM before proceeding with world state scan.
        """
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
        """
        Attempt to resolve a captcha challenge using StealthBot.
        """
        if hasattr(self, "_stealth_manager") and self._stealth_manager:
            self._recorder.log_warning("Captcha detected! Invoking StealthBot challenge resolution...")
            try:
                # Call the underlying StealthBot challenge handler
                self._stealth_manager.handle_challenges()
                self._recorder.log_info("StealthBot challenge resolution complete.")
                return True
            except Exception as e:
                self._recorder.log_error(f"StealthBot challenge resolution failed: {e}")
                return False
        else:
            self._recorder.log_warning("Captcha detected but Stealth mode is not active. Manual intervention required.")
            return False
    
    def _goal_achieved(self, decisions: List[Decision]) -> bool:
        """
        Check if the CURRENT goal step has been achieved.
        """
        if not self._parsed_goal:
            return False

        current_step = self._parsed_goal.current_step
        if not current_step:
            return True

        # 1. VERIFY patterns
        if current_step.action == "verify":
            # Check secondary visibility signal
            if current_step.value and self._text_visible_on_page(current_step.value):
                if decisions and decisions[-1].confidence >= 0.6:
                    return True
            
            # Check primary trust signal from intelligence layer
            if decisions:
                last_decision = decisions[-1]
                if last_decision.action == "verify" and last_decision.confidence >= 0.9:
                    return True
        
        # 2. NAVIGATE patterns
        elif current_step.action == "navigate":
            if current_step.value and current_step.value in self._driver.current_url:
                return True
                
        # 3. INTERACTION STEPS (click, type)
        # These are handled by _execute_and_verify's return value in the main loop.
        # But for redundancy, we return True if the last action matched the intent.
        elif decisions:
            last_decision = decisions[-1]
            if last_decision.action == current_step.action and last_decision.confidence >= 0.5:
                 return True

        return False

    def _extract_verify_text(self) -> Optional[str]:
        """
        Extract text to verify from goal.
        Supports patterns:
        - verify 'text'
        - verify "text"
        - verify [unquoted text] appears/exists/is visible
        - verify heading [unquoted text]
        """
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
        """
        Check if text is visible, with semantic filtering to avoid generic sidebars/footers.
        """
        try:
            # Avoid matching text in generic site areas that might lead to "False Pass"
            script = """
            return (function(targetText) {
                targetText = targetText.toLowerCase();
                
                // 1. Try to find the most specific semantic container
                const containers = document.querySelectorAll('article, main, #content, .post, .post-content, .entry-content');
                for (let container of containers) {
                    if (container.innerText.toLowerCase().includes(targetText)) return true;
                }
                
                // 2. Direct body check, but exclude noisy sections
                const body = document.body.cloneNode(true);
                const noisyTags = ['nav', 'footer', 'aside', 'script', 'style'];
                const noise = body.querySelectorAll(noisyTags.join(', ') + ', .sidebar, .related-posts, .menu');
                noise.forEach(n => n.remove());
                
                return body.innerText.toLowerCase().includes(targetText);
            })(arguments[0]);
            """
            return self._driver.execute_script(script, text)
        except Exception as e:
            # Fallback to standard check if script fails
            self._recorder.log_warning(f"Semantic verification failed: {e}. Falling back to standard check.")
            page_text = self._driver.find_element("tag name", "body").text.lower()
            return text.lower() in page_text
    
    def _pivot_to_stealth(self) -> bool:
        """
        Dynamically relaunch the current session in Stealth mode.
        """
        if self._stealth_manager:
            return True # Already in stealth
            
        current_url = self._driver.current_url
        self._recorder.log_warning(f"Auto-Stealth: Block detected at {current_url}. Pivoting to StealthBot...")
        
        # 1. Close standard driver
        self.close()
        
        # 2. Force stealth_mode and re-initialize
        self.config.stealth_mode = True
        self._initialize()
        
        # 3. Restore URL
        self._driver.get(current_url)
        return True

    def close(self) -> None:
        """Release resources."""
        # Clean up stealth manager (this also quits the driver)
        if self._stealth_manager:
            try:
                self._stealth_manager.__exit__(None, None, None)
            except Exception:
                pass
            self._stealth_manager = None
            self._driver = None # Manager already quit it
        
        # Clean up standard driver
        if self._driver:
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

    def __del__(self):
        """Final backup cleanup on garbage collection."""
        try:
            self.close()
        except Exception:
            pass
