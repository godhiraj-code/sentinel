#!/usr/bin/env python3
"""
Stealth Mode Example
====================

This example demonstrates how to use The Sentinel's stealth mode
to bypass bot detection systems like Cloudflare, reCAPTCHA, etc.

Stealth mode uses sb-stealth-wrapper (built on SeleniumBase UC Mode)
to present as a real browser and evade automation detection.

Usage:
    python examples/stealth_mode.py
"""

from sentinel import SentinelOrchestrator


def main():
    """Run an exploration with stealth mode enabled."""
    
    print("=" * 60)
    print("🛡️ The Sentinel - Stealth Mode Example")
    print("=" * 60)
    print()
    
    # Stealth mode is particularly useful for:
    # - Sites with Cloudflare protection
    # - Sites with bot detection (Akamai, PerimeterX, etc.)
    # - Sites that check automation flags
    # - Rate-limited APIs
    
    print("⚠️ Note: First run will download UC driver (~100MB)")
    print()
    
    # Create agent with stealth mode enabled
    agent = SentinelOrchestrator(
        url="https://nowsecure.nl/",  # Bot detection test site
        goal="Verify the page loads successfully and shows 'You are human'",
        stealth_mode=True,  # Enable bot evasion
        headless=False,  # Headed mode is more reliable for stealth
        training_mode=True,
        max_steps=5,
    )
    
    print(f"Target URL: {agent.config.url}")
    print(f"Goal: {agent.config.goal}")
    print(f"Stealth Mode: {'✅ Enabled' if agent.config.stealth_mode else '❌ Disabled'}")
    print()
    
    print("Starting stealth exploration...")
    print("-" * 40)
    
    try:
        result = agent.run()
        
        print()
        print("-" * 40)
        
        if result.success:
            print("✅ Successfully bypassed bot detection!")
        else:
            print(f"Result: {result.steps} steps executed")
            if result.error:
                print(f"Note: {result.error}")
        
        print()
        print(f"Duration: {result.duration_seconds:.2f}s")
        print(f"Report: {result.report_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        print()
        print("Troubleshooting tips:")
        print("  1. Try headed mode (headless=False)")
        print("  2. Check if site blocks VPNs")
        print("  3. Some sites may be impossible to automate")
    
    finally:
        print()
        print("Closing browser...")
        agent.close()
        print("Done!")


def compare_stealth_vs_normal():
    """Compare stealth mode vs normal mode on a detection site."""
    
    print("=" * 60)
    print("Comparing Stealth vs Normal Mode")
    print("=" * 60)
    print()
    
    # Test URL that detects bots
    test_url = "https://bot.sannysoft.com/"
    
    # Normal mode (will likely be detected)
    print("Testing NORMAL mode...")
    normal_agent = SentinelOrchestrator(
        url=test_url,
        goal="Check if we are detected as a bot",
        stealth_mode=False,
        max_steps=1,
    )
    
    try:
        normal_result = normal_agent.run()
        print(f"  Steps: {normal_result.steps}")
    finally:
        normal_agent.close()
    
    print()
    
    # Stealth mode (should evade detection)
    print("Testing STEALTH mode...")
    stealth_agent = SentinelOrchestrator(
        url=test_url,
        goal="Check if we are detected as a bot",
        stealth_mode=True,
        max_steps=1,
    )
    
    try:
        stealth_result = stealth_agent.run()
        print(f"  Steps: {stealth_result.steps}")
    finally:
        stealth_agent.close()
    
    print()
    print("Check the generated reports to see detection differences!")


if __name__ == "__main__":
    # Run the main example
    main()
    
    # Uncomment to run comparison
    # compare_stealth_vs_normal()
