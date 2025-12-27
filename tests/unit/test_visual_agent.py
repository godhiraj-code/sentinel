"""
Unit tests for VisualAgent.

Tests the VLM integration with mock backend to avoid model downloads during CI.
"""

import pytest
from unittest.mock import MagicMock, patch
import os
import tempfile

from sentinel.layers.sense.visual_agent import VisualAgent, VisualElement


class TestVisualAgentMock:
    """Test VisualAgent with mock backend."""
    
    def test_init_with_mock(self):
        """Test initialization with mock backend."""
        agent = VisualAgent(backend="mock")
        assert agent.backend == "mock"
    
    def test_describe_state_mock(self):
        """Test describe_state returns a description."""
        agent = VisualAgent(backend="mock")
        
        # Create a temp file to simulate a screenshot
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name
        
        try:
            description = agent.describe_state(temp_path)
            assert "Login button" in description or "button" in description.lower()
            assert len(description) > 20
        finally:
            os.unlink(temp_path)
    
    def test_describe_state_missing_file(self):
        """Test describe_state handles missing files."""
        agent = VisualAgent(backend="mock")
        description = agent.describe_state("/nonexistent/path.png")
        assert "Error" in description
    
    def test_find_element_mock(self):
        """Test find_element returns coordinates."""
        agent = VisualAgent(backend="mock")
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name
        
        try:
            element = agent.find_element(temp_path, "login button")
            assert element is not None
            assert isinstance(element, VisualElement)
            assert element.x >= 0
            assert element.y >= 0
            assert element.confidence > 0
        finally:
            os.unlink(temp_path)
    
    def test_verify_action_mock(self):
        """Test verify_action returns confidence score."""
        agent = VisualAgent(backend="mock")
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            before_path = f.name
            
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data 2")
            after_path = f.name
        
        try:
            confidence = agent.verify_action(before_path, after_path, "clicked the button")
            assert 0.0 <= confidence <= 1.0
        finally:
            os.unlink(before_path)
            os.unlink(after_path)


class TestVisualAgentAutoDetect:
    """Test auto-detection of backend."""
    
    def test_auto_detect_falls_back_to_moondream(self):
        """Test that auto detection finds a backend."""
        # Clear OpenAI key to force non-openai detection
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            agent = VisualAgent(backend="auto")
            # Should fall back to moondream or mock
            assert agent.backend in ["moondream", "mock"]


class TestVisualElement:
    """Test VisualElement dataclass."""
    
    def test_visual_element_creation(self):
        """Test creating a VisualElement."""
        elem = VisualElement(
            description="login button",
            x=100, y=200,
            width=80, height=30,
            confidence=0.95
        )
        assert elem.description == "login button"
        assert elem.x == 100
        assert elem.confidence == 0.95
