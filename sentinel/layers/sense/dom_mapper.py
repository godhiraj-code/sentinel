"""
DOM Mapper - Unified Element Discovery.

Uses lumos-shadowdom to pierce Shadow DOMs and build a complete
element map that any AI agent can use for decision-making.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import hashlib

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement


@dataclass
class ElementNode:
    """
    Represents an interactive element in the World State.
    
    This is a universal representation that works for both
    standard DOM elements and Shadow DOM elements.
    """
    id: str  # Unique identifier for this element
    tag: str  # HTML tag name (e.g., "button", "input")
    text: str  # Visible text content
    selector: str  # CSS selector for standard DOM
    shadow_path: Optional[str] = None  # Lumos path for Shadow DOM
    attributes: Dict[str, str] = field(default_factory=dict)
    bounding_box: Dict[str, float] = field(default_factory=dict)
    is_visible: bool = True
    is_interactive: bool = True
    element_type: str = "standard"  # "standard", "shadow", "canvas"
    context_text: str = "" # Surrounding text context for disambiguation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "tag": self.tag,
            "text": self.text,
            "selector": self.selector,
            "shadow_path": self.shadow_path,
            "attributes": self.attributes,
            "bounding_box": self.bounding_box,
            "is_visible": self.is_visible,
            "is_interactive": self.is_interactive,
            "element_type": self.element_type,
            "context_text": self.context_text,
        }
    
    def __str__(self) -> str:
        """Human-readable representation for LLM prompts."""
        text_preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        attrs = ", ".join(f'{k}="{v}"' for k, v in self.attributes.items() if k in ["id", "class", "name", "type", "placeholder"])
        context = f" [Context: {self.context_text[:30]}]" if self.context_text else ""
        return f"<{self.tag} {attrs}>{text_preview}</{self.tag}>{context}"


class DOMMapper:
    """
    Builds a complete map of all interactive elements.
    
    Combines standard Selenium element discovery with Shadow DOM
    traversal via lumos-shadowdom to create a unified "World State".
    
    Example:
        >>> mapper = DOMMapper(driver)
        >>> elements = mapper.get_world_state()
        >>> for elem in elements:
        ...     print(f"{elem.tag}: {elem.text}")
    """
    
    # Elements that are typically interactive
    INTERACTIVE_TAGS = [
        "a", "button", "input", "select", "textarea",
        "label", "option", "details", "summary",
    ]
    
    # Attributes that indicate interactivity
    INTERACTIVE_ATTRIBUTES = [
        "onclick", "onchange", "onsubmit", "href",
        "role", "tabindex", "contenteditable",
    ]
    
    def __init__(self, driver: "WebDriver"):
        """
        Initialize the DOM mapper.
        
        Args:
            driver: Selenium WebDriver (optionally wrapped with lumos)
        """
        self.driver = driver
        self._has_lumos = self._check_lumos_support()
    
    def _check_lumos_support(self) -> bool:
        """Check if the driver has Shadow DOM support via lumos."""
        return hasattr(self.driver, "find_shadow")
    
    def get_world_state(self) -> List[ElementNode]:
        """
        Discover ALL interactive elements including Shadow DOM.
        
        Returns:
            List of ElementNode objects representing the world state
        """
        elements: List[ElementNode] = []
        
        # Map standard DOM elements
        elements.extend(self._map_standard_dom())
        
        # Map Shadow DOM elements (if lumos is available)
        if self._has_lumos:
            elements.extend(self._map_shadow_elements())
        
        # Deduplicate by ID
        seen_ids = set()
        unique_elements = []
        for elem in elements:
            if elem.id not in seen_ids:
                seen_ids.add(elem.id)
                unique_elements.append(elem)
        
        return unique_elements
    
    def _map_standard_dom(self) -> List[ElementNode]:
        """Map all interactive elements in the standard DOM using a single JS pass."""
        elements: List[ElementNode] = []
        
        # Build selector for interactive elements
        selector = ", ".join(self.INTERACTIVE_TAGS)
        selector += ", [onclick], [onchange], [role='button'], [role='link'], [tabindex]"
        
        try:
            # Execute unified mapper script
            script = self._get_unified_mapper_script()
            results = self.driver.execute_script(script, selector)
            
            for idx, res in enumerate(results):
                try:
                    # Generate unique ID in Python
                    unique_str = f"{res['tag']}_{res['attributes'].get('id', '')}_{res['attributes'].get('class', '')}_{res['text'][:20]}_{idx}"
                    element_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]
                    
                    node = ElementNode(
                        id=element_id,
                        tag=res['tag'],
                        text=res['text'],
                        selector=res['selector'],
                        shadow_path=None,
                        attributes=res['attributes'],
                        bounding_box=res['rect'],
                        is_visible=True,  # JS filter ensures visibility
                        is_interactive=True,
                        element_type="standard",
                        context_text=res['context'],
                    )
                    elements.append(node)
                except Exception:
                    continue
        except Exception as e:
            # Fallback to slow mapping if script fails
            print(f"WARNING: Unified mapper failed ({e}), falling back to slow mode...")
            try:
                web_elements = self.driver.find_elements("css selector", selector)
                for idx, elem in enumerate(web_elements):
                    node = self._element_to_node(elem, idx)
                    if node and node.is_visible:
                        elements.append(node)
            except Exception:
                pass
        
        return elements

    def _get_unified_mapper_script(self) -> str:
        """Get the JavaScript for vectorized element mapping."""
        return r"""
        const selector = arguments[0];
        const elements = document.querySelectorAll(selector);
        
        const isVisible = (el) => {
            if (el.checkVisibility) return el.checkVisibility();
            return el.offsetWidth > 0 && el.offsetHeight > 0;
        };

        const getStableSelector = (el) => {
            if (el.id && !/^\d/.test(el.id)) return '#' + CSS.escape(el.id);
            const dataAttrs = ['data-testid', 'data-id', 'data-automation'];
            for (let attr of dataAttrs) {
                let val = el.getAttribute(attr);
                if (val) return '[' + attr + '="' + CSS.escape(val) + '"]';
            }
            return el.tagName.toLowerCase();
        };

        return Array.from(elements)
            .filter(isVisible)
            .slice(0, 500)
            .map(el => {
                const rect = el.getBoundingClientRect();
                const attrs = {};
                for (let attr of ['id', 'class', 'role', 'name', 'href', 'aria-label']) {
                    let val = el.getAttribute(attr);
                    if (val) attrs[attr] = val.substring(0, 100);
                }
                return {
                    tag: el.tagName.toLowerCase(),
                    text: (el.innerText || "").substring(0, 100).trim(),
                    selector: getStableSelector(el),
                    context: "",
                    rect: { x: rect.left, y: rect.top, width: rect.width, height: rect.height },
                    attributes: attrs
                };
            });
        """
    
    def _map_shadow_elements(self) -> List[ElementNode]:
        """
        Map elements inside Shadow DOMs using lumos.
        
        This discovers shadow roots and maps their interactive contents.
        """
        elements: List[ElementNode] = []
        
        if not self._has_lumos:
            return elements
        
        # Find all shadow hosts
        try:
            shadow_hosts = self._find_shadow_hosts()
            
            for host in shadow_hosts:
                # For each shadow host, try to find interactive elements
                shadow_elements = self._map_shadow_host_contents(host)
                elements.extend(shadow_elements)
        except Exception:
            pass
        
        return elements
    
    def _find_shadow_hosts(self) -> List["WebElement"]:
        """Find all elements that have shadow roots."""
        # Execute JavaScript to find all shadow hosts
        script = """
        const hosts = [];
        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_ELEMENT,
            null,
            false
        );
        
        let node;
        while (node = walker.nextNode()) {
            if (node.shadowRoot) {
                hosts.push(node);
            }
        }
        return hosts;
        """
        
        try:
            return self.driver.execute_script(script)
        except Exception:
            return []
    
    def _map_shadow_host_contents(self, host: "WebElement") -> List[ElementNode]:
        """Map interactive elements inside a shadow root."""
        elements: List[ElementNode] = []
        
        # Get the tag name for building the lumos path
        try:
            host_tag = host.tag_name
            host_id = host.get_attribute("id") or ""
            
            # Build selector for interactive elements in shadow
            interactive_selector = ", ".join(self.INTERACTIVE_TAGS)
            
            # Use lumos to find elements
            if hasattr(self.driver, "find_all_shadow"):
                # Try common patterns
                for tag in self.INTERACTIVE_TAGS[:5]:  # Limit to avoid slowdown
                    try:
                        # Build lumos path pattern
                        if host_id:
                            path = f"#{host_id} >> {tag}"
                        else:
                            path = f"{host_tag} >> {tag}"
                        
                        shadow_elems = self.driver.find_all_shadow(path, timeout=2)
                        
                        for idx, elem in enumerate(shadow_elems):
                            node = self._element_to_node(
                                elem, 
                                idx,
                                shadow_path=path,
                                element_type="shadow"
                            )
                            if node and node.is_visible:
                                elements.append(node)
                    except Exception:
                        continue
        except Exception:
            pass
        
        return elements
    
    def _element_to_node(
        self,
        element: "WebElement",
        index: int,
        shadow_path: Optional[str] = None,
        element_type: str = "standard"
    ) -> Optional[ElementNode]:
        """Convert a Selenium WebElement to an ElementNode."""
        try:
            tag = element.tag_name
            text = element.text.strip() if element.text else ""
            
            # Get key attributes
            attrs = {}
            for attr in ["id", "class", "name", "type", "placeholder", "href", "value", "aria-label"]:
                try:
                    val = element.get_attribute(attr)
                    if val:
                        attrs[attr] = val[:100]  # Limit length
                except Exception:
                    pass
            
            # Check visibility
            is_visible = element.is_displayed()
            
            # Check if interactive
            is_interactive = (
                tag in self.INTERACTIVE_TAGS or
                any(attr in attrs for attr in ["onclick", "href", "role"]) or
                attrs.get("role") in ["button", "link", "checkbox", "tab"]
            )
            
            # Get bounding box
            try:
                rect = element.rect
                bounding_box = {
                    "x": rect.get("x", 0),
                    "y": rect.get("y", 0),
                    "width": rect.get("width", 0),
                    "height": rect.get("height", 0),
                }
            except Exception:
                bounding_box = {}
            
            # Performance Optimization: Calculate Selector AND Context in ONE call
            # This avoids double round-trips to the browser.
            
            try:
                # UNWRAP WAITLESS ELEMENT: Fix for JSON serialization error
                script_arg = element
                
                # Recursive unwrap to handle nested wrappers
                max_unwrap = 5
                while max_unwrap > 0:
                    if hasattr(script_arg, "wrapped_element"):
                        script_arg = script_arg.wrapped_element
                    elif hasattr(script_arg, "_element"):
                        script_arg = script_arg._element
                    else:
                        break
                    max_unwrap -= 1

                js_result = self.driver.execute_script("""
                    const el = arguments[0];
                    if (!el) return {selector: "", context: ""};

                    // --- A. SELECTOR GENERATION ---
                    // --- A. SELECTOR GENERATION (Robust & Stable) ---
                    const getStableSelector = (el) => {
                        if (el.id && !/^\d/.test(el.id)) return '#' + el.id;
                        
                        let path = [];
                        let cur = el;
                        while (cur && cur.nodeType === Node.ELEMENT_NODE) {
                            let part = cur.nodeName.toLowerCase();
                            // If we find a stable ID, anchor there and stop
                            if (cur.id && !/^\d/.test(cur.id)) {
                                path.unshift('#' + cur.id);
                                break;
                            }
                            // Use classes as secondary stabilizers
                            if (cur.className && typeof cur.className === 'string') {
                                const classes = cur.className.trim().split(/\s+/).filter(c => !c.match(/hover|active|focus|selected/));
                                if (classes.length > 0) part += '.' + classes[0];
                            }
                            
                            let sib = cur, nth = 1;
                            while (sib = sib.previousElementSibling) {
                                if (sib.nodeName === cur.nodeName) nth++;
                            }
                            if (nth !== 1) part += `:nth-of-type(${nth})`;
                            
                            path.unshift(part);
                            cur = cur.parentNode;
                        }
                        return path.join(" > ");
                    };
                    const uniqueSelector = getStableSelector(el);

                    // --- B. CONTEXT DISCOVERY (Breadcrumbs) ---
                    const getContextBreadcrumbs = (el) => {
                        let breadcrumbs = [];
                        
                        // 1. Direct Hints
                        const aria = el.getAttribute('aria-label') || el.title || el.placeholder;
                        if (aria) breadcrumbs.push(aria);
                        
                        // 2. Traversal for Titles & Containers
                        const isHeading = (node) => {
                            const tag = node.tagName;
                            if (/H[1-6]/.test(tag)) return true;
                            if (['STRONG', 'B', 'LEGEND', 'SUMMARY'].includes(tag)) return true;
                            if (node.getAttribute('role') === 'heading') return true;
                            const cls = (node.className || "").toString().toLowerCase();
                            return !!cls.match(/title|header|heading|name|label/);
                        };

                        let cur = el.parentElement;
                        let seenTexts = new Set();
                        while (cur && cur.tagName !== 'BODY' && breadcrumbs.length < 3) {
                            // Check for headings within or above the container
                            const headings = Array.from(cur.querySelectorAll('*'))
                                .filter(h => isHeading(h) && (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING))
                                .map(h => h.innerText.trim())
                                .filter(t => t.length > 2 && t.length < 100);
                            
                            if (headings.length > 0) {
                                const h = headings[headings.length - 1];
                                if (!seenTexts.has(h)) {
                                    breadcrumbs.unshift(h);
                                    seenTexts.add(h);
                                }
                            }
                            
                            // Check for data-attributes (often used in modern frameworks for context)
                            const dataset = cur.dataset;
                            const metaKeys = Object.keys(dataset).filter(k => k.match(/name|title|label|item|id/i));
                            for (let k of metaKeys) {
                                if (dataset[k] && !seenTexts.has(dataset[k])) {
                                    breadcrumbs.unshift(dataset[k]);
                                    seenTexts.add(dataset[k]);
                                }
                            }
                            
                            cur = cur.parentElement;
                        }
                        
                        return breadcrumbs.join(" > ");
                    };

                    const context = getContextBreadcrumbs(el);
                    return {selector: uniqueSelector, context: context};
                """, script_arg)
                
                selector = js_result.get("selector", "")
                context_text = js_result.get("context", "")
            except Exception:
                selector = f"xpath://{tag}"
                context_text = ""
                pass
            
            # Generate unique ID
            unique_str = f"{tag}_{attrs.get('id', '')}_{attrs.get('class', '')}_{text[:20]}_{index}"
            element_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]
            
            return ElementNode(
                id=element_id,
                tag=tag,
                text=text,
                selector=selector,
                shadow_path=shadow_path,
                attributes=attrs,
                bounding_box=bounding_box,
                is_visible=is_visible,
                is_interactive=is_interactive,
                element_type=element_type,
                context_text=context_text,
            )
        except Exception:
            return None
    
    def find_by_text(self, text: str) -> Optional[ElementNode]:
        """Find an element by its visible text content."""
        world_state = self.get_world_state()
        
        # Exact match first
        for node in world_state:
            if node.text.lower() == text.lower():
                return node
        
        # Partial match
        for node in world_state:
            if text.lower() in node.text.lower():
                return node
        
        return None
    
    def find_by_role(self, role: str) -> List[ElementNode]:
        """Find all elements with a specific role."""
        world_state = self.get_world_state()
        return [
            node for node in world_state
            if node.attributes.get("role") == role or node.tag == role
        ]
    def get_page_snapshot(self) -> str:
        """
        Produce a lightweight hash of the current page state.
        Uses URL + interactive element count + first 10 element texts.
        Used for fast before/after comparison.
        """
        try:
            url = self.driver.current_url
            elements = self.get_world_state()
            
            # Combine signals
            signals = [url, str(len(elements))]
            for elem in elements[:10]:
                signals.append(f"{elem.tag}:{elem.text[:20]}")
            
            combined = "|".join(signals)
            return hashlib.md5(combined.encode()).hexdigest()
        except Exception:
            return "unknown_state"
