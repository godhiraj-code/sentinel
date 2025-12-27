# The Sentinel User Guide

> Complete guide to using The Sentinel for autonomous web testing

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [CLI Reference](#cli-reference)
5. [Python API](#python-api)
6. [Configuration Options](#configuration-options)
7. [Understanding the Sense-Decide-Act Loop](#understanding-the-sense-decide-act-loop)
8. [Working with Reports](#working-with-reports)
9. [Session Replay](#session-replay)
10. [Local SLM Support](#local-slm-support)
11. [Vision Language Models](#vision-language-models)
12. [Stealth Mode](#stealth-mode)
13. [Shadow DOM Support](#shadow-dom-support)
14. [Troubleshooting](#troubleshooting)
15. [FAQ](#faq)

---

## Introduction

The Sentinel is an **autonomous web testing agent** that navigates websites and achieves goals without requiring explicit test scripts. Instead of writing:

```python
# Traditional approach
driver.find_element(By.ID, "username").send_keys("test")
driver.find_element(By.ID, "password").send_keys("pass123")
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
```

You simply tell The Sentinel what you want:

```python
# The Sentinel approach
agent = SentinelOrchestrator(
    url="https://example.com/login",
    goal="Login with username 'test' and password 'pass123'"
)
result = agent.run()
```

The agent figures out how to achieve the goal autonomously.

---

## Installation

### Requirements

- Python 3.9 or higher
- Chrome browser installed
- ChromeDriver (auto-downloaded if not present)

### Basic Installation

```bash
pip install the-sentinel
```

### Full Installation (All Features)

```bash
pip install the-sentinel[full]
```

### Development Installation

```bash
git clone https://github.com/yourusername/the-sentinel.git
cd the-sentinel
pip install -e ".[dev]"
```

### Verify Installation

```bash
sentinel doctor
```

This will check all dependencies and show their status:

```
╭─────────────────────╮
│ 🩺 Sentinel Doctor  │
│ System Health Check │
╰─────────────────────╯

┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Package           ┃ Role                         ┃    Status    ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ selenium          │ Core - WebDriver             │ ✅ Installed │
│ lumos             │ Sense - Shadow DOM           │ ✅ Installed │
│ visual-guard      │ Sense - Visual Regression    │ ✅ Installed │
│ waitless          │ Action - UI Stability        │ ✅ Installed │
└───────────────────┴──────────────────────────────┴──────────────┘
```

---

## Quick Start

### Using the CLI

The fastest way to try The Sentinel is via the command line:

```bash
# Navigate to a page and achieve a goal
sentinel explore "https://demo.playwright.dev/todomvc/" "Add 'Buy milk' to the list"
```

The agent will:
1. Open Chrome
2. Navigate to the URL
3. Analyze the page
4. Make decisions to achieve your goal
5. Generate a report

**Controlling the exploration with `--max-steps`:**

```bash
# Quick test - limit to 5 steps
sentinel explore "https://example.com" "Click the button" --max-steps 5

# Complex multi-step flow - allow more steps
sentinel explore "https://example.com" "Login and go to settings" --max-steps 30

# Default is 50 steps, which is good for most cases
sentinel explore "https://example.com" "Complete the checkout"
```

> **💡 Tip**: Start with a low `--max-steps` value (5-10) for simple goals like clicking a button or adding an item. Increase it for complex multi-step workflows.

### Using Python

```python
from sentinel import SentinelOrchestrator

# Create the agent
agent = SentinelOrchestrator(
    url="https://demo.playwright.dev/todomvc/",
    goal="Add 'Buy milk' to the todo list",
    max_steps=10  # Limit exploration steps
)

# Run and get results
result = agent.run()

print(f"Success: {result.success}")
print(f"Steps taken: {result.steps}")
print(f"Duration: {result.duration_seconds:.2f}s")
print(f"Report: {result.report_path}")

# View what decisions were made
for decision in result.decisions:
    print(f"  - {decision.action}: {decision.target} ({decision.confidence:.0%})")
```

---

## CLI Reference

### `sentinel explore`

Run autonomous exploration with a goal.

```bash
sentinel explore <url> <goal> [OPTIONS]
```

**Arguments:**
- `url`: Target website URL
- `goal`: Natural language description of what to achieve

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--stealth/--no-stealth` | `--stealth` | Enable/disable bot evasion |
| `--headless/--headed` | `--headed` | Run browser headlessly |
| `--training` | Off | Use mock LLM (free mode) |
| `--max-steps` | 50 | Maximum exploration steps |
| `--brain` | auto | Intelligence: auto, heuristic, cloud, local |
| `--model` | None | Model name/path for cloud or local brain |
| `--report-dir` | `./sentinel_reports` | Report output directory |

**Examples:**
```bash
# Basic exploration
sentinel explore "https://example.com" "Find the contact page"

# Stealth mode for protected sites
sentinel explore "https://protected.com" "Login" --stealth

# Headless mode for CI/CD
sentinel explore "https://example.com" "Submit form" --headless --max-steps 20
```

### `sentinel stress`

Run UI mutation stress testing.

```bash
sentinel stress <url> [OPTIONS]
```

**Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--mutations` | 5 | Number of mutations to apply |
| `--report-dir` | `./sentinel_reports` | Report output directory |

### `sentinel doctor`

Check system health and dependencies.

```bash
sentinel doctor
```

### `sentinel version`

Show version information.

```bash
sentinel version
```

### `sentinel replay`

Replay a past exploration session.

```bash
sentinel replay <report_dir> [OPTIONS]
```

**Arguments:**
- `report_dir`: Path to the report directory containing flight_record.json

**Options:**
| Option | Description |
|--------|-------------|
| `--rerun` | Re-execute actions on a live browser |
| `--step` | Pause after each step for inspection |

**Examples:**
```bash
# View session summary and decision timeline
sentinel replay ./sentinel_reports/20251227_074249

# Re-run actions on live browser
sentinel replay ./sentinel_reports/20251227_074249 --rerun

# Step-by-step mode with pauses
sentinel replay ./sentinel_reports/20251227_074249 --rerun --step
```

---

## Python API

### SentinelOrchestrator

The main class for autonomous exploration.

```python
from sentinel import SentinelOrchestrator

agent = SentinelOrchestrator(
    url="https://example.com",
    goal="Click the submit button",
    stealth_mode=True,
    headless=False,
    training_mode=False,
    max_steps=50,
    timeout=30,
    report_dir="./sentinel_reports"
)
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | *required* | Target URL to explore |
| `goal` | str | *required* | Natural language goal |
| `stealth_mode` | bool | `True` | Enable bot evasion |
| `headless` | bool | `False` | Run headlessly |
| `training_mode` | bool | `False` | Use mock LLM |
| `max_steps` | int | `50` | Maximum steps |
| `timeout` | int | `30` | Action timeout (seconds) |
| `report_dir` | str | `./sentinel_reports` | Report directory |

**Methods:**
| Method | Returns | Description |
|--------|---------|-------------|
| `run()` | `ExecutionResult` | Execute the exploration |
| `close()` | None | Clean up resources |

### ExecutionResult

The result of an exploration run.

```python
result = agent.run()

print(result.success)           # bool: Did goal succeed?
print(result.goal)              # str: The goal attempted
print(result.url)               # str: Target URL
print(result.steps)             # int: Steps taken
print(result.max_steps)         # int: Max allowed steps
print(result.duration_seconds)  # float: Total time
print(result.decisions)         # List[Decision]: All decisions made
print(result.report_path)       # str: Path to HTML report
print(result.error)             # str | None: Error message if failed
```

### Decision

Represents a single decision made by the agent.

```python
for decision in result.decisions:
    print(decision.action)      # str: "click", "type", "scroll", etc.
    print(decision.target)      # str: CSS selector or element identifier
    print(decision.reasoning)   # str: Why this decision was made
    print(decision.confidence)  # float: 0.0 to 1.0
```

---

## Configuration Options

### Stealth Mode

Stealth mode uses SeleniumBase UC Mode via `sb-stealth-wrapper` to bypass bot detection:

```python
# Enable stealth (recommended for protected sites)
agent = SentinelOrchestrator(
    url="https://protected-site.com",
    goal="Login",
    stealth_mode=True
)
```

### Training Mode

Training mode uses heuristic-based decision making instead of an LLM:

```python
# Free mode - no API costs
agent = SentinelOrchestrator(
    url="https://example.com",
    goal="Click button",
    training_mode=True
)
```

### Headless Mode

Run without a visible browser window:

```python
agent = SentinelOrchestrator(
    url="https://example.com",
    goal="Submit form",
    headless=True
)
```

> **Note:** Headless mode may reduce stealth effectiveness on some sites.

---

## Understanding the Sense-Decide-Act Loop

The Sentinel operates in a continuous loop:

### 1. SENSE Phase

The agent builds a "World State" by:
- **DOM Mapping**: Discovers all interactive elements
- **Shadow DOM Traversal**: Penetrates Shadow DOM boundaries
- **Visual Analysis**: Detects blocking states (modals, spinners, captchas)

```python
# Access the world state directly
from sentinel.layers.sense import DOMMapper

mapper = DOMMapper(driver)
elements = mapper.get_world_state()

for elem in elements:
    print(f"{elem.tag}: {elem.text[:30]}")
```

### 2. DECIDE Phase

The agent chooses the next action based on:
- Current goal
- Available elements
- Previous actions (history)
- Confidence scoring

```python
# Access the decision engine
from sentinel.layers.intelligence import DecisionEngine

brain = DecisionEngine(mock_mode=True)
decision = brain.decide(
    goal="Click the login button",
    world_state=elements,
    history=[]
)

print(f"Action: {decision.action}")
print(f"Target: {decision.target}")
print(f"Confidence: {decision.confidence:.0%}")
```

### 3. ACT Phase

The agent executes the decision with:
- Automatic scrolling to elements
- Retry logic for transient failures
- UI stability waits

```python
# Access the action executor
from sentinel.layers.action import ActionExecutor

executor = ActionExecutor(driver)
success = executor.execute(decision)
```

---

## Working with Reports

### Report Location

Reports are saved to `./sentinel_reports/YYYYMMDD_HHMMSS/`:

```
sentinel_reports/
└── 20231225_143052/
    ├── report.html          # Main HTML report
    ├── flight_record.json   # JSON log of all events
    └── screenshots/         # Screenshots at each step
        ├── step_0.png
        ├── step_1.png
        └── ...
```

### Report Contents

The HTML report includes:
- **Summary**: Success/failure, duration, step count
- **Decision Timeline**: Each action with timestamp
- **World State Snapshots**: Elements discovered
- **Screenshots**: Visual record of each step
- **Error Details**: If exploration failed

### Accessing Report Data Programmatically

```python
import json

# Load the flight record
with open("sentinel_reports/20231225_143052/flight_record.json") as f:
    record = json.load(f)

print(f"Total entries: {len(record['entries'])}")
print(f"Start time: {record['metadata']['start_time']}")
```

---

## Session Replay

Session Replay allows you to view and re-execute past exploration sessions.

### Viewing Past Sessions

```bash
sentinel replay ./sentinel_reports/20251227_074249
```

This displays:
- Run ID, URL, and goal
- Duration and step count
- Decision timeline with confidence bars

### Re-executing on Browser

```bash
# Re-run all actions on a live browser
sentinel replay ./sentinel_reports/20251227_074249 --rerun

# Step-by-step mode (pause after each action)
sentinel replay ./sentinel_reports/20251227_074249 --rerun --step
```

### Python API

```python
from sentinel.reporters.session_replayer import SessionReplayer

# Load a session
replayer = SessionReplayer("./sentinel_reports/20251227_074249")
session = replayer.load()

# Print summary
replayer.print_summary()

# Iterate through decisions
for decision in replayer.get_decisions():
    print(f"{decision.action} -> {decision.target}")

# Re-execute on browser
results = replayer.replay_on_browser(driver)
```

---

## Local SLM Support

The Sentinel supports local Small Language Models (SLMs) for privacy-first, offline decision making.

### Supported Models

- **Phi-3 Mini**: Fast, efficient, ~4GB RAM
- **Mistral 7B**: High quality, ~8GB RAM
- Any GGUF model compatible with llama-cpp-python

### Configuration

```python
agent = SentinelOrchestrator(
    url="https://example.com",
    goal="Click login",
    brain_type="local",
    model_name="C:/models/phi-3-mini.gguf"
)
```

### CLI Usage

```bash
sentinel explore "https://example.com" "Login" --brain local --model phi-3
```

---

## Vision Language Models

The Sentinel includes a `VisualAgent` for screenshot-based UI analysis.

### Backends

- **Moondream2**: Local VLM via HuggingFace transformers
- **OpenAI GPT-4o**: Cloud vision API
- **Mock**: Fast testing without model downloads

### Usage

```python
from sentinel.layers.sense.visual_agent import VisualAgent

agent = VisualAgent(backend="moondream")

# Describe the UI
description = agent.describe_state("screenshot.png")

# Find an element by description
element = agent.find_element("screenshot.png", "the login button")
print(f"Found at ({element.x}, {element.y})")

# Verify an action succeeded
confidence = agent.verify_action("before.png", "after.png", "clicked the button")
```

---

## Stealth Mode

Stealth mode uses `sb-stealth-wrapper` (built on SeleniumBase UC Mode) to evade bot detection.

### When to Use Stealth Mode

- Sites with Cloudflare protection
- Sites with reCAPTCHA/hCaptcha
- Sites that detect automation
- Rate-limited endpoints

### How It Works

1. Uses undetected Chrome driver
2. Randomizes browser fingerprints
3. Simulates human-like interactions
4. Handles challenge pages automatically

### Limitations

- First run downloads UC driver (~100MB)
- Slightly slower than non-stealth mode
- May require headed mode for some challenges

---

## Shadow DOM Support

The Sentinel uses `lumos-shadowdom` to discover elements inside Shadow DOM boundaries.

### Automatic Discovery

Shadow DOM elements are automatically included in the world state:

```python
elements = mapper.get_world_state()

for elem in elements:
    if elem.in_shadow_dom:
        print(f"Shadow element: {elem.tag}")
        print(f"Shadow host: {elem.shadow_host}")
```

### Manual Shadow DOM Access

```python
from lumos import Lumos

lumos = Lumos(driver)
shadow_elements = lumos.find_all_shadow("input")
```

---

## Troubleshooting

### "ChromeDriver not found"

```bash
# The Sentinel auto-downloads ChromeDriver, but if it fails:
pip install webdriver-manager
```

### "Session not created" Error

```bash
# Update Chrome browser to latest version
# Or specify Chrome binary path:
export CHROME_BINARY=/path/to/chrome
```

### Agent Gets Stuck

Try reducing complexity:
```python
agent = SentinelOrchestrator(
    url="https://example.com",
    goal="Click the button",  # Simpler goal
    max_steps=10,             # Fewer steps
    training_mode=True        # Faster decisions
)
```

### Stealth Mode Fails

1. Try headed mode instead of headless
2. Check if site blocks VPNs
3. Add delays between actions

---

## FAQ

### Q: Is The Sentinel an AI agent?

**A:** Yes! It's a hybrid AI agent that can use:
- **Heuristic Brain**: Fast, keyword-matching (default)
- **Local SLM**: Phi-3, Mistral via llama-cpp-python (privacy-first)
- **Cloud LLM**: OpenAI, Claude for maximum intelligence
- **Vision LLM**: Moondream2 for screenshot-based element detection

### Q: Does it work with any website?

**A:** It works with most websites. Some heavily protected sites may require additional configuration or may not be automatable.

### Q: Can I use it for production testing?

**A:** Yes! It's designed for testing. Use headless mode in CI/CD pipelines.

### Q: How does it handle dynamic content?

**A:** The `waitless` integration automatically waits for UI stability before each action.

### Q: Can I extend it with custom actions?

**A:** Yes, the modular architecture allows custom layers. See the Technical Guide.

---

## Next Steps

- Read the [Technical Guide](docs/TECHNICAL_GUIDE.md) for architecture details
- Check [Examples](examples/) for more usage patterns
- Join our community for support

---

**Happy Testing! 🛡️**
