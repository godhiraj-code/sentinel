"""
UI Mutator - Mutation Testing Integration.

Uses vandal concepts to intentionally mutate the UI
and verify test resilience.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


@dataclass
class Mutation:
    """Represents a UI mutation."""
    name: str
    description: str
    element_selector: str
    mutation_type: str  # 'visibility', 'text', 'attribute', 'style', 'structure'
    original_state: Optional[str] = None
    mutated_state: Optional[str] = None
    reverted: bool = False


@dataclass 
class MutationResult:
    """Result of applying a mutation."""
    mutation: Mutation
    test_detected: bool  # Did the test catch this mutation?
    error_message: Optional[str] = None


class UIMutator:
    """
    UI Mutation Testing Engine.
    
    Applies intentional mutations to the UI to verify
    that tests are capable of detecting regressions.
    
    Mutation strategies:
    - stealth_disable: Disables buttons/inputs without visual change
    - ghost_element: Hides elements but keeps space
    - data_sabotage: Changes text/values slightly
    - logic_sabotage: Swaps element behaviors
    - ui_shift: Moves elements slightly
    - slow_load: Adds artificial delays
    
    Example:
        >>> mutator = UIMutator(driver)
        >>> mutation = mutator.apply_random_mutation()
        >>> # Run your test...
        >>> test_passed = run_test()
        >>> result = MutationResult(mutation, test_detected=not test_passed)
        >>> mutator.revert_mutation(mutation)
    """
    
    MUTATION_STRATEGIES = [
        "stealth_disable",
        "ghost_element", 
        "data_sabotage",
        "logic_sabotage",
        "ui_shift",
        "slow_load",
    ]
    
    def __init__(self, driver: "WebDriver"):
        """
        Initialize the UI mutator.
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self._vandal = self._init_vandal()
        self._applied_mutations: List[Mutation] = []
    
    def _init_vandal(self):
        """Try to initialize vandal if available."""
        try:
            from vandal import Vandal
            return Vandal(self.driver)
        except ImportError:
            return None
    
    def apply_mutation(
        self,
        selector: str,
        strategy: str = "stealth_disable",
    ) -> Mutation:
        """
        Apply a mutation to a specific element.
        
        Args:
            selector: CSS selector for target element
            strategy: Mutation strategy to use
        
        Returns:
            Mutation object with details
        """
        if self._vandal:
            # Use vandal library
            return self._apply_vandal_mutation(selector, strategy)
        else:
            # Fallback implementation
            return self._apply_fallback_mutation(selector, strategy)
    
    def apply_random_mutation(self, target_selectors: Optional[List[str]] = None) -> Mutation:
        """
        Apply a random mutation to a random element.
        
        Args:
            target_selectors: Optional list of selectors to choose from
        
        Returns:
            Mutation object with details
        """
        strategy = random.choice(self.MUTATION_STRATEGIES)
        
        if target_selectors:
            selector = random.choice(target_selectors)
        else:
            # Find interactive elements
            selector = self._find_random_interactive_element()
        
        return self.apply_mutation(selector, strategy)
    
    def revert_mutation(self, mutation: Mutation) -> bool:
        """
        Revert a previously applied mutation.
        
        Args:
            mutation: Mutation object to revert
        
        Returns:
            True if revert was successful
        """
        if mutation.reverted:
            return True
        
        if self._vandal:
            try:
                self._vandal.revert()
                mutation.reverted = True
                return True
            except Exception:
                return False
        
        # Fallback revert
        return self._revert_fallback_mutation(mutation)
    
    def revert_all_mutations(self) -> int:
        """
        Revert all applied mutations.
        
        Returns:
            Number of mutations reverted
        """
        reverted_count = 0
        for mutation in self._applied_mutations:
            if self.revert_mutation(mutation):
                reverted_count += 1
        
        self._applied_mutations.clear()
        return reverted_count
    
    def _apply_vandal_mutation(self, selector: str, strategy: str) -> Mutation:
        """Apply mutation using vandal library."""
        try:
            # Map strategy to vandal methods
            if strategy == "stealth_disable":
                self._vandal.sabotage_element(selector, "disable")
            elif strategy == "ghost_element":
                self._vandal.sabotage_element(selector, "hide")
            elif strategy == "data_sabotage":
                self._vandal.sabotage_element(selector, "corrupt_text")
            elif strategy == "logic_sabotage":
                self._vandal.sabotage_element(selector, "swap_action")
            elif strategy == "ui_shift":
                self._vandal.sabotage_element(selector, "shift")
            elif strategy == "slow_load":
                self._vandal.sabotage_element(selector, "delay")
            
            mutation = Mutation(
                name=f"{strategy}_{selector[:20]}",
                description=f"Applied {strategy} to {selector}",
                element_selector=selector,
                mutation_type=strategy,
            )
            self._applied_mutations.append(mutation)
            return mutation
        except Exception as e:
            return Mutation(
                name="failed",
                description=f"Failed to apply mutation: {e}",
                element_selector=selector,
                mutation_type=strategy,
            )
    
    def _apply_fallback_mutation(self, selector: str, strategy: str) -> Mutation:
        """Apply mutation using JavaScript fallback."""
        original_state = None
        
        try:
            if strategy == "stealth_disable":
                # Disable element without visual change
                original_state = self.driver.execute_script(f"""
                    const el = document.querySelector('{selector}');
                    const original = el.disabled;
                    el.disabled = true;
                    el.style.pointerEvents = 'none';
                    return original;
                """)
            
            elif strategy == "ghost_element":
                # Hide element but keep space
                original_state = self.driver.execute_script(f"""
                    const el = document.querySelector('{selector}');
                    const original = el.style.visibility;
                    el.style.visibility = 'hidden';
                    return original;
                """)
            
            elif strategy == "data_sabotage":
                # Change text content slightly
                original_state = self.driver.execute_script(f"""
                    const el = document.querySelector('{selector}');
                    const original = el.textContent;
                    el.textContent = original + ' ';  // Add invisible change
                    return original;
                """)
            
            elif strategy == "logic_sabotage":
                # Remove click handler
                original_state = self.driver.execute_script(f"""
                    const el = document.querySelector('{selector}');
                    const original = el.onclick;
                    el.onclick = (e) => e.preventDefault();
                    return 'onclick_removed';
                """)
            
            elif strategy == "ui_shift":
                # Shift element position
                original_state = self.driver.execute_script(f"""
                    const el = document.querySelector('{selector}');
                    const original = el.style.marginLeft;
                    el.style.marginLeft = '50px';
                    return original;
                """)
            
            elif strategy == "slow_load":
                # Add artificial delay (mark element)
                original_state = self.driver.execute_script(f"""
                    const el = document.querySelector('{selector}');
                    el.dataset.sentinelDelayed = 'true';
                    return 'delayed';
                """)
            
            mutation = Mutation(
                name=f"{strategy}_{selector[:20]}",
                description=f"Applied {strategy} to {selector}",
                element_selector=selector,
                mutation_type=strategy,
                original_state=str(original_state) if original_state else None,
            )
            self._applied_mutations.append(mutation)
            return mutation
            
        except Exception as e:
            return Mutation(
                name="failed",
                description=f"Failed to apply mutation: {e}",
                element_selector=selector,
                mutation_type=strategy,
            )
    
    def _revert_fallback_mutation(self, mutation: Mutation) -> bool:
        """Revert a fallback mutation."""
        try:
            selector = mutation.element_selector
            strategy = mutation.mutation_type
            original = mutation.original_state
            
            if strategy == "stealth_disable":
                self.driver.execute_script(f"""
                    const el = document.querySelector('{selector}');
                    el.disabled = {str(original).lower() if original else 'false'};
                    el.style.pointerEvents = '';
                """)
            
            elif strategy == "ghost_element":
                self.driver.execute_script(f"""
                    const el = document.querySelector('{selector}');
                    el.style.visibility = '{original or "visible"}';
                """)
            
            elif strategy == "data_sabotage":
                if original:
                    self.driver.execute_script(f"""
                        const el = document.querySelector('{selector}');
                        el.textContent = `{original}`;
                    """)
            
            elif strategy == "ui_shift":
                self.driver.execute_script(f"""
                    const el = document.querySelector('{selector}');
                    el.style.marginLeft = '{original or "0"}';
                """)
            
            mutation.reverted = True
            return True
            
        except Exception:
            return False
    
    def _find_random_interactive_element(self) -> str:
        """Find a random interactive element on the page."""
        try:
            selectors = self.driver.execute_script("""
                const elements = document.querySelectorAll('button, a, input, select');
                const visible = Array.from(elements).filter(el => 
                    el.offsetParent !== null && 
                    el.offsetWidth > 0 && 
                    el.offsetHeight > 0
                );
                return visible.slice(0, 10).map(el => {
                    if (el.id) return '#' + el.id;
                    if (el.className) return el.tagName.toLowerCase() + '.' + el.className.split(' ')[0];
                    return el.tagName.toLowerCase();
                });
            """)
            
            if selectors:
                return random.choice(selectors)
            return "button"
        except Exception:
            return "button"
    
    def run_mutation_test(
        self,
        test_function,
        selectors: Optional[List[str]] = None,
        num_mutations: int = 5,
    ) -> List[MutationResult]:
        """
        Run a mutation test suite.
        
        Args:
            test_function: Function that runs the test, returns True if passed
            selectors: Optional list of element selectors to mutate
            num_mutations: Number of mutations to apply
        
        Returns:
            List of MutationResult objects
        """
        results = []
        
        for _ in range(num_mutations):
            # Apply mutation
            mutation = self.apply_random_mutation(selectors)
            
            if mutation.name == "failed":
                continue
            
            # Run test
            try:
                test_passed = test_function()
                test_detected = not test_passed
            except Exception as e:
                test_detected = True
                
            results.append(MutationResult(
                mutation=mutation,
                test_detected=test_detected,
            ))
            
            # Revert mutation
            self.revert_mutation(mutation)
        
        return results
