# The Sentinel Technical Guide

> Deep dive into architecture, components, and extensibility
> 
> By [Dhiraj Das](https://www.dhirajdas.dev)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Layer Deep Dives](#layer-deep-dives)
4. [Data Flow](#data-flow)
5. [Extending The Sentinel](#extending-the-sentinel)
6. [Integration Points](#integration-points)
7. [Performance Considerations](#performance-considerations)
8. [Testing Architecture](#testing-architecture)

---

## Architecture Overview

The Sentinel follows a **Layered Agent Architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLI / Python API                               │
│                         (Entry Points Layer)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                       SentinelOrchestrator                               │
│                    (Coordination & State Layer)                          │
├───────────────┬───────────────┬───────────────┬─────────────────────────┤
│  SENSE LAYER  │  DECIDE LAYER │  ACT LAYER    │  VALIDATE LAYER         │
│  - DOMMapper  │  - Decision   │  - Executor   │  - UIMutator            │
│  - Visual     │    Engine     │    (Self-Heal)│                         │
│    Analyzer   │  - Heuristic  │  - Teleporter │                         │
│  - Visual     │  - Local SLM  │  - Stealth    │                         │
│    Agent(VLM) │  - Cloud LLM  │               │                         │
├───────────────┴───────────────┴───────────────┴─────────────────────────┤
│                 FlightRecorder + SessionReplayer                         │
│                       (Cross-cutting Layer)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                        Driver Factory                                    │
│                    (Infrastructure Layer)                                │
└─────────────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Single Responsibility**: Each component does one thing well
2. **Graceful Degradation**: Missing libraries trigger fallbacks, not failures
3. **Observable Execution**: Every decision is logged for debugging
4. **Extensibility**: Layers can be replaced or enhanced

---

## Core Components

### SentinelOrchestrator

**Location:** `sentinel/core/orchestrator.py`

The central coordinator that implements the Sense-Decide-Act loop.

```python
class SentinelOrchestrator:
    """
    Main loop:
    1. Navigate to target URL
    2. For each step:
       a. SENSE: Build world state (DOMMapper + VisualAnalyzer)
       b. DECIDE: Choose action (DecisionEngine)
       c. ACT: Execute action (ActionExecutor)
       d. Check if goal achieved
    3. Generate report (FlightRecorder)
    """
```

**Key Methods:**
| Method | Description |
|--------|-------------|
| `_initialize()` | Lazy initialization of all layers |
| `run()` | Execute the main loop |
| `_handle_blocked_state()` | Recovery from modal/spinner states |
| `_goal_achieved()` | Heuristic + Rigorous goal completion check |
| `_extract_verify_text()` | Extract assertion targets from goal string |
| `_text_visible_on_page()` | High-fidelity visibility check |

**State Management:**
```python
self._driver          # WebDriver instance
self._stealth_manager # StealthBot context manager
self._dom_mapper      # Sense: DOMMapper
self._visual_analyzer # Sense: VisualAnalyzer
self._executor        # Action: ActionExecutor
self._brain           # Intelligence: DecisionEngine
self._recorder        # Reporting: FlightRecorder
```

### Driver Factory

**Location:** `sentinel/core/driver_factory.py`

Creates enhanced WebDriver instances with optional features.

```python
def create_driver(
    headless: bool = False,
    stealth_mode: bool = False,
    profile_path: Optional[str] = None,
    enable_shadow_dom: bool = True,
    enable_stability: bool = True,
    stability_timeout: int = 15,
    mutation_threshold: int = 200,
    stability_mode: str = "relaxed",
) -> WebDriver
```

**Enhancement Pipeline:**
```
Chrome Driver
    │
    ├── Stealth Options (anti-detection)
    │
    ├── Lumos (Shadow DOM support)
    │
    └── Waitless (UI stability wrapper)
```

**StealthDriverManager:**

For `sb-stealth-wrapper` integration which requires context manager usage:

```python
class StealthDriverManager:
    """Wraps StealthBot for unified interface."""
    
    def __enter__(self):
        self._stealth_bot = StealthBot(headless=self.headless)
        self._stealth_bot.__enter__()
        self._driver = self._stealth_bot.sb
        return self
    
    @property
    def driver(self):
        return self._driver
    
    def safe_get(self, url):
        return self._stealth_bot.safe_get(url)
```

---

## Layer Deep Dives

### Sense Layer

**Purpose:** Build a complete understanding of the current page state.

#### DOMMapper

**Location:** `sentinel/layers/sense/dom_mapper.py`

Discovers all interactive elements, including those inside Shadow DOMs.

**ElementNode Structure:**
```python
@dataclass
class ElementNode:
    id: str                    # Unique identifier
    tag: str                   # HTML tag name
    text: str                  # Visible text content
    attributes: Dict[str, str] # All attributes
    selector: str              # CSS selector path
    is_interactive: bool       # Button, input, link, etc.
    is_visible: bool           # Currently visible
    in_shadow_dom: bool        # Inside Shadow DOM
    shadow_host: Optional[str] # Host element if in shadow
    bounding_box: Dict         # Position and size
```

**Discovery Algorithm:**
```python
def get_world_state(self) -> List[ElementNode]:
    """
    1. Query all interactive elements via JavaScript
    2. For each element:
       a. Extract attributes and position
       b. Build CSS selector path
       c. Check visibility
    3. If lumos available:
       a. Traverse Shadow DOM hosts
       b. Discover shadow elements
    4. Return unified list
    """
```

**Performance Optimization:**

Uses single JavaScript execution for speed:
```javascript
// Single JS call to get all elements
return Array.from(document.querySelectorAll('button, a, input, ...'))
    .filter(el => el.offsetParent !== null)
    .map(el => ({
        tag: el.tagName,
        text: el.textContent,
        // ... 
    }));
```

#### VisualAnalyzer

**Location:** `sentinel/layers/sense/visual_analyzer.py`

Detects UI states that would block interaction.

**Detection Categories:**
| Category | Detection Method |
|----------|------------------|
| Modal Overlays | CSS selectors + position/size check |
| Loading Spinners | Class names + CSS animations |
| Captchas | Text patterns + iframe inspection |
| Page Ready | `document.readyState` + jQuery.active |

**Optimized Detection:**

All checks run in single JavaScript execution to avoid waitless delays:
```python
def _has_modal_overlay(self) -> Tuple[bool, str]:
    script = """
    const selectors = ['.modal', '.overlay', ...];
    for (const selector of selectors) {
        // Check in JS, not Python
    }
    return {blocked: false, reason: ''};
    """
    return self.driver.execute_script(script)
```

### Intelligence Layer

**Purpose:** Decide what action to take based on goal and current state.

#### DecisionEngine

**Location:** `sentinel/layers/intelligence/decision_engine.py`

**Decision Structure:**
```python
@dataclass
class Decision:
    action: str      # "click", "type", "scroll", "wait"
    target: str      # CSS selector or descriptor
    value: str       # For "type" action - what to type
    reasoning: str   # Why this decision was made
    confidence: float # 0.0 to 1.0
```

**Decision Algorithm (Heuristic Mode):**
```python
def decide(self, goal, world_state, history) -> Decision:
    """
    1. Parse goal for keywords (click, type, submit, etc.)
    2. Score each element based on:
       - Text match with goal keywords
       - Tag relevance (button > div for "click")
       - Attribute matches (id, name, aria-label)
       - Previous interaction history
    3. Select highest-scoring element
    4. Determine appropriate action
    5. Calculate confidence score
    """
```

**Scoring Example:**
```python
def _score_element(self, element, goal_keywords):
    score = 0.0
    
    # Text match
    if any(kw in element.text.lower() for kw in goal_keywords):
        score += 0.5
    
    # Tag relevance
    if element.tag in ["BUTTON", "A", "INPUT"]:
        score += 0.2
    
    # Attribute match
    if any(kw in element.id.lower() for kw in goal_keywords):
        score += 0.3
    
    return min(score, 1.0)
```

**Brain Implementations (v0.2.0):**

```python
# HeuristicBrain - Fast, no external dependencies
from sentinel.layers.intelligence.brains import HeuristicBrain
brain = HeuristicBrain()

# LocalBrain - Privacy-first, local SLM
from sentinel.layers.intelligence.brains import LocalBrain
brain = LocalBrain(model_path="phi-3-mini.gguf")

# CloudBrain - Maximum intelligence
from sentinel.layers.intelligence.brains import CloudBrain
brain = CloudBrain(provider="openai", model="gpt-4")
```

### Action Layer

**Purpose:** Execute decisions reliably with recovery mechanisms.

#### ActionExecutor

**Location:** `sentinel/layers/action/executor.py`

**Supported Actions:**
| Action | Description |
|--------|-------------|
| `click` | Click on element |
| `type` | Type text into input |
| `scroll` | Scroll element into view |
| `wait` | Explicit wait |
| `navigate` | Go to URL |

**Execution Pipeline:**
```python
def execute(self, decision: Decision) -> bool:
    """
    1. Resolve target to WebElement
    2. Scroll element into view
    3. Execute action via native waitless-wrapped driver
    4. Handle navigation-induced exceptions during stability checks
    5. Return success/failure
    """
```

**Waitless-Native Architecture (v0.3.0):**

Unlike previous versions that used explicit `WebDriverWait` loops, the v0.3.0 ActionExecutor relies almost entirely on the **Waitless-native driver**. Every `find_element` call is automatically wrapped with mutation-rate analysis, ensuring that the agent never acts on a moving or settling UI.

**Retry Logic:**
```python
def _execute_with_retry(self, action_fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return action_fn()
        except StaleElementReferenceException:
            # Self-healing: Re-find element and retry
            pass
        except ElementClickInterceptedException:
            # Self-healing: Try JavaScript fallback
            self.driver.execute_script("arguments[0].click();", element)
    return False
```

#### Teleporter

**Location:** `sentinel/layers/action/teleporter.py`

Manages browser session state and context switching.

**Features:**
| Feature | Description |
|---------|-------------|
| `save_state()` | Capture cookies, localStorage, sessionStorage |
| `load_state()` | Restore previous state |
| `switch_to_iframe()` | Navigate iframe hierarchy |
| `switch_to_window()` | Handle multiple tabs |

**State Persistence:**
```python
@dataclass
class BrowserState:
    cookies: List[Dict]
    local_storage: Dict[str, str]
    session_storage: Dict[str, str]
    current_url: str
    timestamp: datetime
```

### Validation Layer

**Purpose:** Test resilience through UI mutation.

#### UIMutator

**Location:** `sentinel/layers/validation/mutator.py`

**Mutation Strategies:**
| Strategy | Effect |
|----------|--------|
| `stealth_disable` | Disable element without visual change |
| `ghost_element` | Hide element but preserve space |
| `data_sabotage` | Corrupt text content slightly |
| `logic_sabotage` | Remove event handlers |
| `ui_shift` | Move element position |

**Mutation Testing Flow:**
```python
mutator = UIMutator(driver)

# Apply mutation
mutation = mutator.apply_mutation("#submit-btn", "stealth_disable")

# Run test
test_passed = your_test_function()

# Verify test detected mutation
if not test_passed:
    print("Test correctly caught the mutation!")

# Revert
mutator.revert_mutation(mutation)
```

### Reporting Layer

**Purpose:** Record all decisions for debugging and analysis.

#### FlightRecorder

**Location:** `sentinel/reporters/flight_recorder.py`

**Event Types:**
| Type | Data Captured |
|------|---------------|
| `navigation` | URL navigated to |
| `world_state` | Element count, blocked status |
| `decision` | Action, target, confidence |
| `action` | Success/failure, error |
| `warning` | Non-fatal issues |
| `error` | Exceptions and failures |

**Report Generation:**
```python
def generate_report(self) -> str:
    """
    1. Compile all log entries
    2. Generate HTML with:
       - Summary statistics
       - Decision timeline
       - Screenshots
       - Error details
    3. Save JSON log for programmatic access
    """
```

#### SessionReplayer

**Location:** `sentinel/reporters/session_replayer.py`

Replays and debugs past exploration sessions.

**Key Classes:**
```python
@dataclass
class ReplayStep:
    step_number: int
    timestamp: datetime
    event_type: str
    message: str
    data: Dict[str, Any]
    screenshot_path: Optional[str]

@dataclass  
class ReplaySession:
    run_id: str
    url: str
    goal: str
    steps: List[ReplayStep]
    success: bool
```

**Usage:**
```python
from sentinel.reporters.session_replayer import SessionReplayer

replayer = SessionReplayer("./sentinel_reports/20251227_074249")
session = replayer.load()

# View summary
replayer.print_summary()

# Iterate decisions
for decision in replayer.get_decisions():
    print(f"{decision.action} -> {decision.target}")

# Re-execute on browser
results = replayer.replay_on_browser(driver, step_mode=True)
```

---

## Data Flow

### Request Flow

```
User Goal: "Add 'Buy milk' to the todo list"
           │
           ▼
┌─────────────────────────────────────┐
│         SentinelOrchestrator        │
│  ┌───────────────────────────────┐  │
│  │     Initialize Components     │  │
│  └───────────────────────────────┘  │
│                 │                    │
│                 ▼                    │
│  ┌───────────────────────────────┐  │
│  │      Navigate to URL          │  │
│  └───────────────────────────────┘  │
│                 │                    │
│                 ▼                    │
│  ┌─────────────────────────────────────────────┐
│  │              MAIN LOOP                      │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│  │  │  SENSE  │──│ DECIDE  │──│   ACT   │     │
│  │  └─────────┘  └─────────┘  └─────────┘     │
│  │       │            │            │          │
│  │       ▼            ▼            ▼          │
│  │  WorldState    Decision    ActionResult    │
│  │       │            │            │          │
│  │       └────────────┴────────────┘          │
│  │                    │                       │
│  │                    ▼                       │
│  │            Goal Achieved?                  │
│  │               /      \                     │
│  │             Yes       No                   │
│  │              │         └─── Loop Again     │
│  │              ▼                             │
│  │         SUCCESS                            │
│  └─────────────────────────────────────────────┘
│                 │                    │
│                 ▼                    │
│  ┌───────────────────────────────┐  │
│  │      Generate Report          │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
           │
           ▼
    ExecutionResult
```

### State Flow

```
              ┌──────────────┐
              │  Page Load   │
              └──────┬───────┘
                     │
                     ▼
    ┌────────────────────────────────┐
    │         DOMMapper              │
    │  ┌──────────────────────────┐  │
    │  │  Standard DOM Elements   │  │
    │  └──────────────────────────┘  │
    │  ┌──────────────────────────┐  │
    │  │  Shadow DOM Elements     │  │◄─── lumos
    │  └──────────────────────────┘  │
    └────────────────┬───────────────┘
                     │
                     ▼
              ┌──────────────┐
              │  WorldState  │
              │  (Elements)  │
              └──────┬───────┘
                     │
                     ▼
    ┌────────────────────────────────┐
    │        VisualAnalyzer          │
    │  ┌──────────────────────────┐  │
    │  │  Modal Detection         │  │
    │  │  Spinner Detection       │  │
    │  │  Captcha Detection       │  │
    │  └──────────────────────────┘  │
    └────────────────┬───────────────┘
                     │
                     ▼
              ┌──────────────┐
              │   Blocked?   │
              │   (yes/no)   │
              └──────────────┘
```

---

## Extending The Sentinel

### Custom Decision Engine

```python
from sentinel.layers.intelligence.decision_engine import DecisionEngine, Decision

class CustomDecisionEngine(DecisionEngine):
    """Add custom decision logic."""
    
    def decide(self, goal, world_state, history):
        # Your custom logic
        if "login" in goal.lower():
            return self._handle_login_flow(goal, world_state)
        
        # Fall back to parent
        return super().decide(goal, world_state, history)
    
    def _handle_login_flow(self, goal, world_state):
        # Custom login handling
        pass
```

### Custom Action

```python
from sentinel.layers.action.executor import ActionExecutor

class CustomExecutor(ActionExecutor):
    """Add custom actions."""
    
    def execute(self, decision):
        if decision.action == "my_custom_action":
            return self._execute_custom_action(decision)
        return super().execute(decision)
    
    def _execute_custom_action(self, decision):
        # Your custom action
        pass
```

### Custom Reporter

```python
from sentinel.reporters.flight_recorder import FlightRecorder

class CustomRecorder(FlightRecorder):
    """Add custom logging."""
    
    def log_custom_event(self, data):
        self.entries.append(LogEntry(
            timestamp=datetime.now(),
            step=len(self.entries),
            event_type="custom",
            message="Custom event",
            data=data
        ))
```

---

## Integration Points

### With pytest

```python
import pytest
from sentinel import SentinelOrchestrator

@pytest.fixture
def agent():
    agent = SentinelOrchestrator(
        url="https://example.com",
        goal="Run test",
        training_mode=True
    )
    yield agent
    agent.close()

def test_autonomous_flow(agent):
    result = agent.run()
    assert result.success
```

### With CI/CD

```yaml
# GitHub Actions example
test-autonomous:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Setup Chrome
      uses: browser-actions/setup-chrome@latest
    - name: Install
      run: pip install the-sentinel
    - name: Run exploration
      run: |
        sentinel explore "${{ env.TEST_URL }}" "Verify homepage" \
          --headless --max-steps 10
```

---

## Performance Considerations

### Speed Optimizations

1. **JavaScript-based queries**: Faster than multiple `find_element` calls
2. **Relaxed waitless config**: Avoids over-waiting
3. **Lazy initialization**: Components created on first use
4. **Single-pass analysis**: Visual checks in one JS execution

### Memory Management

1. **World state trimming**: Only visible elements retained
2. **Report streaming**: Large reports written incrementally
3. **Screenshot compression**: Optional WebP format

### Scaling

| Scenario | Recommendation |
|----------|----------------|
| Single test | Use as-is |
| Test suite | Share driver between tests |
| Parallel | Use separate drivers per worker |
| CI/CD | Headless mode + lower max_steps |

---

## Testing Architecture

### Unit Tests

```python
# tests/unit/test_decision_engine.py
def test_decision_engine_click():
    engine = DecisionEngine(mock_mode=True)
    
    elements = [
        MockElement(tag="BUTTON", text="Submit"),
        MockElement(tag="DIV", text="Submit"),
    ]
    
    decision = engine.decide("Click submit button", elements, [])
    
    assert decision.action == "click"
    assert "button" in decision.target.lower()
```

### Integration Tests

```python
# tests/integration/test_orchestrator.py
def test_full_exploration():
    agent = SentinelOrchestrator(
        url="https://demo.playwright.dev/todomvc/",
        goal="Add 'Test item'",
        training_mode=True,
        max_steps=5
    )
    
    result = agent.run()
    
    assert result.steps > 0
    assert result.report_path is not None
    agent.close()
```

---

## Development Phases

### ✅ Completed (v0.3.0)
- Local SLM Integration (Phi-3, Mistral)
- Self-Healing Actions (JS fallback, stale element recovery)
- Vision Foundation (VisualAgent basic integration)
- Session Replay (view and re-execute past sessions)
- **Waitless-Native Drive** (Robustness hardening)
- **Rigorous Verification Engine** (Assert mode)
- **Multi-State Visual Logging**

### 🔄 In Progress (v0.4.0)
- Human-in-the-Loop mode
- Visual regression comparison
- Test generation from exploration

### 🔮 Future
- Multi-Agent parallel exploration
- Distributed testing
- Shared knowledge graph
- VLM-dominant reasoning flow (GPT-4o / GPT-4V)

---

**For more details, see the source code and inline documentation.**
