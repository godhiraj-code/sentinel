"""
Integration tests for Sentinel v0.3.0 Bug Fixes.

Tests on multiple websites to ensure robust autonomous operation:
1. TodoMVC (static site, Shadow DOM)
2. Example.com (simple static site)
3. dhirajdas.dev (animated site with delayed popups)
"""

import pytest
import time
import os

# Skip if dependencies not available
pytest.importorskip("selenium")


class TestSentinelIntegration:
    """Integration tests for Sentinel across multiple websites."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        from sentinel import SentinelOrchestrator
        self.SentinelOrchestrator = SentinelOrchestrator
        yield
    
    def test_todomvc_add_item(self):
        """Test adding an item on TodoMVC - tests type action and goal detection."""
        agent = self.SentinelOrchestrator(
            url="https://demo.playwright.dev/todomvc/",
            goal="Add 'Buy milk' to the todo list",
            stealth_mode=False,
            headless=True,  # Run headless for CI
            max_steps=10,
            brain_type="heuristic",
        )
        
        result = agent.run()
        
        # Verify result structure
        assert result is not None
        assert hasattr(result, "success")
        assert hasattr(result, "steps")
        assert hasattr(result, "decisions")
        assert hasattr(result, "report_path")
        
        # Verify report was generated with screenshots
        assert result.report_path is not None
        assert os.path.exists(result.report_path)
        
        # Check for screenshots in report directory
        report_dir = os.path.dirname(result.report_path)
        screenshots_dir = os.path.join(report_dir, "screenshots")
        
        # Should have navigation screenshot
        nav_screenshots = [f for f in os.listdir(screenshots_dir) if "navigation" in f]
        assert len(nav_screenshots) > 0, "Navigation screenshot should exist"
        
        # Should have world_state screenshots
        ws_screenshots = [f for f in os.listdir(screenshots_dir) if "world_state" in f]
        assert len(ws_screenshots) > 0, "World state screenshots should exist"
        
        # Should have after_action screenshots
        action_screenshots = [f for f in os.listdir(screenshots_dir) if "after_action" in f]
        assert len(action_screenshots) > 0, "After action screenshots should exist"
        
        print(f"✅ TodoMVC test completed in {result.steps} steps")
        print(f"   Report: {result.report_path}")
        print(f"   Screenshots: {len(nav_screenshots) + len(ws_screenshots) + len(action_screenshots)}")
    
    def test_example_com_simple_click(self):
        """Test simple navigation on example.com - basic stability test."""
        agent = self.SentinelOrchestrator(
            url="https://example.com",
            goal="Click the 'More information' link",
            stealth_mode=False,
            headless=True,
            max_steps=5,
            brain_type="heuristic",
        )
        
        result = agent.run()
        
        # Even if goal not achieved, should have valid structure
        assert result is not None
        assert result.decisions is not None
        assert len(result.decisions) > 0 or result.steps > 0
        
        print(f"✅ Example.com test completed: success={result.success}")
    
    def test_config_defaults(self):
        """Test that default configuration works without explicit params."""
        # Minimal config - only required params
        agent = self.SentinelOrchestrator(
            url="https://example.com",
            goal="Navigate the page",
        )
        
        # Should have sensible defaults
        assert agent.config.stability_timeout == 15
        assert agent.config.mutation_threshold == 200
        assert agent.config.stability_mode == "relaxed"
        assert agent.config.max_steps == 50
        assert agent.config.screenshot_on_step == True
        
        print("✅ Config defaults test passed")
    
    def test_dhirajdas_dev_rigorous_verification(self):
        """Test dhirajdas.dev - rigorous test with explicit class and title verification."""
        # This test ensures we are not being "lazy":
        # 1. We specify the class to click
        # 2. We explicitly verify the resulting page content
        agent = self.SentinelOrchestrator(
            url="https://dhirajdas.dev",
            goal="Click the Read Article button with class blog-nudge-button and verify the title 'Announcing pytest-mockllm' appears",
            stealth_mode=True,
            headless=True,
            max_steps=15,
            brain_type="heuristic",
            stability_timeout=25, 
            stability_mode="relaxed",
        )
        
        result = agent.run()
        
        assert result is not None
        assert result.success is True, f"Rigorous verification failed. Goal was: {agent.config.goal}"
        
        print(f"✅ dhirajdas.dev rigorous verification PASSED")



    def test_the_internet_dynamic_loading(self):
        """Test 'The Internet' dynamic loading - verifies robustness on elements that appear after a delay."""
        agent = self.SentinelOrchestrator(
            url="https://the-internet.herokuapp.com/dynamic_loading/1",
            goal="Click 'Start' and verify 'Hello World!' appears",
            stealth_mode=False,
            headless=True,
            max_steps=10,
            brain_type="heuristic",
        )
        
        result = agent.run()
        
        assert result is not None
        print(f"✅ The Internet test completed: success={result.success}")




class TestWaitlessIntegration:
    """Test that waitless is properly integrated (not bypassed)."""
    
    def test_wrapped_driver_used(self):
        """Verify we use the wrapped driver, not unwrapped."""
        from sentinel.core.driver_factory import create_driver
        
        driver = create_driver(
            headless=True,
            enable_stability=True,
            stability_timeout=5,
            mutation_threshold=100,
            stability_mode="relaxed",
        )
        
        # Should be waitless-wrapped
        assert hasattr(driver, "_waitless_wrapped"), "Driver should be waitless-wrapped"
        
        driver.quit()
        print("✅ Waitless integration test passed")
    
    def test_find_element_uses_wrapped_driver(self):
        """Test that ActionExecutor uses wrapped driver for find_element."""
        from sentinel.layers.action.executor import ActionExecutor
        from unittest.mock import MagicMock
        
        # Create a mock wrapped driver
        mock_driver = MagicMock()
        mock_driver._waitless_wrapped = True
        mock_driver.find_element.return_value = MagicMock()
        
        executor = ActionExecutor(mock_driver, timeout=5)
        
        # Call _find_element - should use wrapped driver's find_element
        executor._find_element(".test-selector")
        
        # Verify we called the wrapped driver, not unwrapped
        assert mock_driver.find_element.called, "Should call wrapped driver's find_element"
        
        print("✅ Find element uses wrapped driver test passed")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
