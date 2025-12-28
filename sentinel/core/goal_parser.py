import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class TargetSpec:
    """Specifications for identifying a target element."""
    text: Optional[str] = None
    css_class: Optional[str] = None
    id: Optional[str] = None
    role: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)

    def __repr__(self) -> str:
        parts = []
        if self.text: parts.append(f"text='{self.text}'")
        if self.css_class: parts.append(f"class='{self.css_class}'")
        if self.id: parts.append(f"id='{self.id}'")
        if self.attributes: parts.append(f"attrs={self.attributes}")
        return f"TargetSpec({', '.join(parts)})"

@dataclass
class GoalStep:
    """A single structured step in a multi-step goal."""
    action: str  # click, type, verify, navigate, scroll
    target: TargetSpec
    value: Optional[str] = None  # Text to type or verify
    context_hint: Optional[str] = None  # Context keyword (e.g. 'pytest-mockllm')
    description: str = ""  # Natural language description of this step
    is_completed: bool = False

    def __repr__(self) -> str:
        return f"GoalStep(action='{self.action}', target={self.target}, value={self.value}, context='{self.context_hint}')"

@dataclass
class ParsedGoal:
    """Structured representation of the entire user goal."""
    raw_goal: str
    steps: List[GoalStep] = field(default_factory=list)
    current_step_index: int = 0

    @property
    def current_step(self) -> Optional[GoalStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def is_completed(self) -> bool:
        return all(step.is_completed for step in self.steps)

    def next_step(self) -> None:
        if self.current_step:
            self.current_step.is_completed = True
        self.current_step_index += 1

class RegexGoalParser:
    """Parses natural language goals into a sequence of GoalSteps."""

    def parse(self, goal: str) -> ParsedGoal:
        # ... (splitting logic remains same)
        step_texts = re.split(r'\s+(?:and\s+)?then\s+', goal, flags=re.IGNORECASE)
        if len(step_texts) == 1:
            step_texts = re.split(r'\s+and\s+(?=click|type|enter|input|search|find|verify|navigate|go|open)', goal, flags=re.IGNORECASE)

        parsed_steps = []
        for raw_step in step_texts:
            step = self._parse_single_step(raw_step.strip())
            if step:
                parsed_steps.append(step)
        
        if not parsed_steps and goal.strip():
            parsed_steps.append(self._parse_single_step(f"achieve {goal}"))

        return ParsedGoal(raw_goal=goal, steps=parsed_steps)

    def _parse_single_step(self, text: str) -> Optional[GoalStep]:
        """Parse a single clause into a GoalStep with context extraction."""
        text_lower = text.lower()
        context_hint = None
        
        # Extract context keyword (X for Y, X in Y, X of Y)
        # Multi-word context support (greedy match until end or reserved keywords)
        context_match = re.search(r"(.*?)\s+(?:for|in|associated with|near|of)\s+['\"]?([^'\"].*?)['\"]?$", text, re.IGNORECASE)
        if context_match:
            base_text = context_match.group(1).strip()
            context_hint = context_match.group(2).strip()
            # We'll use the base_text for further parsing, but keep full text in description
        else:
            base_text = text

        # 1. VERIFY patterns
        # Handle 'verify that X says Y', 'verify heading X counts', etc.
        # Prioritize quoted text as the value
        quoted_value = re.search(r"['\"]([^'\"]+)['\"]", base_text)
        
        verify_match = re.search(r"verify\s+(?:that\s+)?(?:the\s+)?(.*)$", base_text, re.IGNORECASE)
        if verify_match:
            val = verify_match.group(1).strip()
            # If there's quoted text, it's likely the value
            if quoted_value:
                val = quoted_value.group(1).strip()
            else:
                # Strip trailing "exists", "appears", etc.
                val = re.sub(r"\s+(?:exists|appears|is visible|is present|says|matches)$", "", val, flags=re.IGNORECASE).strip()
                # Strip leading keywords
                val = re.sub(r"^(?:text|title|heading|header|page|the)\s+", "", val, flags=re.IGNORECASE).strip()
                
            return GoalStep(
                action="verify",
                target=TargetSpec(),
                value=val,
                context_hint=context_hint,
                description=text
            )

        # 2. TYPE/SEARCH patterns
        # Handle 'type X in Y', 'search for X', 'enter X into Y'
        # Check for quoted first
        type_match = re.search(r"(?:type|enter|input|search|find|lookup)\s+(?:for\s+)?['\"]([^'\"]+)['\"]\s+(?:in|into|on|the|at)?\s*(.*?)$", base_text, re.IGNORECASE)
        if type_match:
            return GoalStep(
                action="type",
                target=self._parse_target(type_match.group(2) or "search"),
                value=type_match.group(1),
                context_hint=context_hint,
                description=text
            )
            
        # Handle UNQUOTED type/search (last word or after 'for')
        # e.g. "search for Artificial Intelligence" -> val=AI, target=search
        unquoted_search = re.search(r"(?:search|find|lookup|type|enter)\s+(?:for\s+)?(.*?)(?:\s+(?:in|into|on|the|at)\s+(.*))?$", base_text, re.IGNORECASE)
        if unquoted_search:
            val = unquoted_search.group(1).strip()
            target_raw = unquoted_search.group(2) or "search"
            # If value is 'for', or generic, skip
            if val and val.lower() not in ["the", "a", "for"]:
                return GoalStep(
                    action="type",
                    target=self._parse_target(target_raw),
                    value=val,
                    context_hint=context_hint,
                    description=text
                )

        # 3. CLICK patterns
        click_match = re.search(r"click\s+(?:the\s+)?(.*?)$", base_text, re.IGNORECASE)
        if click_match:
            return GoalStep(
                action="click",
                target=self._parse_target(click_match.group(1)),
                context_hint=context_hint,
                description=text
            )

        # 4. NAVIGATE patterns
        nav_match = re.search(r"(?:navigate|go|open)\s+(?:to\s+)?(https?://\S+)", base_text, re.IGNORECASE)
        if nav_match:
            return GoalStep(
                action="navigate",
                target=TargetSpec(),
                value=nav_match.group(1),
                context_hint=context_hint,
                description=text
            )

        # 5. Generic Fallback
        words = base_text.split()
        if words:
            target = self._parse_target(base_text)
            return GoalStep(action="click", target=target, context_hint=context_hint, description=text)

        return None

    def _parse_target(self, text: str) -> TargetSpec:
        """Extract TargetSpec from text (e.g. 'button with class X')."""
        spec = TargetSpec()
        
        # Extract class
        class_match = re.search(r"class\s*[:\s]\s*([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        if class_match:
            spec.css_class = class_match.group(1)
            text = text.replace(class_match.group(0), "")

        # Extract ID
        id_match = re.search(r"id\s*[:\s]\s*([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        if id_match:
            spec.id = id_match.group(1)
            text = text.replace(id_match.group(0), "")

        # Extract Role
        role_match = re.search(r"role\s*[:\s]\s*([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        if role_match:
            spec.role = role_match.group(1)
            text = text.replace(role_match.group(0), "")

        # Remaining text is likely the visible text label
        # Clean up common fluff (World-Class semantic stripping)
        clean_text = re.sub(r"\s+(?:with|the)\s+", " ", text, flags=re.IGNORECASE).strip()
        # Strip trailing descriptors like 'button', 'link', 'dropdown'
        clean_text = re.sub(r"\s+(?:button|link|icon|dropdown|menu|toggle|field|input)$", "", clean_text, flags=re.IGNORECASE).strip()
        
        if clean_text:
            spec.text = clean_text.strip("'\" ")
            
        return spec
