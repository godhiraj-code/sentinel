# The Sentinel 🛡️

> **The Selenium of the AI Era**  
> **Autonomous Web Testing Agent for "Untestable" Environments**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/the-sentinel.svg)](https://badge.fury.io/py/the-sentinel)

The Sentinel is a unified autonomous web testing framework that combines the power of 10+ specialized automation libraries into a single, intelligent agent. It uses a **Sense → Decide → Act** loop to navigate web applications and achieve goals without explicit scripting.

---

## 🎯 What Makes The Sentinel Different?

| Traditional Automation | The Sentinel |
|------------------------|--------------|
| Write explicit selectors | Agent finds elements autonomously |
| Hardcode wait times | Automatic UI stability detection |
| Fail on DOM changes | **Self-healing** element recovery |
| Detect bot protection | Built-in stealth mode |
| Manual debugging | Flight recorder with **multi-state screenshots** |
| Goal Verification | **Rigorous assertion-based verification** |
| Cloud-only AI | **Local SLM support** (offline, privacy-first) |

---

## ⚡ Quick Start

### Installation

```bash
pip install the-sentinel
```

Or install with all features:
```bash
pip install the-sentinel[full]
```

### CLI Usage

```bash
# Check your setup
sentinel doctor

# Explore a website with a goal (quotes around text to add are important!)
sentinel explore "https://demo.playwright.dev/todomvc/" "Add 'Buy milk' to the list"

# Limit exploration steps (useful for quick tests)
sentinel explore "https://example.com" "Click the login button" --max-steps 10

# Use stealth mode for protected sites (enabled by default)
sentinel explore "https://example.com/login" "Login with test credentials" --stealth

# Disable stealth mode for faster execution on trusted sites
sentinel explore "https://demo.playwright.dev/todomvc/" "Add 'Hello' to the list" --no-stealth

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
    goal="Add 'Buy milk' to the todo list",
    stealth_mode=True,
    max_steps=20
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

| Library | Purpose | Layer |
|---------|---------|-------|
| [lumos-shadowdom](https://pypi.org/project/lumos-shadowdom/) | Shadow DOM traversal | Sense |
| [visual-guard](https://pypi.org/project/visual-guard/) | Visual regression detection | Sense |
| [waitless](https://pypi.org/project/waitless/) | UI stability (no explicit waits) | Action |
| [selenium-teleport](https://pypi.org/project/selenium-teleport/) | Session state management | Action |
| [sb-stealth-wrapper](https://pypi.org/project/sb-stealth-wrapper/) | Bot detection bypass | Action |
| [project-vandal](https://pypi.org/project/project-vandal/) | UI mutation testing | Validation |
| [pytest-glow-report](https://pypi.org/project/pytest-glow-report/) | Beautiful HTML reports | Reporting |
| [pytest-mockllm](https://pypi.org/project/pytest-mockllm/) | LLM mocking for training | Intelligence |
| [llama-cpp-python](https://pypi.org/project/llama-cpp-python/) | **Local SLM inference** | Intelligence |

---

## 🔧 Configuration

### SentinelOrchestrator Options

```python
SentinelOrchestrator(
    url="https://example.com",       # Target URL
    goal="Click the login button",   # Natural language goal
    stealth_mode=True,               # Enable bot evasion (default: True)
    headless=False,                  # Run headlessly (default: False)
    training_mode=False,             # Use mock LLM (free, default: False)
    max_steps=50,                    # Max exploration steps (default: 50)
    timeout=30,                      # Action timeout in seconds (default: 30)
    report_dir="./reports"           # Report output directory
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
  --brain TEXT              Intelligence: auto, heuristic, cloud, local
  --model TEXT              Model name/path for cloud or local brain
  --report-dir PATH         Report output directory

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
- ✅ Shadow DOM support
- ✅ Stealth mode
- ✅ HTML report generation
- ✅ Rigorous Goal Verification
- ✅ **Local SLM integration** (Phi-3, Mistral)
- ✅ **Self-healing actions** (JS fallback)
- ✅ **Waitless-Native stability** (Zero-delay automation)
- ✅ **Multi-state Visual Logging**

### Next Phase (v0.4.0)
- 🔄 VLM integration (Moondream, LLaVA)
- 🔄 Human-in-the-Loop mode
- 🔄 Visual regression comparison
- 🔄 Session replay from reports

### Future
- 🔮 Multi-page flow recording
- 🔮 Self-healing test generation
- 🔮 CI/CD integration
- 🔮 Distributed exploration

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
