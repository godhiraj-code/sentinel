#!/usr/bin/env python3
"""
Basic Discovery Example
=======================

This example demonstrates how The Sentinel autonomously explores
a web application to achieve a goal.

Goal: Add a todo item to a TodoMVC application.

Usage:
    python examples/basic_discovery.py
"""

from sentinel import SentinelOrchestrator


def main():
    """Run a basic autonomous exploration."""
    
    print("=" * 60)
    print("🛡️ The Sentinel - Basic Discovery Example")
    print("=" * 60)
    print()
    
    # Create the autonomous agent
    # - url: The target website to explore
    # - goal: What we want to achieve (natural language)
    # - stealth_mode: Bypass bot detection (useful for protected sites)
    # - training_mode: Use heuristics instead of LLM (free, fast)
    # - max_steps: How many actions before giving up
    
    agent = SentinelOrchestrator(
        url="https://demo.playwright.dev/todomvc/",
        goal="Add 'Buy milk' to the todo list",
        stealth_mode=False,  # This demo site doesn't need stealth
        training_mode=True,  # Use heuristics (no API costs)
        max_steps=10,
        headless=False,  # Show the browser so we can watch
    )
    
    print(f"Target URL: {agent.config.url}")
    print(f"Goal: {agent.config.goal}")
    print(f"Max Steps: {agent.config.max_steps}")
    print()
    
    # Run the agent
    print("Starting exploration...")
    print("-" * 40)
    
    try:
        result = agent.run()
        
        print()
        print("-" * 40)
        print("Exploration Complete!")
        print()
        
        # Display results
        if result.success:
            print(f"✅ Goal achieved in {result.steps} steps!")
        else:
            print(f"❌ Goal not achieved after {result.steps} steps")
            if result.error:
                print(f"   Error: {result.error}")
        
        print()
        print(f"Duration: {result.duration_seconds:.2f} seconds")
        print(f"Report: {result.report_path}")
        
        # Show the decisions made
        if result.decisions:
            print()
            print("Decisions made:")
            for i, decision in enumerate(result.decisions, 1):
                confidence_icon = "🟢" if decision.confidence > 0.7 else "🟡" if decision.confidence > 0.4 else "🔴"
                print(f"  {i}. {confidence_icon} {decision.action}: {decision.target[:50]}")
                print(f"      Confidence: {decision.confidence:.0%}")
                print(f"      Reasoning: {decision.reasoning[:60]}...")
        
    except Exception as e:
        print(f"Error during exploration: {e}")
        raise
    
    finally:
        # Always clean up
        print()
        print("Closing browser...")
        agent.close()
        print("Done!")


if __name__ == "__main__":
    main()
