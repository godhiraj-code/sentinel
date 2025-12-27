import pytest
from unittest.mock import MagicMock, patch
from sentinel.layers.intelligence.decision_engine import DecisionEngine
from sentinel.layers.intelligence.brains.base import Decision

class MockElement:
    def __init__(self, tag="button", text="Login", selector="#login", is_visible=True, is_interactive=True):
        self.tag = tag
        self.text = text
        self.selector = selector
        self.is_visible = is_visible
        self.is_interactive = is_interactive
        self.attributes = {}

def test_decision_engine_heuristic_fallback():
    """Test that DecisionEngine falls back to HeuristicBrain when brain_type is unknown."""
    engine = DecisionEngine(brain_type="unknown_brain")
    assert engine.brain_type == "heuristic"
    assert engine.brain.__class__.__name__ == "HeuristicBrain"

@patch("sentinel.core.system_profiler.SystemProfiler.get_profile")
def test_decision_engine_auto_selection(mock_get_profile):
    """Test that DecisionEngine auto-selects brain based on profile."""
    # Mock profile with no keys and low RAM
    mock_profile = MagicMock()
    mock_profile.has_openai_key = False
    mock_profile.has_anthropic_key = False
    mock_profile.total_ram_gb = 4.0
    mock_profile.can_run_local_slm = False
    mock_get_profile.return_value = mock_profile
    
    engine = DecisionEngine(brain_type="auto")
    # According to SystemProfiler logic, this should be 'heuristic'
    assert engine.brain.__class__.__name__ == "HeuristicBrain"

def test_heuristic_brain_decision():
    """Test that HeuristicBrain makes a sensible decision."""
    from sentinel.layers.intelligence.brains.heuristic_brain import HeuristicBrain
    brain = HeuristicBrain()
    
    goal = "click the login button"
    world_state = [
        MockElement(tag="button", text="Login", selector="#login"),
        MockElement(tag="div", text="Header", selector=".header", is_interactive=False)
    ]
    
    decision = brain.decide(goal, world_state, [])
    assert decision.action == "click"
    assert decision.target == "#login"
    assert decision.confidence >= 0.4
