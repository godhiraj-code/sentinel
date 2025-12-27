from sentinel.core.orchestrator import SentinelOrchestrator
import os

def test_v050_verification_loop():
    """
    Integration test for Phase 3 Verification Loop.
    Goal: Add a todo, then verify it exists.
    Tests:
    1. Action execution + immediate verification (DOM change)
    2. Step transition (Click -> Verify)
    3. Final goal achievement via text presence
    """
    goal = "Type 'Verification Test' in the todo input and then verify 'Verification Test' appears"
    
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
    
    # Check if reports captured the verification signals
    # (We can't easily check report content in a simple script, but success is a good proxy)
    
    assert result.success is True
    assert result.steps >= 2

if __name__ == "__main__":
    test_v050_verification_loop()
