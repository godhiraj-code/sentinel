# Implementation Plan: Adaptive Intelligence Layer

## Goal
Upgrade the `DecisionEngine` to support multiple intelligence backends (Heuristic, Cloud LLM, Local SLM) with automatic resource-aware selection. This enables "Sentinel" to run efficiently on low-end hardware (6GB RAM) while scaling up on powerful machines.

## User Review Required
> [!IMPORTANT]
> **New Dependency**: We will need `psutil` for system profiling.
> **Optional Dependencies**: `openai`, `anthropic` for cloud, `llama-cpp-python` for local.

## Proposed Changes

### 1. New Core Component: `SystemProfiler`
Create `sentinel/core/system_profiler.py` to detect capabilities.
- Check available RAM
- Check if CUDA/MPS is available
- Check for API keys in environment

### 2. Interface Definition: `BrainInterface`
Abstract base class for all brains in `sentinel/layers/intelligence/brains/base.py`.
- `decide(goal, world_state, history) -> Decision`

### 3. Brain Implementations
- `HeuristicBrain` (Refactored from current `DecisionEngine`)
- `CloudBrain` (OpenAI/Anthropic integration)
- `LocalBrain` (Phi-3 integration via GGUF)

### 4. Upgrade `DecisionEngine`
Refactor `sentinel/layers/intelligence/decision_engine.py` to be a **Router**.
- Accepts `brain_type` config ("auto", "heuristic", "cloud", "local").
- If "auto", uses `SystemProfiler` to pick the best implementation.

### 5. CLI Updates
Add `--brain [auto|heuristic|cloud|local]` and `--model <name>` flags.

## Data Flow
```mermaid
graph TD
    A[Orchestrator] -->|Asks for Decision| B[DecisionEngine (Router)]
    B -->|Check Config/Resources| C{Selector}
    C -->|Low RAM / No Keys| D[HeuristicBrain]
    C -->|API Key Present| E[CloudBrain]
    C -->|High RAM + GPU| F[LocalBrain]
    D --> G[Decision]
    E --> G
    F --> G
```

## Verification Plan
1. **Low Resource Test**: Mock `psutil` to report 4GB RAM -> Assert `HeuristicBrain` is chosen.
2. **Action Verification**: Ensure `HeuristicBrain` behaves exactly like the current implementation (no regression).
