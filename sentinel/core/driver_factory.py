"""
Driver Factory - Unified WebDriver creation with stealth capabilities.

Provides a single interface to create WebDriver instances with optional
stealth mode (via sb-stealth-wrapper), Shadow DOM support (via lumos),
and stability features (via waitless).
"""

from typing import Optional, Union, Any
from contextlib import contextmanager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

# Type alias for driver - can be extended to support other wrappers
WebDriverType = webdriver.Chrome


class StealthDriverManager:
    """
    Manages a StealthBot session for stealth web automation.
    
    StealthBot from sb-stealth-wrapper must be used as a context manager.
    This class wraps it to provide a unified interface.
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self._stealth_bot = None
        self._sb = None  # SeleniumBase BaseCase
        self._driver = None  # Actual WebDriver
        
    def __enter__(self):
        from sb_stealth_wrapper import StealthBot
        self._stealth_bot = StealthBot(headless=self.headless)
        self._stealth_bot.__enter__()
        # After entering context, sb is initialized (BaseCase)
        self._sb = self._stealth_bot.sb
        # Get the actual WebDriver from BaseCase
        self._driver = self._sb.driver
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._stealth_bot:
            return self._stealth_bot.__exit__(exc_type, exc_val, exc_tb)
        return False
    
    @property
    def driver(self):
        """Get the underlying Selenium WebDriver."""
        return self._driver
    
    @property 
    def sb(self):
        """Get the SeleniumBase BaseCase for native SB methods."""
        return self._sb
    
    def safe_get(self, url: str):
        """Navigate to URL with challenge handling."""
        if self._stealth_bot:
            return self._stealth_bot.safe_get(url)
    
    def smart_click(self, selector: str):
        """Click element with stealth and retries."""
        if self._stealth_bot:
            return self._stealth_bot.smart_click(selector)
    
    def save_screenshot(self, name: str):
        """Save a debug screenshot."""
        if self._stealth_bot:
            return self._stealth_bot.save_screenshot(name)


def create_driver(
    headless: bool = False,
    stealth_mode: bool = False,
    profile_path: Optional[str] = None,
    enable_shadow_dom: bool = True,
    enable_stability: bool = True,
    # Waitless stability config
    stability_timeout: int = 15,
    mutation_threshold: int = 200,
    stability_mode: str = "relaxed",
) -> WebDriverType:
    """
    Create a WebDriver instance with optional enhancements.
    
    Args:
        headless: Run browser in headless mode
        stealth_mode: Enable bot detection bypass (uses sb-stealth-wrapper)
        profile_path: Path to browser profile for session persistence
        enable_shadow_dom: Enable Shadow DOM support (uses lumos-shadowdom)
        enable_stability: Enable UI stability features (uses waitless)
    
    Returns:
        Enhanced WebDriver instance
    
    Note:
        For stealth mode, use create_stealth_context() instead for proper
        context management of StealthBot.
    
    Example:
        >>> driver = create_driver(stealth_mode=False)
        >>> driver.get("https://example.com")
    """
    # For stealth mode, we use a standard driver with stealth options
    # Full stealth requires context manager - use create_stealth_context()
    driver = _create_standard_driver(headless, profile_path, stealth_mode)
    
    # Apply enhancements
    if enable_shadow_dom:
        driver = _apply_shadow_dom_support(driver)
    
    if enable_stability:
        driver = _apply_stability_wrapper(
            driver,
            timeout=stability_timeout,
            mutation_threshold=mutation_threshold,
            strictness=stability_mode,
        )
    
    return driver


@contextmanager
def create_stealth_context(headless: bool = False):
    """
    Create a stealth driver context using sb-stealth-wrapper.
    
    This is the recommended way to use stealth mode as it properly
    manages the StealthBot lifecycle.
    
    Example:
        >>> with create_stealth_context(headless=False) as stealth:
        ...     stealth.safe_get("https://example.com")
        ...     stealth.smart_click("#button")
    """
    try:
        manager = StealthDriverManager(headless=headless)
        with manager:
            yield manager
    except ImportError:
        import warnings
        warnings.warn(
            "sb-stealth-wrapper not installed. Using standard driver. "
            "Install with: pip install sb-stealth-wrapper",
            UserWarning
        )
        driver = _create_standard_driver(headless)
        try:
            yield driver
        finally:
            driver.quit()


def _create_standard_driver(
    headless: bool = False,
    profile_path: Optional[str] = None,
    stealth_options: bool = False,
) -> webdriver.Chrome:
    """Create a standard Chrome WebDriver with optional stealth options."""
    options = ChromeOptions()
    
    if headless:
        options.add_argument("--headless=new")
    
    if profile_path:
        options.add_argument(f"--user-data-dir={profile_path}")
    
    # Common stability options
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    if stealth_options:
        # Additional stealth options
        options.add_argument("--disable-infobars")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(options=options)
    
    # Remove webdriver property to reduce detection
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        }
    )
    
    return driver


def _apply_shadow_dom_support(driver: WebDriverType) -> WebDriverType:
    """
    Apply Shadow DOM support using lumos-shadowdom.
    
    Adds find_shadow(), find_all_shadow(), and find_shadow_text() methods.
    """
    try:
        from lumos import Lumos
        
        # Wrap driver with Shadow DOM capabilities
        # Lumos adds shadow DOM methods to the driver
        lumos = Lumos(driver)
        # Mark driver as lumos-wrapped for feature detection
        driver._lumos_instance = lumos
        driver._lumos_wrapped = True
        return driver
    except ImportError:
        import warnings
        warnings.warn(
            "lumos-shadowdom not installed. Shadow DOM features disabled. "
            "Install with: pip install lumos-shadowdom",
            UserWarning
        )
        return driver
    except Exception as e:
        import warnings
        warnings.warn(
            f"Lumos initialization failed: {e}. Shadow DOM features disabled.",
            UserWarning
        )
        return driver


def _apply_stability_wrapper(
    driver: WebDriverType,
    timeout: int = 15,
    mutation_threshold: int = 200,
    strictness: str = "relaxed",
) -> WebDriverType:
    """
    Apply UI stability features using waitless.
    
    Wraps all actions with automatic quiescence detection.
    
    Args:
        driver: WebDriver to wrap
        timeout: Seconds to wait for stability (default: 15)
        mutation_threshold: DOM mutations/sec considered stable (default: 200)
        strictness: 'strict', 'normal', or 'relaxed' (default: 'relaxed')
    """
    try:
        from waitless import stabilize, StabilizationConfig
        
        # Use user-configurable parameters
        config = StabilizationConfig(
            timeout=timeout,
            strictness=strictness,
            mutation_rate_threshold=mutation_threshold,
            debug_mode=False,
        )
        
        stabilized = stabilize(driver, config=config)
        # Mark driver as waitless-wrapped for feature detection
        stabilized._waitless_wrapped = True
        return stabilized
    except ImportError:
        import warnings
        warnings.warn(
            "waitless not installed. Stability features disabled. "
            "Install with: pip install waitless",
            UserWarning
        )
        return driver
    except Exception as e:
        import warnings
        warnings.warn(
            f"Waitless initialization failed: {e}. Stability features disabled.",
            UserWarning
        )
        return driver
