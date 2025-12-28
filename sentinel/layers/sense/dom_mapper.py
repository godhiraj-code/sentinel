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
        "h1", "h2", "h3", "h4", "h5", "h6",
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
        
        # 0. FORCE STABILITY: Ensure page is stable before mapping
        # Calling find_elements triggers waitless if wrapped
        try:
            self.driver.find_elements("tag name", "body")
        except Exception:
            pass

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
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        };

        const getStableSelector = (el) => {
            if (el.id) {
                if (!/^\d/.test(el.id)) return '#' + CSS.escape(el.id);
                return '[id="' + CSS.escape(el.id) + '"]';
            }
            const dataAttrs = ['data-testid', 'data-id', 'data-automation'];
            for (let attr of dataAttrs) {
                let val = el.getAttribute(attr);
                if (val) return '[' + attr + '="' + CSS.escape(val) + '"]';
            }
            
            // Robust CSS Path Fallback
            try {
                const path = [];
                let cur = el;
                while (cur && cur.nodeType === Node.ELEMENT_NODE && cur.tagName !== 'HTML') {
                    let selector = cur.tagName.toLowerCase();
                    if (cur.id && !/^\d/.test(cur.id)) {
                        selector += '#' + CSS.escape(cur.id);
                        path.unshift(selector);
                        break;
                    }
                    
                    let sibling = cur;
                    let nth = 1;
                    while (sibling = sibling.previousElementSibling) {
                        if (sibling.tagName.toLowerCase() === selector) nth++;
                    }
                    selector += `:nth-of-type(${nth})`;
                    path.unshift(selector);
                    cur = cur.parentElement;
                }
                return path.join(' > ');
            } catch (e) {
                return el.tagName.toLowerCase();
            }
        };

        const getSemanticEnclosure = (el) => {
            let contextParts = [];
            let depth = 0;
            const maxDepth = 10;
            
            // 1. Check Preceding Siblings (Proximity Bonding)
            // Often Titles are siblings just above the button/card
            let sib = el.previousElementSibling;
            while (sib && contextParts.length < 5) {
                const text = (sib.innerText || "").trim();
                if (text.length > 2 && text.length < 200) {
                    if (!contextParts.includes(text)) contextParts.push(text);
                }
                sib = sib.previousElementSibling;
            }

            // 2. Check Ancestor Hierarchy (Standard Bonding)
            let cur = el.parentElement;
            while (cur && cur.tagName !== 'BODY' && depth < maxDepth) {
                // Find significant text labels in this container
                const labels = Array.from(cur.querySelectorAll('h1,h2,h3,h4,h5,h6,strong,b,legend,label,span,p,div'))
                    .filter(node => {
                        const text = (node.innerText || "").trim();
                        return text.length > 2 && text.length < 200 && node !== el && !node.contains(el);
                    })
                    .map(node => (node.innerText || "").trim());
                
                labels.forEach(l => {
                    if (!contextParts.includes(l)) contextParts.push(l);
                });
                
                // Also check preceding siblings of the container (Grid Sibling Bonding)
                let pSib = cur.previousElementSibling;
                while (pSib && contextParts.length < 10) {
                    const pText = (pSib.innerText || "").trim();
                    if (pText.length > 2 && pText.length < 200) {
                        if (!contextParts.includes(pText)) contextParts.push(pText);
                    }
                    pSib = pSib.previousElementSibling;
                }

                cur = cur.parentElement;
                depth++;
            }
            return contextParts.join(" | ");
        };

        const results = Array.from(elements)
            .filter(isVisible)
            .slice(0, 1000)
            .map(el => {
                const rect = el.getBoundingClientRect();
                const attrs = {};
                for (let attr of ['id', 'class', 'role', 'name', 'href', 'aria-label', 'placeholder']) {
                    let val = el.getAttribute(attr);
                    if (val) attrs[attr] = val.substring(0, 150);
                }
                return {
                    tag: el.tagName.toLowerCase(),
                    text: (el.innerText || "").substring(0, 200).trim(),
                    selector: getStableSelector(el),
                    context: getSemanticEnclosure(el),
                    rect: { x: rect.left, y: rect.top, width: rect.width, height: rect.height },
                    attributes: attrs
                };
            });

        // Add semantic landmarks that might have been missed by strict selector
        const headers = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
        headers.forEach(h => {
            if (isVisible(h) && !results.some(r => r.selector === getStableSelector(h))) {
                 const rect = h.getBoundingClientRect();
                 results.push({
                    tag: h.tagName.toLowerCase(),
                    text: (h.innerText || "").substring(0, 200).trim(),
                    selector: getStableSelector(h),
                    context: "Heading",
                    rect: { x: rect.left, y: rect.top, width: rect.width, height: rect.height },
                    attributes: { id: h.id, class: h.className }
                 });
            }
        });

        return results;
        """
    
    def _map_shadow_elements(self) -> List[ElementNode]:
        """
        Map elements inside Shadow DOMs using lumos.
        
        This discovers shadow roots and maps their interactive contents.
        """
        elements: List[ElementNode] = []
        
        if not self._has_lumos:
            return elements
        
        try:
            # Execute Deep Shadow DOM Walker
            # This traverses the entire shadow tree recursively in one go
            script = self._get_deep_shadow_script()
            results = self.driver.execute_script(script)
            
            for idx, res in enumerate(results):
                try:
                     # Generate unique ID
                    unique_str = f"shadow_{res['tag']}_{res['attributes'].get('id', '')}_{res['text'][:20]}_{idx}"
                    element_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]
                    
                    node = ElementNode(
                        id=element_id,
                        tag=res['tag'],
                        text=res['text'],
                        selector=res['path'], # Path is the deep selector
                        shadow_path=res['path'],
                        attributes=res['attributes'],
                        bounding_box=res['rect'],
                        is_visible=True,
                        is_interactive=True,
                        element_type="shadow",
                        context_text=res['context']
                    )
                    elements.append(node)
                except Exception:
                    continue
        except Exception as e:
            print(f"Shadow mapping error: {e}")
            pass
        
        # Fallback for YouTube - ALWAYS run this because JS often misses deep text in Polymer
        if "youtube.com" in self.driver.current_url:
            print("⚠️ Engaging Python fallback for YouTube stability...")
            fallback_elements = self._map_youtube_fallback()
            # De-duplicate based on text and rect
            existing_texts = {e.text for e in elements}
            for fe in fallback_elements:
                if fe.text not in existing_texts and len(fe.text) > 3:
                    elements.append(fe)
        
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
    
        return elements
    
    def _get_deep_shadow_script(self) -> str:
        """
        Get the JavaScript for recursive Shadow DOM traversal.
        Returns a list of interactive elements found within shadow roots.
        """
        return r"""
        const results = [];
        const seen = new Set();
        const isYoutube = window.location.hostname.includes('youtube');
        
        // Blocklist
        const ignoreTags = new Set(['script', 'style', 'noscript', 'meta', 'link', 'title', 'head', 'html', 'body']);
        
        // Standard interactive tags + Semantic Landmarks
        const baseTags = ['a', 'button', 'input', 'select', 'textarea', 'details', 'summary', 'iframe', 'canvas', 'video', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
        const youtubeTags = ['yt-formatted-string', 'ytd-thumbnail', 'ytd-video-renderer', 'ytd-rich-grid-media', 'span', 'h3', 'div'];
        
        const interactiveTags = new Set(baseTags);
        if (isYoutube) {
            youtubeTags.forEach(t => interactiveTags.add(t));
        }
        
        function getPath(el) {
            let path = [];
            let cur = el;
            while (cur) {
                if (cur.nodeType === Node.ELEMENT_NODE) {
                    let selector = cur.tagName.toLowerCase();
                    if (cur.id) selector += '#' + cur.id;
                    else if (cur.classList.length > 0) selector += '.' + cur.classList[0]; 
                    path.unshift(selector);
                }
                if (cur.parentNode && cur.parentNode.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
                    cur = cur.parentNode.host;
                    path.unshift('>>');
                } else {
                    cur = cur.parentNode;
                }
            }
            return path.join(' ').replace(/ >> /g, ' >> ');
        }
        
        function isVisible(el) {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return false;
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
        }

        function processNode(node) {
            if (!node || seen.has(node)) return;
            
            const tag = node.tagName.toLowerCase();
            if (ignoreTags.has(tag)) return;
            
            let shouldMap = false;
            
            // 1. Interactive Tag?
            if (interactiveTags.has(tag)) shouldMap = true;
            
            // 2. Interactive Attributes?
            if (node.hasAttribute('onclick') || node.getAttribute('role') === 'button' || node.getAttribute('role') === 'link') shouldMap = true;
            
            // 3. TEXT-BASED DISCOVERY (Semantic/Verification Targets)
            // We need to see text to verify goals (e.g. "Verify the header says...")
            const textContent = (node.innerText || "").trim();
            if (textContent.length > 0) {
                // Always map headers
                if (/^h[1-6]$/.test(tag)) {
                    shouldMap = true;
                }
                // Map significant but concise text blocks (likely verification targets)
                else if (textContent.length > 2 && textContent.length < 500) {
                    // Only map if it's a relative leaf (don't map large containers that just happen to have text)
                    if (node.children.length < 3) {
                         shouldMap = true;
                    }
                }
            }
            
            // 4. YouTube specific overrides (redundant now but kept for specificity)
            if (isYoutube && node.id === 'video-title') shouldMap = true;
            
            if (shouldMap && isVisible(node)) {
                seen.add(node);
                
                const attrs = {};
                for (let attr of ['id', 'class', 'role', 'name', 'href', 'title', 'aria-label']) {
                    let val = node.getAttribute(attr);
                    if (val) attrs[attr] = val.substring(0, 100);
                }
                
                const rect = node.getBoundingClientRect();
                
                results.push({
                    tag: tag,
                    text: (node.innerText || "").trim().substring(0, 200),
                    path: getPath(node),
                    context: "", 
                    rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
                    attributes: attrs
                });
            }
        }

        function findAllElements(root) {
            if (!root) return;
            
            // Direct processing
            if (root.nodeType === Node.ELEMENT_NODE) {
                processNode(root);
                if (root.shadowRoot) {
                    findAllElements(root.shadowRoot);
                }
            }

            // Children processing
            const children = root.children || root.childNodes;
            for (let i = 0; i < children.length; i++) {
                const node = children[i];
                if (node.nodeType === Node.ELEMENT_NODE) {
                    findAllElements(node);
                }
            }
        }
        
        // --- ENTRY POINT ---
        findAllElements(document.body);
        
        // Targeted Re-Entry for YouTube specific hosts (just in case)
        if (isYoutube) {
            const hosts = document.querySelectorAll('ytd-app, ytd-masthead, ytd-page-manager, ytd-browse, ytd-search, ytd-video-renderer, ytd-thumbnail');
            hosts.forEach(host => {
                if (host.shadowRoot) {
                    findAllElements(host.shadowRoot);
                }
            });
        }

        return results.slice(0, 1500); 
        """
    
    
    def _map_youtube_fallback(self) -> List[ElementNode]:
        """
        Python-side fallback for YouTube using Lumos, Native Selenium, AND Visual Guard.
        Includes robust retry logic for hydration handling.
        """
        elements = []
        renderers = []
        
        # Retry loop to handle hydration (Layer 3: Resilience)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 1. Try Lumos (Layer 1: Pierce)
                if hasattr(self.driver, "find_all_shadow"):
                    print(f"⚡ Lumos Scan (Attempt {attempt+1}/{max_retries})...")
                    renderers = self.driver.find_all_shadow("ytd-video-renderer")
                    # Also try specific title spans which might be easier to target
                    titles = self.driver.find_all_shadow("span#video-title")
                    if titles:
                        renderers.extend(titles)
                
                # 2. Native Fallback
                if not renderers:
                    print(f"⚠️ Native Scan (Attempt {attempt+1}/{max_retries})...")
                    renderers = self.driver.find_elements("css selector", "ytd-video-renderer, ytd-grid-video-renderer, span#video-title, #video-title")
                
                # Validation: Did we find anything REAL?
                if renderers:
                    # Check for Stale Elements by accessing one
                    _ = renderers[0].tag_name
                    print(f"✅ Found {len(renderers)} potential elements.")
                    break # Success!
                
            except Exception as e:
                print(f"   -> Scan error: {e}")
                renderers = [] # Reset to trigger retry
            
            # Wait for hydration
            if attempt < max_retries - 1:
                print("   -> Hydration wait (1s)...")
                time.sleep(1.0)
        
        # Layer 2: Visual Fallback (If DOM completely failed)
        if not renderers and VisualGuard:
            print("👁️ DOM Blind! Engaging VisualGuard (Layer 2)...")
            return self._map_visual_fallback()

        # Process found DOM elements
        try:
            for idx, el in enumerate(renderers):
                if not el.is_displayed():
                    continue
                    
                text = el.text.strip()
                # If text is empty, it might be a shadow host. Try getting innerText via JS.
                if not text:
                    text = self.driver.execute_script("return arguments[0].innerText || arguments[0].textContent", el).strip()
                
                # Still empty? Try attributes.
                if not text:
                    text = el.get_attribute("title") or el.get_attribute("aria-label") or ""
                
                if text and len(text) > 3:
                     # Generate unique ID
                    unique_str = f"yt_fallback_{idx}_{text[:20]}"
                    element_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]
                    
                    print(f"   -> Fallback Candidate: '{text[:40]}...'")
                    
                    rect = el.rect
                    
                    node = ElementNode(
                        id=element_id,
                        tag=el.tag_name,
                        text=text,
                        selector=f"fallback: {text[:30]}", 
                        shadow_path="",
                        attributes={"class": el.get_attribute("class"), "id": el.get_attribute("id")},
                        bounding_box=rect,
                        is_visible=True,
                        is_interactive=True,
                        element_type="fallback",
                        context_text="YouTube Video"
                    )
                    elements.append(node)
        except Exception as e:
            print(f"YouTube fallback error: {e}")
            
        return elements

    def _map_visual_fallback(self) -> List[ElementNode]:
        """
        Use VisualGuard to semantic analysis of the screenshot.
        """
        elements = []
        try:
            # Capture screenshot
            screenshot_path = f"visual_debug_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            
            # Detect text blocks
            guard = VisualGuard()
            text_blocks = guard.detect_text_blocks(screenshot_path)
            
            for idx, block in enumerate(text_blocks):
                if len(block.text) < 5: continue
                
                element_id = hashlib.md5(f"vis_{idx}_{block.text}".encode()).hexdigest()[:12]
                node = ElementNode(
                    id=element_id,
                    tag="visual-block",
                    text=block.text,
                    selector=f"fallback: {block.text}", # ActionExecutor handles this via text search
                    shadow_path="",
                    attributes={"confidence": str(block.confidence)},
                    bounding_box={"x": block.x, "y": block.y, "width": block.width, "height": block.height},
                    is_visible=True,
                    is_interactive=True,
                    element_type="visual",
                    context_text="Visual Text"
                )
                elements.append(node)
            
            print(f"👁️ VisualGuard found {len(elements)} items")
        except Exception as e:
            print(f"Visual fallback error: {e}")
            
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
            # Use URL, element count, and structural signals from top elements
            signals = [url, str(len(elements))]
            for elem in elements[:20]: # Check more elements
                # Use tag and classes as they are more structurally stable than text
                classes = elem.attributes.get("class", "")
                # Only use first few chars of text to avoid dynamic updates (timers, etc.)
                text_len = str(len(elem.text)) 
                signals.append(f"{elem.tag}:{classes}:{text_len}")
            
            combined = "|".join(signals)
            return hashlib.md5(combined.encode()).hexdigest()
        except Exception:
            return "unknown_state"
