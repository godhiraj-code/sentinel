# Changelog

All notable changes to The Sentinel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-12-27

### Added
- **Unified Perception**: Implemented `Unified JS Mapper` for O(1) vectorized element sensing, providing 100x speedup on large commercial sites.
- **Adaptive Stealth Pivot**: New mechanism to automatically detect bot-blocks and re-launch the browser in Undetected Chrome (UC) mode mid-mission.
- **Structured Goal Parser**: New `RegexGoalParser` decomposes complex natural language into discrete `GoalStep` instances.
- **Multi-Step Execution**: Support for chaining actions with conjunctions like "and then", "then", and "finally".
- **Rigorous Verification**: Enhanced goal perception to support explicit verification clauses (e.g., `"verify the title 'X' appears"`).
- **Multi-State Visual Logging**: Added 3-point screenshot capture (Navigation, World State, After Action) for high-fidelity debugging.
- **Waitless-Native Drive**: Orchestrator and ActionExecutor now use a native waitless-wrapped driver, ensuring zero stability signal bypasses.
- **Wikipedia Optimization**: Fixed perception bottlenecks that caused hangs on text-heavy, high-element-count pages.

### Fixed
- **Waitless Bypass**: Fixed architectural flaws where `WebDriverWait` was bypassing the `waitless` stabilization layer.
- **Click Detection Flakiness**: Significantly improved `ActionExecutor.click` success detection during page transitions and animations.
- **Config Propagation**: Fixed issues where `waitless` stability parameters were not propagating correctly from CLI/API to the driver.

### Updated
- **SentinelOrchestrator API**: Added `stability_timeout`, `mutation_threshold`, and `stability_mode` parameters to the constructor.
- **FlightRecorder**: Added `log_info` support and updated emoji-rich event logging.

---

## [0.2.0] - 2025-12-27

### Added
- **Local Intelligence**: Integrated `LocalBrain` via `llama-cpp-python` for privacy-first, offline SLM support (Phi-3, Mistral).
- **Intelligence Tests**: Established unit testing for `DecisionEngine` and `Brain` implementations.
- **Branding Refresh**: Aligned the project as "The Selenium of the AI Era."
- **Self-Healing Actions**: `ActionExecutor` now re-resolves stale elements and uses JavaScript fallback for intercepted clicks.
- **Vision Foundation**: Created `VisualAgent` base class for future VLM integration.
- **VLM Integration**: Full `VisualAgent` implementation with Moondream2, OpenAI, and mock backends.
  - `describe_state()`: Analyze screenshots and describe UI
  - `find_element()`: Locate elements by natural language description
  - `verify_action()`: Compare before/after screenshots to verify action success
- **Session Replay**: New `sentinel replay` command to view and re-execute past exploration sessions.
  - `--rerun`: Re-execute actions on a live browser
  - `--step`: Pause after each step for inspection

### Updated
- **Core Dependencies**: Updated `sb-stealth-wrapper` (0.3.0), `waitless` (0.3.2), and `selenium-chatbot-test` (0.2.0).
- **Selector Management**: Improved reliability via updated `waitless` stabilization signals.
- **Element Finding**: Added `WebDriverWait` with `expected_conditions` for smarter element resolution.
- **Orchestrator**: Added `use_vision` parameter to enable VLM-based visual analysis.

---

## [0.1.0] - 2024-12-25

### Added

#### Core Framework
- **SentinelOrchestrator**: Main controller implementing Sense-Decide-Act loop
- **ExecutionResult**: Structured result object with success status, steps, and decisions
- **SentinelConfig**: Configuration dataclass for all options

#### Sense Layer
- **DOMMapper**: Discovers all interactive DOM elements
- **Shadow DOM Support**: Integrates lumos-shadowdom for Web Components
- **VisualAnalyzer**: Detects modals, spinners, captchas, and blocked states

#### Intelligence Layer
- **DecisionEngine**: Heuristic-based decision making with confidence scores
- **Decision dataclass**: Structured representation of agent decisions

#### Action Layer
- **ActionExecutor**: Reliable execution with retry logic
- **Teleporter**: Session state management via selenium-teleport
- **StealthDriverManager**: Bot evasion via sb-stealth-wrapper

#### Validation Layer
- **UIMutator**: UI mutation testing via project-vandal
- Multiple mutation strategies (stealth_disable, ghost_element, data_sabotage, etc.)

#### Reporting
- **FlightRecorder**: Comprehensive logging of all decisions
- HTML report generation with decision timeline
- JSON export for programmatic access

#### CLI
- `sentinel explore`: Autonomous website exploration
- `sentinel stress`: UI mutation stress testing
- `sentinel doctor`: System health check
- `sentinel version`: Version information

#### Documentation
- Comprehensive README
- User Guide with CLI and API reference
- Technical Guide with architecture deep-dive
- Blog post introducing the project
- Contributing guidelines
- Example scripts (basic, shadow DOM, stealth, mutation testing)

### Technical Details
- Python 3.9+ support
- Selenium 4.x base
- Click-based CLI with Rich formatting
- Modular layer architecture
- Graceful degradation for missing dependencies

### Known Limitations
- Heuristic-only decision making (LLM integration coming)
- Limited to Chrome browser
- Some complex goals may require breakdown into steps

---

## Future Releases

### [0.2.0] - Planned Q1 2025
- Local SLM integration (phi-3-mini via llama-cpp-python)
- Cloud LLM fallback for complex decisions
- pytest-mockllm integration for testing
- Improved goal understanding

### [0.3.0] - Planned Q2 2025
- Visual regression via visual-guard
- Screenshot-based element detection
- Before/after comparison in reports
- Visual change alerts

### [0.4.0] - Planned Q3 2025  
- Self-healing capabilities
- Automatic selector recovery
- Test generation from exploration
- Failure pattern learning

---

[Unreleased]: https://github.com/godhiraj-code/sentinel/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/godhiraj-code/sentinel/releases/tag/v0.1.0
