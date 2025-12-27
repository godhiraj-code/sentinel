"""
Session Replayer - Replay and Debug Past Exploration Runs.

Loads flight records from past Sentinel runs and allows:
- Step-by-step visualization of the agent's journey
- Re-execution of recorded actions on a live browser
- Comparison of current vs recorded results
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReplayStep:
    """A single step in a replay session."""
    step_number: int
    timestamp: datetime
    event_type: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    screenshot_path: Optional[str] = None
    
    @property
    def action(self) -> Optional[str]:
        """Get the action type if this is a decision step."""
        return self.data.get("action")
    
    @property
    def target(self) -> Optional[str]:
        """Get the target selector if this is a decision step."""
        return self.data.get("target")
    
    @property
    def confidence(self) -> float:
        """Get the confidence score if this is a decision step."""
        return self.data.get("confidence", 0.0)
    
    @property
    def reasoning(self) -> Optional[str]:
        """Get the reasoning if this is a decision step."""
        return self.data.get("reasoning")


@dataclass
class ReplaySession:
    """A complete replay session from a flight record."""
    run_id: str
    url: str
    goal: str
    start_time: datetime
    end_time: Optional[datetime]
    steps: List[ReplayStep] = field(default_factory=list)
    success: bool = False
    total_decisions: int = 0
    
    @property
    def duration_seconds(self) -> float:
        """Total session duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class SessionReplayer:
    """
    Replay and debug past Sentinel exploration runs.
    
    Example:
        >>> replayer = SessionReplayer("./sentinel_reports/20251227_074249")
        >>> session = replayer.load()
        >>> for step in replayer.iterate_steps():
        ...     print(f"Step {step.step_number}: {step.event_type}")
        >>> replayer.replay_on_browser(driver)  # Re-execute on live browser
    """
    
    def __init__(self, report_dir: str):
        """
        Initialize the session replayer.
        
        Args:
            report_dir: Path to the report directory containing flight_record.json
        """
        self.report_dir = report_dir
        self.flight_record_path = os.path.join(report_dir, "flight_record.json")
        self.session: Optional[ReplaySession] = None
        self._current_step_index = 0
        
    def load(self) -> ReplaySession:
        """
        Load the flight record and parse into a ReplaySession.
        
        Returns:
            ReplaySession with all recorded steps.
        """
        if not os.path.exists(self.flight_record_path):
            raise FileNotFoundError(f"Flight record not found: {self.flight_record_path}")
        
        with open(self.flight_record_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Parse the flight record
        self.session = self._parse_flight_record(data)
        logger.info(f"[SessionReplayer] Loaded session with {len(self.session.steps)} steps")
        
        return self.session
    
    def _parse_flight_record(self, data: Dict[str, Any]) -> ReplaySession:
        """Parse raw flight record JSON into a ReplaySession."""
        entries = data.get("entries", [])
        metadata = data.get("metadata", {})
        
        steps = []
        url = ""
        goal = metadata.get("goal", "Unknown goal")
        start_time = None
        end_time = None
        total_decisions = 0
        success = False
        
        for entry in entries:
            # Parse timestamp
            ts_str = entry.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except:
                timestamp = datetime.now()
            
            if start_time is None:
                start_time = timestamp
            end_time = timestamp
            
            event_type = entry.get("event_type", "unknown")
            message = entry.get("message", "")
            entry_data = entry.get("data", {})
            screenshot = entry.get("screenshot_path")
            
            # Extract URL from navigation events
            if event_type == "navigation":
                url = entry_data.get("url", url)
            
            # Count decisions
            if event_type == "decision":
                total_decisions += 1
            
            # Check for success
            if event_type == "action_result" and entry_data.get("success"):
                success = True
            
            step = ReplayStep(
                step_number=entry.get("step", len(steps)),
                timestamp=timestamp,
                event_type=event_type,
                message=message,
                data=entry_data,
                screenshot_path=screenshot,
            )
            steps.append(step)
        
        return ReplaySession(
            run_id=os.path.basename(self.report_dir),
            url=url,
            goal=goal,
            start_time=start_time or datetime.now(),
            end_time=end_time,
            steps=steps,
            success=success,
            total_decisions=total_decisions,
        )
    
    def iterate_steps(self):
        """Iterate through all steps in the session."""
        if not self.session:
            self.load()
        yield from self.session.steps
    
    def get_decisions(self) -> List[ReplayStep]:
        """Get only the decision steps from the session."""
        if not self.session:
            self.load()
        return [s for s in self.session.steps if s.event_type == "decision"]
    
    def get_step(self, index: int) -> Optional[ReplayStep]:
        """Get a specific step by index."""
        if not self.session:
            self.load()
        if 0 <= index < len(self.session.steps):
            return self.session.steps[index]
        return None
    
    def next_step(self) -> Optional[ReplayStep]:
        """Get the next step in the sequence."""
        step = self.get_step(self._current_step_index)
        if step:
            self._current_step_index += 1
        return step
    
    def reset(self):
        """Reset the replay to the beginning."""
        self._current_step_index = 0
    
    def print_summary(self):
        """Print a summary of the replay session."""
        if not self.session:
            self.load()
        
        s = self.session
        print("=" * 60)
        print("🎬 SESSION REPLAY SUMMARY")
        print("=" * 60)
        print(f"Run ID:    {s.run_id}")
        print(f"URL:       {s.url}")
        print(f"Goal:      {s.goal}")
        print(f"Duration:  {s.duration_seconds:.2f}s")
        print(f"Steps:     {len(s.steps)}")
        print(f"Decisions: {s.total_decisions}")
        print(f"Success:   {'✅ Yes' if s.success else '❌ No'}")
        print("-" * 60)
        print("Decision Timeline:")
        
        for step in self.get_decisions():
            conf_bar = "█" * int(step.confidence * 10) + "░" * (10 - int(step.confidence * 10))
            print(f"  [{conf_bar}] {step.action.upper()} → {step.target[:40] if step.target else 'N/A'}")
            if step.reasoning:
                print(f"      └─ {step.reasoning[:50]}...")
        
        print("=" * 60)
    
    def replay_on_browser(self, driver, step_mode: bool = False, callback=None):
        """
        Re-execute the recorded actions on a live browser.
        
        Args:
            driver: Selenium WebDriver instance
            step_mode: If True, pause after each step for inspection
            callback: Optional callback function called after each step
        
        Returns:
            List of (step, success) tuples
        """
        from sentinel.layers.action import ActionExecutor
        
        if not self.session:
            self.load()
        
        executor = ActionExecutor(driver)
        results = []
        
        # Navigate to the URL first
        if self.session.url:
            logger.info(f"[SessionReplayer] Navigating to {self.session.url}")
            driver.get(self.session.url)
        
        for step in self.get_decisions():
            logger.info(f"[SessionReplayer] Replaying: {step.action} → {step.target}")
            
            # Create a mock decision for the executor
            from sentinel.layers.intelligence import Decision
            decision = Decision(
                action=step.action,
                target=step.target or "",
                reasoning=f"Replay: {step.reasoning}",
                confidence=step.confidence,
                metadata=step.data.get("metadata", {}),
            )
            
            # Execute the action
            success = executor.execute(decision)
            results.append((step, success))
            
            if callback:
                callback(step, success)
            
            if step_mode:
                input(f"Press Enter to continue to next step...")
        
        return results


def replay_command(report_dir: str, step_mode: bool = False, rerun: bool = False):
    """
    CLI entry point for session replay.
    
    Args:
        report_dir: Path to the report directory
        step_mode: Pause after each step
        rerun: Actually re-execute actions on a browser
    """
    replayer = SessionReplayer(report_dir)
    
    try:
        replayer.load()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return
    
    # Print summary
    replayer.print_summary()
    
    if rerun:
        print("\n🔄 Re-running session on browser...")
        from sentinel.core.driver_factory import create_driver
        
        driver = create_driver(headless=False)
        try:
            results = replayer.replay_on_browser(driver, step_mode=step_mode)
            
            print("\n📊 Replay Results:")
            for step, success in results:
                status = "✅" if success else "❌"
                print(f"  {status} {step.action} → {step.target[:40] if step.target else 'N/A'}")
        finally:
            driver.quit()
