from sentinel.core.orchestrator import SentinelOrchestrator
import os

def test_dhirajdas_dev_multi_step():
    """
    Integration test: Navigate -> Click Article -> Verify Title.
    Tests multi-step goal parsing and execution on dhirajdas.dev.
    """
    goal = "Click the Read Article button with class blog-nudge-button and then verify 'Announcing pytest-mockllm' appears"
    
    agent = SentinelOrchestrator(
        url="https://dhirajdas.dev",
        goal=goal,
        max_steps=10,
        headless=True
    )
    
    result = agent.run()
    
    print(f"Goal: {goal}")
    print(f"Success: {result.success}")
    print(f"Steps taken: {result.steps}")
    
    assert result.success is True
    assert result.steps >= 2
    
if __name__ == "__main__":
    test_dhirajdas_dev_multi_step()
