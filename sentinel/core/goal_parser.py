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
    description: str = ""  # Natural language description of this step
    is_completed: bool = False

    def __repr__(self) -> str:
        return f"GoalStep(action='{self.action}', target={self.target}, value={self.value})"

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
        """Parse a goal string into structured steps."""
        # 1. Split exclusively by "then" or "and then" first (strongest separators)
        step_texts = re.split(r'\s+(?:and\s+)?then\s+', goal, flags=re.IGNORECASE)
        
        # 2. If only one chunk, try splitting by "and" if it seems to separate actions
        # Avoid splitting "input and label" or "id X and class Y"
        # We look for "and [VERB]"
        if len(step_texts) == 1:
            # Split only if "and" is followed by an action word
            step_texts = re.split(r'\s+and\s+(?=click|type|enter|input|verify|navigate|go|open)', goal, flags=re.IGNORECASE)

        parsed_steps = []
        for raw_step in step_texts:
            step = self._parse_single_step(raw_step.strip())
            if step:
                parsed_steps.append(step)
        
        # If no steps parsed but string isn't empty, create a generic search/click step
        if not parsed_steps and goal.strip():
            parsed_steps.append(self._parse_single_step(f"achieve {goal}"))

        return ParsedGoal(raw_goal=goal, steps=parsed_steps)

    def _parse_single_step(self, text: str) -> Optional[GoalStep]:
        """Parse a single clause into a GoalStep."""
        text_lower = text.lower()
        
        # 1. VERIFY patterns
        verify_match = re.search(r"verify\s+(?:that\s+)?(?:the\s+)?(?:text|title|heading)?\s*['\"]?([^'\"]+)['\"]?\s*(?:exists|appears|is visible)?", text, re.IGNORECASE)
        if verify_match:
            return GoalStep(
                action="verify",
                target=TargetSpec(),
                value=verify_match.group(1).strip(),
                description=text
            )

        # 2. TYPE patterns
        # "Type 'HelloWorld' in the input"
        type_match = re.search(r"(?:type|enter|input)\s+['\"]([^'\"]+)['\"]\s+(?:in|into|on|the)?\s*(.*?)$", text, re.IGNORECASE)
        if type_match:
            return GoalStep(
                action="type",
                target=self._parse_target(type_match.group(2)),
                value=type_match.group(1),
                description=text
            )

        # 3. CLICK patterns
        # "Click the 'Login' button"
        click_match = re.search(r"click\s+(?:the\s+)?(.*?)$", text, re.IGNORECASE)
        if click_match:
            return GoalStep(
                action="click",
                target=self._parse_target(click_match.group(1)),
                description=text
            )

        # 4. NAVIGATE patterns
        nav_match = re.search(r"(?:navigate|go|open)\s+(?:to\s+)?(https?://\S+)", text, re.IGNORECASE)
        if nav_match:
            return GoalStep(
                action="navigate",
                target=TargetSpec(),
                value=nav_match.group(1),
                description=text
            )

        # 5. Generic Fallback - Assume the whole text is a target to click (e.g. "Login")
        words = text.split()
        if words:
            # If the first word is a common automation verb not caught by specific regex
            # Or just any word like "Login", "Submit"
            target = self._parse_target(text)
            return GoalStep(action="click", target=target, description=text)

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
        # Clean up common fluff
        clean_text = re.sub(r"\s+(?:with|the)\s+", " ", text, flags=re.IGNORECASE).strip()
        if clean_text:
            spec.text = clean_text.strip("'\" ")
            
        return spec
