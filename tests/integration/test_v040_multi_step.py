from sentinel.core.orchestrator import SentinelOrchestrator
import os

def test_todomvc_multi_step():
    """
    Integration test: Add two items and then verify.
    This tests the GoalParser's ability to split and the Orchestrator's 
    ability to transition between steps.
    """
    goal = "Type 'Buy Milk' in the todo input and then type 'Walk Dog' in the todo input and then verify 'Buy Milk' exists"
    
    agent = SentinelOrchestrator(
        url="https://demo.playwright.dev/todomvc/",
        goal=goal,
        max_steps=10,
        headless=True
    )
    
    result = agent.run()
    
    print(f"Goal: {goal}")
    print(f"Success: {result.success}")
    print(f"Steps taken: {result.steps}")
    
    assert result.success is True
    assert result.steps >= 3 # At least 3 logical steps
    
if __name__ == "__main__":
    test_todomvc_multi_step()
