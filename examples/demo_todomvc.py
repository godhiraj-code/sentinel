"""
End-to-End Demo: Sentinel on TodoMVC

This script demonstrates Sentinel's autonomous web testing capabilities
on the Playwright TodoMVC demo site.

Goal: Add 'Buy milk' to the todo list
"""

from sentinel import SentinelOrchestrator
import time

def main():
    print("=" * 60)
    print("🛡️  THE SENTINEL - End-to-End Demo")
    print("=" * 60)
    print()
    print("Target: https://demo.playwright.dev/todomvc/")
    print("Goal: Add 'Buy milk' to the todo list")
    print()
    print("Starting autonomous exploration...")
    print("-" * 60)
    
    # Create the Sentinel agent
    agent = SentinelOrchestrator(
        url="https://demo.playwright.dev/todomvc/",
        goal="Add 'Buy milk' to the todo list",
        stealth_mode=False,  # TodoMVC doesn't need stealth
        headless=False,      # Show the browser so we can watch
        max_steps=15,        # Limit steps for demo
        brain_type="heuristic",  # Use fast heuristic brain for demo
    )
    
    start_time = time.time()
    
    # Run the agent
    result = agent.run()
    
    elapsed = time.time() - start_time
    
    print("-" * 60)
    print()
    
    if result.success:
        print("✅ SUCCESS! Goal achieved!")
    else:
        print(f"❌ Failed: {result.error}")
    
    print()
    print(f"📊 Statistics:")
    print(f"   Steps taken: {result.steps}")
    print(f"   Time elapsed: {elapsed:.2f}s")
    print(f"   Decisions made: {len(result.decisions)}")
    print()
    
    print("📝 Decision Timeline:")
    for i, decision in enumerate(result.decisions, 1):
        confidence_bar = "█" * int(decision.confidence * 10) + "░" * (10 - int(decision.confidence * 10))
        print(f"   {i}. [{confidence_bar}] {decision.action.upper()} → {decision.target[:40]}")
        print(f"      Reason: {decision.reasoning[:60]}...")
    
    print()
    print(f"📄 Full report: {result.report_path}")
    print()
    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
