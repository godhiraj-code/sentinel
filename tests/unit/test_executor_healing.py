import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch
from sentinel.layers.action.executor import ActionExecutor, ActionResult

class MockElement:
    def __init__(self, selector="#target"):
        self.selector = selector
        self.click_count = 0
        
    def click(self):
        self.click_count += 1
        # Simulate an intercepted click on first attempt
        if self.click_count == 1:
            raise Exception("ElementClickInterceptedException")
        return True

    def is_displayed(self):
        return True

def test_executor_js_fallback():
    """Test that ActionExecutor uses JS fallback when standard click fails."""
    mock_driver = MagicMock()
    # Simulate standard click always failing
    mock_element = MagicMock()
    mock_element.click.side_effect = Exception("Permanent Interception")
    
    executor = ActionExecutor(mock_driver)
    
    # Create a real-ish node
    @dataclass
    class Node:
        selector: str
        shadow_path: Optional[str] = None
        
    mock_node = Node(selector="#bad-btn")
    
    with patch.object(executor, "_find_element", return_value=mock_element):
        result = executor.click(mock_node)
        
        # Verify result
        assert result.success is True
        assert result.metadata.get("strategy") == "js_fallback"
        # Verify JS execution was called
        mock_driver.execute_script.assert_any_call("arguments[0].click();", mock_element)

def test_executor_stale_recovery():
    """Test that ActionExecutor re-resolves stale elements during retries."""
    mock_driver = MagicMock()
    executor = ActionExecutor(mock_driver)
    
    @dataclass
    class Node:
        selector: str
        shadow_path: Optional[str] = None
        
    mock_node = Node(selector="#stale-btn")
    
    # First resolve returns a stale mock, second resolve returns a fresh one
    stale_mock = MagicMock()
    # Mocking the exception explicitly to trigger the retry logic
    stale_mock.click.side_effect = Exception("StaleElementReferenceException")
    fresh_mock = MagicMock()
    
    with patch.object(executor, "_find_element") as mock_find:
        # Resolve happens once initially, then again inside the retry loop
        mock_find.side_effect = [stale_mock, stale_mock, fresh_mock]
        
        result = executor.click(mock_node)
        
        assert result.success is True
        assert fresh_mock.click.called
        assert mock_find.call_count >= 2
