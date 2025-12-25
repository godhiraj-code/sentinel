#!/usr/bin/env python3
"""
UI Mutation Testing Example
===========================

This example demonstrates how to use The Sentinel's UI mutation
testing capabilities to stress-test your test suites.

UI mutation testing intentionally breaks the UI in subtle ways
to verify that your tests can detect problems.

Usage:
    python examples/mutation_testing.py
"""

from selenium import webdriver
from sentinel.core.driver_factory import create_driver
from sentinel.layers.validation import UIMutator


def main():
    """Run UI mutation testing demonstration."""
    
    print("=" * 60)
    print("🛡️ The Sentinel - UI Mutation Testing")
    print("=" * 60)
    print()
    
    # Create a driver
    print("Creating driver...")
    driver = create_driver(
        headless=False,
        stealth_mode=False,
    )
    
    try:
        # Navigate to a test page
        url = "https://demo.playwright.dev/todomvc/"
        print(f"Navigating to: {url}")
        driver.get(url)
        print(f"Page title: {driver.title}")
        print()
        
        # Create the UI mutator
        mutator = UIMutator(driver)
        
        # Available mutation strategies:
        # 1. stealth_disable - Disable element without visual change
        # 2. ghost_element - Hide element but preserve space
        # 3. data_sabotage - Corrupt text content slightly
        # 4. logic_sabotage - Remove event handlers
        # 5. ui_shift - Move element position
        
        print("Available Mutation Strategies:")
        print("-" * 40)
        print("  • stealth_disable - Disables click handling")
        print("  • ghost_element - Makes element invisible")
        print("  • data_sabotage - Corrupts text content")
        print("  • logic_sabotage - Removes event handlers")
        print("  • ui_shift - Moves element position")
        print()
        
        # Find an element to mutate
        # For TodoMVC, let's target the input field
        target_selector = ".new-todo"
        
        print(f"Target element: {target_selector}")
        print()
        
        # Apply a stealth_disable mutation
        print("Applying 'stealth_disable' mutation...")
        print("-" * 40)
        
        mutation = mutator.apply_mutation(target_selector, "stealth_disable")
        
        if mutation:
            print(f"✅ Mutation applied!")
            print(f"   Type: {mutation.strategy}")
            print(f"   Target: {mutation.selector}")
            print(f"   Timestamp: {mutation.timestamp}")
            print()
            
            # Now run your test - it should fail because the element is disabled
            print("Now run your test...")
            print("The input should not work because it's been sabotaged!")
            print()
            
            # Simulate a test
            input("Press Enter to revert the mutation...")
            
            # Revert the mutation
            print()
            print("Reverting mutation...")
            mutator.revert_mutation(mutation)
            print("✅ Mutation reverted - element should work again")
            
        else:
            print("❌ Could not apply mutation to element")
            print("   (Element may not exist or be accessible)")
        
        print()
        
        # Demonstrate multiple mutations
        print("Demonstrating Multiple Mutations:")
        print("-" * 40)
        
        mutations = []
        
        # Apply different mutations to test robustness
        test_mutations = [
            ("h1", "data_sabotage"),
            (".todoapp", "ui_shift"),
        ]
        
        for selector, strategy in test_mutations:
            print(f"Applying {strategy} to {selector}...")
            mutation = mutator.apply_mutation(selector, strategy)
            if mutation:
                mutations.append(mutation)
                print(f"  ✅ Applied")
            else:
                print(f"  ⚠️ Could not apply")
        
        print()
        print(f"Total mutations applied: {len(mutations)}")
        
        if mutations:
            print()
            input("Press Enter to revert all mutations...")
            
            # Revert all
            print("Reverting all mutations...")
            mutator.revert_all()
            print("✅ All mutations reverted")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    
    finally:
        print()
        print("Closing browser...")
        driver.quit()
        print("Done!")


def stress_test_example():
    """
    Example of how to use mutations for stress testing.
    
    This pattern helps verify that your test suite is resilient:
    1. Apply a mutation (break something)
    2. Run your tests
    3. Verify tests detected the mutation
    4. Revert mutation
    """
    
    from sentinel.layers.validation import UIMutator
    
    driver = create_driver(headless=True)
    mutator = UIMutator(driver)
    
    try:
        driver.get("https://your-app.com")
        
        # Define what to mutate
        mutations_to_test = [
            ("#submit-btn", "stealth_disable"),
            ("#email-input", "ghost_element"),
            (".price-display", "data_sabotage"),
        ]
        
        results = []
        
        for selector, strategy in mutations_to_test:
            # Apply mutation
            mutation = mutator.apply_mutation(selector, strategy)
            
            if mutation:
                # Run your test suite
                # test_passed = run_your_tests()
                test_passed = False  # Placeholder
                
                if not test_passed:
                    results.append((selector, strategy, "DETECTED"))
                else:
                    results.append((selector, strategy, "MISSED"))
                
                # Revert
                mutator.revert_mutation(mutation)
        
        # Report
        print("\nMutation Test Results:")
        print("-" * 50)
        for selector, strategy, status in results:
            icon = "✅" if status == "DETECTED" else "❌"
            print(f"{icon} {selector} ({strategy}): {status}")
        
        detected = sum(1 for _, _, s in results if s == "DETECTED")
        print(f"\nMutation Score: {detected}/{len(results)}")
        
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
    
    # Uncomment to run stress test example
    # stress_test_example()
