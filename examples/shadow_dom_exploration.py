#!/usr/bin/env python3
"""
Shadow DOM Exploration Example
==============================

This example demonstrates how The Sentinel discovers and interacts
with elements inside Shadow DOM boundaries.

Shadow DOM creates encapsulated DOM trees that are invisible to
regular querySelector calls. The Sentinel uses lumos-shadowdom
to pierce these boundaries automatically.

Usage:
    python examples/shadow_dom_exploration.py
"""

from selenium import webdriver
from sentinel.core.driver_factory import create_driver
from sentinel.layers.sense import DOMMapper


def main():
    """Explore Shadow DOM elements."""
    
    print("=" * 60)
    print("🛡️ The Sentinel - Shadow DOM Exploration")
    print("=" * 60)
    print()
    
    # Create a driver with Shadow DOM support
    # The driver factory automatically wraps with lumos if available
    print("Creating enhanced driver...")
    driver = create_driver(
        headless=False,
        stealth_mode=False,
        enable_shadow_dom=True,
        enable_stability=True,
    )
    
    try:
        # Navigate to a page with Shadow DOM components
        # Note: This example uses Google's search page which has some Shadow DOM
        # You can replace this with your own Shadow DOM-heavy application
        
        url = "https://example.com"  # Replace with your Shadow DOM app
        print(f"Navigating to: {url}")
        driver.get(url)
        print(f"Page title: {driver.title}")
        print()
        
        # Create the DOM mapper
        mapper = DOMMapper(driver)
        
        # Get the complete world state (including Shadow DOM)
        print("Discovering elements...")
        print("-" * 40)
        
        elements = mapper.get_world_state()
        
        # Categorize elements
        standard_elements = [e for e in elements if not e.in_shadow_dom]
        shadow_elements = [e for e in elements if e.in_shadow_dom]
        
        print(f"Total interactive elements: {len(elements)}")
        print(f"  Standard DOM: {standard_elements}")
        print(f"  Shadow DOM: {len(shadow_elements)}")
        print()
        
        # Display standard DOM elements
        if standard_elements:
            print("Standard DOM Elements:")
            print("-" * 40)
            for elem in standard_elements[:10]:  # Show first 10
                text_preview = elem.text[:30] + "..." if len(elem.text) > 30 else elem.text
                print(f"  [{elem.tag}] {text_preview or '(no text)'}")
                print(f"    Selector: {elem.selector}")
                if elem.is_interactive:
                    print(f"    Interactive: ✅")
            
            if len(standard_elements) > 10:
                print(f"  ... and {len(standard_elements) - 10} more")
        
        print()
        
        # Display Shadow DOM elements
        if shadow_elements:
            print("Shadow DOM Elements:")
            print("-" * 40)
            for elem in shadow_elements[:10]:  # Show first 10
                text_preview = elem.text[:30] + "..." if len(elem.text) > 30 else elem.text
                print(f"  [{elem.tag}] {text_preview or '(no text)'}")
                print(f"    Shadow Host: {elem.shadow_host}")
                print(f"    Selector: {elem.selector}")
            
            if len(shadow_elements) > 10:
                print(f"  ... and {len(shadow_elements) - 10} more")
        else:
            print("No Shadow DOM elements found on this page.")
            print("Try with a page that uses Web Components.")
        
        print()
        
        # Demonstrate direct lumos access if available
        print("Checking lumos integration...")
        if hasattr(driver, '_lumos_instance'):
            print("✅ lumos-shadowdom is active")
            lumos = driver._lumos_instance
            
            # Try finding shadow elements directly
            # lumos.find_all_shadow() would work if there are shadow elements
            print("   Use driver._lumos_instance for direct Shadow DOM access")
        else:
            print("⚠️ lumos-shadowdom not available (fallback mode)")
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    
    finally:
        print()
        print("Closing browser...")
        driver.quit()
        print("Done!")


if __name__ == "__main__":
    main()
