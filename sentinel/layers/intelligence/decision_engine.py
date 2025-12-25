"""
Decision Engine - Goal-Based Element Selection.

Provides intelligent decision making for autonomous exploration.
Can use a local SLM, mock LLM (for testing), or simple heuristics.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re


@dataclass
class Decision:
    """
    Represents an agent decision.
    
    This encapsulates what action to take, on what target,
    and why the decision was made.
    """
    action: str  # 'click', 'type', 'scroll', 'wait', 'navigate', 'goal_achieved'
    target: str  # Element selector or shadow path
    reasoning: str  # Why this decision was made
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action": self.action,
            "target": self.target,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        """Create from dictionary."""
        return cls(
            action=data.get("action", ""),
            target=data.get("target", ""),
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", 0.0),
            metadata=data.get("metadata", {}),
        )


class DecisionEngine:
    """
    Intelligent decision making for autonomous exploration.
    
    The decision engine analyzes the current world state (list of elements)
    and the goal, then decides which element to interact with next.
    
    Modes:
    - mock_mode: Uses heuristics for testing (no LLM calls)
    - Full mode: Uses LLM/SLM for intelligent decisions (future)
    
    Example:
        >>> engine = DecisionEngine(mock_mode=True)
        >>> decision = engine.decide(
        ...     goal="Click the login button",
        ...     world_state=elements,
        ...     history=[]
        ... )
        >>> print(f"Action: {decision.action} on {decision.target}")
    """
    
    def __init__(
        self,
        mock_mode: bool = True,
        model_path: Optional[str] = None,
    ):
        """
        Initialize the decision engine.
        
        Args:
            mock_mode: Use heuristic-based decisions (no LLM)
            model_path: Path to local SLM model (for future use)
        """
        self.mock_mode = mock_mode
        self.model_path = model_path
        self._llm = None
        
        if not mock_mode and model_path:
            self._init_llm(model_path)
    
    def _init_llm(self, model_path: str) -> None:
        """Initialize local LLM (future implementation)."""
        # Placeholder for local SLM integration
        # Would use llama-cpp-python or similar
        pass
    
    def decide(
        self,
        goal: str,
        world_state: List[Any],  # List[ElementNode]
        history: List[Decision],
    ) -> Decision:
        """
        Decide the next action based on goal and current state.
        
        Args:
            goal: Natural language goal (e.g., "Add item to cart")
            world_state: List of ElementNodes from DOMMapper
            history: List of previous decisions
        
        Returns:
            Decision with action, target, and reasoning
        """
        if self.mock_mode:
            return self._heuristic_decision(goal, world_state, history)
        else:
            return self._llm_decision(goal, world_state, history)
    
    def _heuristic_decision(
        self,
        goal: str,
        world_state: List[Any],
        history: List[Decision],
    ) -> Decision:
        """
        Make a decision using keyword matching heuristics.
        
        This is a simple but effective approach for common scenarios.
        """
        goal_lower = goal.lower()
        
        # Extract action keywords from goal
        action_keywords = self._extract_goal_keywords(goal_lower)
        
        # Score each element based on relevance to goal
        scored_elements = []
        for elem in world_state:
            if not elem.is_visible or not elem.is_interactive:
                continue
            
            score = self._score_element(elem, action_keywords, history)
            if score > 0:
                scored_elements.append((elem, score))
        
        # Sort by score (highest first)
        scored_elements.sort(key=lambda x: x[1], reverse=True)
        
        if not scored_elements:
            # No matching elements - try scrolling or waiting
            return Decision(
                action="scroll",
                target="body",
                reasoning="No matching elements found, scrolling to discover more",
                confidence=0.3,
            )
        
        # Pick the best match
        best_elem, best_score = scored_elements[0]
        
        # Determine action type
        action = self._determine_action(best_elem, goal_lower)
        
        # Check if this might complete the goal
        if best_score > 0.8 and action == "click":
            # High confidence match
            confidence = min(0.9, best_score)
        else:
            confidence = best_score * 0.7
        
        # Build metadata for type actions
        metadata = {}
        if action == "type":
            # Extract text to type from goal
            metadata["text"] = self._extract_type_text(goal_lower)
        
        return Decision(
            action=action,
            target=best_elem.selector or best_elem.shadow_path or "",
            reasoning=f"Matched '{best_elem.text[:30]}' with goal keywords",
            confidence=confidence,
            metadata=metadata,
        )
    
    def _extract_goal_keywords(self, goal: str) -> Dict[str, List[str]]:
        """Extract relevant keywords from the goal."""
        keywords = {
            "action": [],
            "target": [],
            "value": [],
        }
        
        # Action keywords
        if "click" in goal:
            keywords["action"].append("click")
        if "type" in goal or "enter" in goal or "input" in goal:
            keywords["action"].append("type")
        if "submit" in goal:
            keywords["action"].append("submit")
            keywords["action"].append("click")
        if "select" in goal:
            keywords["action"].append("select")
        if "add" in goal:
            keywords["action"].append("add")
        if "remove" in goal or "delete" in goal:
            keywords["action"].append("remove")
        
        # Target keywords - extract nouns/phrases
        # Remove common action words
        target_text = goal
        for action_word in ["click", "type", "enter", "input", "submit", "select", "add", "remove", "delete", "the", "a", "an", "to", "on", "in"]:
            target_text = target_text.replace(action_word, " ")
        
        # Split into words and filter
        words = [w.strip() for w in target_text.split() if len(w.strip()) > 2]
        keywords["target"] = words
        
        # Value extraction (for type actions)
        # Look for quoted strings
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", goal)
        keywords["value"] = quoted
        
        return keywords
    
    def _score_element(
        self,
        elem: Any,  # ElementNode
        keywords: Dict[str, List[str]],
        history: List[Decision],
    ) -> float:
        """Score an element based on relevance to goal keywords."""
        score = 0.0
        tag = elem.tag.lower() if elem.tag else ""
        
        # Special handling for input fields when goal mentions adding/typing
        has_add_action = any(a in keywords["action"] for a in ["add", "type", "enter"])
        has_value_to_type = len(keywords["value"]) > 0
        
        # If goal says "add X" or "type X" and we have a quoted value, prioritize inputs
        if has_add_action and has_value_to_type:
            if tag in ["input", "textarea"]:
                # Strong boost for text input fields
                elem_type = elem.attributes.get("type", "text").lower()
                if elem_type in ["text", "search", "email", "password", ""]:
                    score += 0.7
                # Check for placeholder hints
                placeholder = elem.attributes.get("placeholder", "").lower()
                if placeholder:
                    for val in keywords["value"]:
                        if any(word in placeholder for word in ["todo", "add", "new", "item", "task"]):
                            score += 0.4
        
        # Text matching
        elem_text = (elem.text or "").lower()
        for keyword in keywords["target"]:
            if keyword in elem_text:
                score += 0.4
            # Partial match
            elif any(keyword in word for word in elem_text.split()):
                score += 0.2
        
        # Attribute matching (id, class, name, placeholder, aria-label)
        important_attrs = ["id", "class", "name", "placeholder", "aria-label", "title"]
        for attr_key in important_attrs:
            attr_val = elem.attributes.get(attr_key, "")
            if not attr_val:
                continue
            attr_val_lower = attr_val.lower()
            for keyword in keywords["target"]:
                if keyword in attr_val_lower:
                    score += 0.3
            # Check if value to type is mentioned in placeholder
            for val in keywords["value"]:
                if val.lower() in attr_val_lower:
                    score += 0.2
        
        # Tag-based scoring
        if "click" in keywords["action"] or "submit" in keywords["action"]:
            if tag in ["button", "a"]:
                score += 0.2
            if elem.attributes.get("type") in ["submit", "button"]:
                score += 0.2
        
        if "type" in keywords["action"] or "add" in keywords["action"]:
            if tag in ["input", "textarea"]:
                score += 0.3
        
        # Penalize already-clicked elements
        for past_decision in history[-5:]:  # Check last 5 decisions
            if past_decision.target == elem.selector:
                score -= 0.5
        
        return max(0, min(1.0, score))
    
    def _determine_action(self, elem: Any, goal: str) -> str:
        """Determine what action to take on an element."""
        tag = elem.tag.lower()
        elem_type = elem.attributes.get("type", "").lower()
        
        # Input fields -> type
        if tag in ["input", "textarea"]:
            if elem_type not in ["submit", "button", "checkbox", "radio"]:
                return "type"
        
        # Default to click for interactive elements
        return "click"
    
    def _extract_type_text(self, goal: str) -> str:
        """Extract text to type from the goal."""
        # Look for quoted strings
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", goal)
        if quoted:
            return quoted[0]
        
        # Look for common patterns
        patterns = [
            r"type\s+(.+?)(?:\s+in|\s+into|\s*$)",
            r"enter\s+(.+?)(?:\s+in|\s+into|\s*$)",
            r"input\s+(.+?)(?:\s+in|\s+into|\s*$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, goal, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _llm_decision(
        self,
        goal: str,
        world_state: List[Any],
        history: List[Decision],
    ) -> Decision:
        """
        Make a decision using LLM/SLM.
        
        This is a placeholder for future LLM integration.
        Falls back to heuristics if LLM is not available.
        """
        # For now, delegate to heuristics
        # Future: Build prompt and query LLM
        return self._heuristic_decision(goal, world_state, history)
    
    def _build_llm_prompt(
        self,
        goal: str,
        world_state: List[Any],
        history: List[Decision],
    ) -> str:
        """Build a prompt for the LLM (future use)."""
        elements_str = "\n".join(
            f"- [{i}] {elem}" for i, elem in enumerate(world_state[:20])
        )
        
        history_str = "\n".join(
            f"- {d.action} on {d.target}" for d in history[-5:]
        )
        
        prompt = f"""You are an autonomous web testing agent.

Goal: {goal}

Available elements:
{elements_str}

Previous actions:
{history_str if history else "None"}

Decide the next action. Respond with JSON:
{{"action": "click|type|scroll|wait|goal_achieved", "target": "element selector or index", "reasoning": "why this action"}}
"""
        return prompt
