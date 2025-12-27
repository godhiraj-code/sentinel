"""
Flight Recorder - Decision Logging and Report Generation.

Captures the agent's decision-making process and generates
beautiful reports using pytest-glow-report concepts.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
import json
import os

if TYPE_CHECKING:
    from sentinel.layers.intelligence.decision_engine import Decision


@dataclass
class LogEntry:
    """A single log entry in the flight record."""
    timestamp: datetime
    step: int
    event_type: str  # 'navigation', 'world_state', 'decision', 'action', 'warning', 'error', 'info'
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    screenshot_path: Optional[str] = None


class FlightRecorder:
    """
    Records the agent's decision-making process.
    
    Acts as a "Black Box" for the agent, capturing:
    - World state snapshots
    - Decisions and reasoning
    - Action results
    - Screenshots at key moments
    
    Generates HTML reports using pytest-glow-report style.
    
    Example:
        >>> recorder = FlightRecorder()
        >>> recorder.log_navigation("https://example.com")
        >>> recorder.log_decision(0, decision)
        >>> report_path = recorder.generate_report()
    """
    
    def __init__(
        self,
        output_dir: str = "./sentinel_reports",
        run_name: Optional[str] = None,
    ):
        """
        Initialize the flight recorder.
        
        Args:
            output_dir: Directory for reports and screenshots
            run_name: Optional name for this run
        """
        self.output_dir = output_dir
        self.run_name = run_name or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.entries: List[LogEntry] = []
        self.metadata: Dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "run_name": self.run_name,
        }
        
        # Create output directories
        self.run_dir = os.path.join(output_dir, self.run_name)
        self.screenshots_dir = os.path.join(self.run_dir, "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        self._glow = self._init_glow_report()
    
    def _init_glow_report(self):
        """Try to initialize pytest-glow-report if available."""
        try:
            from beautiful_report import GlowReport
            return GlowReport(output_dir=self.run_dir)
        except ImportError:
            return None
    
    def log_navigation(self, url: str) -> None:
        """Log a navigation event."""
        self.entries.append(LogEntry(
            timestamp=datetime.now(),
            step=0,
            event_type="navigation",
            message=f"Navigated to {url}",
            data={"url": url},
        ))
        self.metadata["url"] = url
    
    def log_world_state(
        self,
        step: int,
        world_state: List[Any],
        is_blocked: bool,
        reason: str,
    ) -> None:
        """Log a world state snapshot."""
        # Summarize world state
        element_summary = [
            {"tag": elem.tag, "text": elem.text[:30] if elem.text else "", "id": elem.id}
            for elem in world_state[:10]  # Limit to first 10
        ]
        
        self.entries.append(LogEntry(
            timestamp=datetime.now(),
            step=step,
            event_type="world_state",
            message=f"World state: {len(world_state)} elements, blocked={is_blocked}",
            data={
                "element_count": len(world_state),
                "is_blocked": is_blocked,
                "block_reason": reason,
                "elements": element_summary,
            },
        ))
    
    def log_decision(self, step: int, decision: "Decision") -> None:
        """Log a decision."""
        self.entries.append(LogEntry(
            timestamp=datetime.now(),
            step=step,
            event_type="decision",
            message=f"Decision: {decision.action} on {decision.target[:30]}",
            data=decision.to_dict(),
        ))
        
        if self._glow:
            try:
                self._glow.step(f"Step {step}: {decision.action} - {decision.reasoning}")
            except Exception:
                pass
    
    def log_action_result(self, step: int, success: bool, error: Optional[str] = None) -> None:
        """Log an action result."""
        self.entries.append(LogEntry(
            timestamp=datetime.now(),
            step=step,
            event_type="action",
            message=f"Action result: {'success' if success else 'failed'}",
            data={"success": success, "error": error},
        ))
    
    def log_info(self, message: str) -> None:
        """Log a general information message."""
        self.entries.append(LogEntry(
            timestamp=datetime.now(),
            step=len(self.entries),
            event_type="info",
            message=message,
        ))
    
    def log_warning(self, message: str) -> None:
        """Log a warning."""
        self.entries.append(LogEntry(
            timestamp=datetime.now(),
            step=len(self.entries),
            event_type="warning",
            message=message,
        ))
    
    def log_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """Log an error."""
        self.entries.append(LogEntry(
            timestamp=datetime.now(),
            step=len(self.entries),
            event_type="error",
            message=message,
            data={"exception": str(exception) if exception else None},
        ))
    
    def capture_screenshot(self, name: str, driver=None) -> Optional[str]:
        """
        Capture a screenshot.
        
        Args:
            name: Name for the screenshot
            driver: WebDriver instance (if not using glow)
        
        Returns:
            Path to saved screenshot
        """
        if self._glow:
            try:
                return self._glow.screenshot(name)
            except Exception:
                pass
        
        if driver:
            try:
                path = os.path.join(self.screenshots_dir, f"{name}.png")
                driver.save_screenshot(path)
                
                # Add to last entry
                if self.entries:
                    self.entries[-1].screenshot_path = path
                
                return path
            except Exception:
                pass
        
        return None
    
    def generate_report(self) -> str:
        """
        Generate an HTML report.
        
        Returns:
            Path to the generated report
        """
        self.metadata["end_time"] = datetime.now().isoformat()
        self.metadata["total_steps"] = len([e for e in self.entries if e.event_type == "decision"])
        
        # If glow is available, use it
        if self._glow:
            try:
                return self._glow.generate()
            except Exception:
                pass
        
        # Generate fallback HTML report
        return self._generate_fallback_report()
    
    def _generate_fallback_report(self) -> str:
        """Generate a simple HTML report without glow."""
        report_path = os.path.join(self.run_dir, "report.html")
        
        # Build HTML
        html = self._build_html_report()
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        # Also save JSON log
        json_path = os.path.join(self.run_dir, "flight_record.json")
        with open(json_path, "w") as f:
            json.dump({
                "metadata": self.metadata,
                "entries": [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "step": e.step,
                        "event_type": e.event_type,
                        "message": e.message,
                        "data": e.data,
                        "screenshot_path": e.screenshot_path,
                    }
                    for e in self.entries
                ],
            }, f, indent=2)
        
        return report_path
    
    def _build_html_report(self) -> str:
        """Build HTML report content."""
        # Count results
        decisions = [e for e in self.entries if e.event_type == "decision"]
        actions = [e for e in self.entries if e.event_type == "action"]
        success_count = len([a for a in actions if a.data.get("success")])
        failed_count = len(actions) - success_count
        
        # Build timeline
        timeline_html = ""
        for entry in self.entries:
            icon = self._get_event_icon(entry.event_type)
            status_class = self._get_status_class(entry)
            
            # Calculate relative path for screenshot
            screenshot_html = ""
            if entry.screenshot_path:
                try:
                    rel_path = os.path.relpath(entry.screenshot_path, self.run_dir)
                    screenshot_html = f'<img src="{rel_path}" class="timeline-screenshot">'
                except ValueError:
                    # Fallback if paths are on different drives
                    screenshot_html = f'<img src="{entry.screenshot_path}" class="timeline-screenshot">'

            timeline_html += f"""
            <div class="timeline-item {status_class}">
                <div class="timeline-icon">{icon}</div>
                <div class="timeline-content">
                    <div class="timeline-time">{entry.timestamp.strftime('%H:%M:%S')}</div>
                    <div class="timeline-message">{entry.message}</div>
                    {self._format_data(entry.data) if entry.data else ''}
                    {screenshot_html}
                </div>
            </div>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentinel Flight Record - {self.run_name}</title>
    <style>
        :root {{
            --bg-dark: #0d1117;
            --bg-card: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
            --success: #3fb950;
            --warning: #d29922;
            --error: #f85149;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }}
        
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        .header {{
            text-align: center;
            padding: 2rem;
            margin-bottom: 2rem;
            background: var(--bg-card);
            border-radius: 12px;
            border: 1px solid var(--border);
        }}
        
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--accent), #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent);
        }}
        
        .stat-label {{
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        
        .timeline {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
        }}
        
        .timeline-item {{
            display: flex;
            gap: 1rem;
            padding: 1rem 0;
            border-bottom: 1px solid var(--border);
        }}
        
        .timeline-item:last-child {{ border-bottom: none; }}
        
        .timeline-icon {{
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--border);
            border-radius: 50%;
            font-size: 1.25rem;
        }}
        
        .timeline-content {{ flex: 1; }}
        
        .timeline-time {{
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
        
        .timeline-message {{ font-weight: 500; }}
        
        .timeline-data {{
            margin-top: 0.5rem;
            padding: 0.5rem;
            background: var(--bg-dark);
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.8rem;
            overflow-x: auto;
        }}
        
        .timeline-screenshot {{
            max-width: 300px;
            margin-top: 0.5rem;
            border-radius: 4px;
        }}
        
        .success {{ border-left: 3px solid var(--success); }}
        .warning {{ border-left: 3px solid var(--warning); }}
        .error {{ border-left: 3px solid var(--error); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Sentinel Flight Record</h1>
            <p>Run: {self.run_name}</p>
            <p>{self.metadata.get('url', 'N/A')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{len(decisions)}</div>
                <div class="stat-label">Decisions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--success)">{success_count}</div>
                <div class="stat-label">Successful Actions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--error)">{failed_count}</div>
                <div class="stat-label">Failed Actions</div>
            </div>
        </div>
        
        <div class="timeline">
            <h2 style="margin-bottom: 1rem;">Timeline</h2>
            {timeline_html}
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _get_event_icon(self, event_type: str) -> str:
        """Get emoji icon for event type."""
        icons = {
            "navigation": "🧭",
            "world_state": "👁️",
            "decision": "🧠",
            "action": "⚡",
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️",
        }
        return icons.get(event_type, "📝")
    
    def _get_status_class(self, entry: LogEntry) -> str:
        """Get CSS class based on entry status."""
        if entry.event_type == "error":
            return "error"
        if entry.event_type == "warning":
            return "warning"
        if entry.event_type == "action":
            return "success" if entry.data.get("success") else "error"
        return ""
    
    def _format_data(self, data: Dict[str, Any]) -> str:
        """Format data as HTML."""
        if not data:
            return ""
        
        # Filter out large data
        filtered = {k: v for k, v in data.items() if not isinstance(v, (list, dict)) or len(str(v)) < 200}
        
        if not filtered:
            return ""
        
        return f'<div class="timeline-data">{json.dumps(filtered, indent=2)}</div>'
