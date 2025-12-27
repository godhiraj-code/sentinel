# The Sentinel 🛡️

> **The Selenium of the AI Era**  
> **Autonomous Web Testing Agent for "Untestable" Environments**
> 
> Created by [Dhiraj Das](https://www.dhirajdas.dev)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/the-sentinel.svg)](https://badge.fury.io/py/the-sentinel)

The Sentinel is a unified autonomous web testing framework that combines the power of 10+ specialized automation libraries into a single, intelligent agent. It uses a **Sense → Decide → Act** loop to navigate web applications and achieve goals without explicit scripting.

**Now featuring (v0.3.0):**
- **Waitless Engine**: Automatic handling of complex animations.
- **Adaptive Stealth**: Automatic pivot to UC mode when bot detection is triggered.
- **Smart Click**: Human-like mouse trajectories for behavioral bypass.
- **Unified JS Mapper**: Vectorized element extraction (100x sensing speed).
- **Goal Parser**: Structured, multi-step goal execution.
- **TripleNet Resilience**: Deep Shadow DOM traversal (Lumos + Native + VisualGuard).
- **Privacy-First Intelligence**: Local SLM support.

---

## 🎯 What Makes The Sentinel Different?

| Traditional Automation | The Sentinel |
|------------------------|--------------|
| Write explicit selectors | Agent finds elements autonomously |
| Hardcode wait times | Automatic UI stability detection |
| Fail on DOM changes | **Self-healing** element recovery |
| Detect bot protection | **Adaptive Stealth Pivot** & Real challenge resolution |
| Manual debugging | Flight recorder with **multi-state screenshots** |
| Goal Verification | **Multi-step goal parsing** & rigorous assertion |
| Cloud-only AI | **Local SLM support** (offline, privacy-first) |

---

## ⚡ Quick Start

### Installation

While we prepare for the official PyPI release, you can install The Sentinel directly from source:

**Option 1: Local Development (Recommended)**
```bash
git clone https://github.com/godhiraj-code/sentinel.git
cd sentinel
pip install -e "."
```

**Option 2: Direct from GitHub**
```bash
pip install git+https://github.com/godhiraj-code/sentinel.git
```

**Option 3: Full Installation (with ML features)**
```bash
pip install ".[full]"
```

### CLI Usage

```bash
# Check your setup
sentinel doctor

# Explore a website with a goal (quotes around text to add are important!)
sentinel explore "https://demo.playwright.dev/todomvc/" "Add 'Buy milk' to the list"

# Limit exploration steps (useful for quick tests)
sentinel explore "https://example.com" "Click the login button" --max-steps 10

# Start in high-performance mode (will pivot to stealth if blocked)
sentinel explore "https://demo.playwright.dev/todomvc/" "Add 'Hello' to the list"

# Force stealth mode from the start
sentinel explore "https://amazon.com" "Search for gaming mice" --stealth

# Run in headless mode (for CI/CD)
sentinel explore "https://example.com" "Submit the form" --headless --max-steps 20

# Run UI mutation stress testing
sentinel stress "https://example.com" --mutations 10

# Replay a past session
sentinel replay ./sentinel_reports/20251227_074249

# Re-run past session on live browser
sentinel replay ./sentinel_reports/20251227_074249 --rerun
```

> **💡 Tip**: Use `--max-steps` to control how many actions the agent takes before giving up. Lower values (5-10) are good for simple goals, higher values (20-50) for complex multi-step flows.

### Python API

```python
from sentinel import SentinelOrchestrator

# Create an autonomous agent
agent = SentinelOrchestrator(
    url="https://demo.playwright.dev/todomvc/",
    goal="Type 'Buy milk', then click 'Add', and finally verify 'Buy milk' exists",
    stealth_mode=False,     # Starts fast, pivots to stealth only if needed
    max_steps=20,           # Limit to 20 steps
    brain_type="auto",      # auto, heuristic, cloud, local
    stability_mode="relaxed" # relaxed, normal, strict
)

# Run the agent
result = agent.run()

if result.success:
    print(f"✅ Goal achieved in {result.steps} steps!")
else:
    print(f"❌ Failed: {result.error}")

# View the decision report
print(f"Report: {result.report_path}")
```

### Session Replay

```python
from sentinel.reporters.session_replayer import SessionReplayer

# Load a past session
replayer = SessionReplayer("./sentinel_reports/20251227_074249")
session = replayer.load()

# Print summary
replayer.print_summary()

# Iterate through decisions
for decision in replayer.get_decisions():
    print(f"{decision.action} → {decision.target}")

# Re-execute on browser
results = replayer.replay_on_browser(driver)
```

---

## 🏗️ Architecture

The Sentinel is built as a **Master Orchestrator** that unifies specialized automation libraries:

```
┌─────────────────────────────────────────────────────────────────┐
│                    🎯 SENTINEL ORCHESTRATOR                     │
│                   (Sense → Decide → Act Loop)                   │
├─────────────────────────────────────────────────────────────────┤
│  👁️ SENSE LAYER              │  🦾 ACTION LAYER                │
│  ├─ DOMMapper (lumos)        │  ├─ ActionExecutor (waitless)   │
│  ├─ VisualAnalyzer           │  │   └─ Self-Healing (JS fallback)│
│  │   (visual-guard)          │  ├─ Teleporter (selenium-teleport)│
│  └─ VisualAgent (VLM-ready)  │  └─ Stealth (sb-stealth-wrapper)│
├─────────────────────────────────────────────────────────────────┤
│  🧪 VALIDATION LAYER         │  🧠 INTELLIGENCE LAYER          │
│  └─ UIMutator (vandal)       │  ├─ HeuristicBrain              │
│                              │  ├─ CloudBrain (OpenAI/Claude)  │
│                              │  └─ LocalBrain (Phi-3, Mistral) │
├─────────────────────────────────────────────────────────────────┤
│  📊 REPORTING: FlightRecorder (pytest-glow-report)             │
└─────────────────────────────────────────────────────────────────┘
```

### Integrated Libraries

| Library | Version | Purpose | Layer |
|---------|---------|---------|-------|
| [waitless](https://pypi.org/project/waitless/) | `>=0.3.2` | UI stability (no explicit waits) | Action |
| [sb-stealth-wrapper](https://pypi.org/project/sb-stealth-wrapper/) | `>=0.3.0` | Bot detection bypass | Action |
| [lumos-shadowdom](https://pypi.org/project/lumos-shadowdom/) | `>=0.2.0` | Shadow DOM traversal | Sense |
| [visual-guard](https://pypi.org/project/visual-guard/) | `>=0.1.0` | Visual regression detection | Sense |
| [selenium-teleport](https://pypi.org/project/selenium-teleport/) | `>=0.1.0` | Session state management | Action |
| [project-vandal](https://pypi.org/project/project-vandal/) | `>=0.2.0` | UI mutation testing | Validation |
| [pytest-glow-report](https://pypi.org/project/pytest-glow-report/) | `>=0.1.0` | Beautiful HTML reports | Reporting |
| [pytest-mockllm](https://pypi.org/project/pytest-mockllm/) | `>=0.2.0` | LLM mocking for training | Intelligence |
| [llama-cpp-python](https://pypi.org/project/llama-cpp-python/) | `>=0.2.0` | **Local SLM inference** | Intelligence |

---

## 🔧 Configuration

### SentinelOrchestrator Options

```python
SentinelOrchestrator(
    url="https://example.com",       # Target URL
    goal="Click the login button",   # Natural language goal
    stealth_mode=False,              # Adaptive: False=Fast+Pivot, True=Forced Stealth
    headless=False,                  # Run headlessly (default: False)
    max_steps=50,                    # Max exploration steps (default: 50)
    report_dir="./sentinel_reports", # Report output directory
    brain_type="auto",               # Intelligence: auto, heuristic, cloud, local
    model_name=None,                 # Specific model name or path
    stability_mode="relaxed",        # Waitless: strict, normal, relaxed
    stability_timeout=15,             # Stability timeout in seconds
    use_vision=False                 # Enable VLM-based visual analysis
)
```

### CLI Options

```bash
sentinel explore <url> <goal> [OPTIONS]

Options:
  --stealth/--no-stealth    Enable bot evasion (default: enabled)
  --headless/--headed       Run in headless mode (default: headed)
  --training                Use mock LLM (free mode)
  --max-steps INTEGER       Maximum exploration steps (default: 50)
  --brain TEXT              Intelligence Strategy: auto, heuristic, cloud, local
  --model TEXT              Specific model name (e.g. gpt-4, claude-3) or path
  --report-dir PATH         Report output directory (default: ./sentinel_reports)
  --stability-mode TEXT     Stability strictness: strict, normal, relaxed (default: relaxed)
  --stability-timeout SEC   Waitless stability timeout (default: 15s)

sentinel replay <report_dir> [OPTIONS]

Options:
  --rerun                   Re-execute actions on live browser
  --step                    Pause after each step for inspection
```

---

## 📊 Reports & Debugging

The Sentinel generates detailed HTML reports (powered by `pytest-glow-report`) with:

- **Decision Timeline**: Every action the agent took.
- **World State Snapshots**: Elements discovered at each step.
- **Multi-State Screenshots**: Visual record of Navigation, World State, and After-Action result.
- **Confidence Scores**: How sure the agent was about each decision.
- **Heuristic Log**: Details on why a goal was marked as achieved.

Reports are saved to `./sentinel_reports/YYYYMMDD_HHMMSS/report.html`

### Session Replay

Replay past exploration sessions to debug and re-validate:

```bash
# View session summary and decision timeline
sentinel replay ./sentinel_reports/20251227_074249

# Re-execute on live browser
sentinel replay ./sentinel_reports/20251227_074249 --rerun
```

---

## 🧪 Use Cases

### 1. Autonomous Exploratory Testing
```python
agent = SentinelOrchestrator(
    url="https://your-app.com",
    goal="Find all interactive elements and click them"
)
```

### 2. Bot-Protected Site Testing
```python
agent = SentinelOrchestrator(
    url="https://protected-site.com/login",
    goal="Login with username 'test' and password 'test123'",
    stealth_mode=True
)
```

### 3. Shadow DOM Exploration
```python
from sentinel.layers.sense import DOMMapper

mapper = DOMMapper(driver)
elements = mapper.get_world_state()

for elem in elements:
    if elem.in_shadow_dom:
        print(f"Shadow element: {elem.tag}[{elem.id}]")
```

### 4. UI Mutation Testing
```python
from sentinel.layers.validation import UIMutator

mutator = UIMutator(driver)
mutation = mutator.apply_mutation("#submit-btn", "stealth_disable")

# Run your test...
test_passed = run_your_test()

# Check if test detects the mutation
if not test_passed:
    print("✅ Test correctly detected the mutation!")

mutator.revert_mutation(mutation)
```

---

## 📈 Roadmap

### Current (v0.3.0) ✅
- ✅ Core Sense-Decide-Act loop
- ✅ **Deep Shadow DOM & YouTube** (TripleNet Strategy)
- ✅ **Adaptive Stealth Pivot** (Auto-relaunch in UC mode)
- ✅ **Unified JS Mapper** (O(1) sensing, 100x speedup)
- ✅ **Session Replay** (Recorded mission rerun)
- ✅ **Local SLM integration** (Phi-3, Mistral)
- ✅ **VLM Foundation** (Moondream2, GPT-4o backends)
- ✅ **Self-healing actions** (JS fallback)
- ✅ **Waitless-Native stability**
- ✅ HTML report generation

### Next Phase (v0.4.0)
- 🔄 **Human-in-the-Loop mode** (Manual intervention for tricky tasks)
- 🔄 **Visual regression comparison** (Detect UI changes over time)
- 🔄 **Autonomous VLM Perceptor** (Decision making based *only* on pixels)
- 🔄 **Session state snapshotting** (Save/Load cookies and storage)

### Future
- 🔮 Multi-page flow recording
- 🔮 Self-healing test generation
- 🔮 CI/CD integration plugins
- 🔮 Distributed exploration grid

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

```bash
# Clone the repo
git clone https://github.com/godhiraj-code/sentinel.git
cd the-sentinel

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

The Sentinel is built upon and unifies these excellent projects:
- SeleniumBase for UC Mode stealth
- lumos-shadowdom for Shadow DOM traversal
- And all other integrated libraries

---

**Created by [Dhiraj Das](https://www.dhirajdas.dev)** | [GitHub](https://github.com/godhiraj-code/sentinel) | [Website](https://www.dhirajdas.dev)
