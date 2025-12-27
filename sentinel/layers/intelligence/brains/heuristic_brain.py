from typing import List, Dict, Any, Optional
import re
from .base import BrainInterface, Decision


class HeuristicBrain(BrainInterface):
    """
    Heuristic-based brain using keyword matching and scoring.
    Fast, robust, and works without any external models.
    """
    
    def decide(
        self,
        goal: str,
        world_state: List[Any],
        history: List[Decision]
    ) -> Decision:
        """
        Make a decision using keyword matching heuristics.
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
                metadata={}
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
        target_text = goal
        for action_word in ["click", "type", "enter", "input", "submit", "select", "add", "remove", "delete", "the", "a", "an", "to", "on", "in"]:
            target_text = target_text.replace(action_word, " ")
        
        # Split into words and filter
        words = [w.strip() for w in target_text.split() if len(w.strip()) > 2]
        keywords["target"] = words
        
        # Value extraction (for type actions)
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", goal)
        keywords["value"] = quoted
        
        return keywords
    
    def _score_element(
        self,
        elem: Any,
        keywords: Dict[str, List[str]],
        history: List[Decision],
    ) -> float:
        """Score an element based on relevance to goal keywords."""
        score = 0.0
        tag = elem.tag.lower() if elem.tag else ""
        
        # Special handling for input fields when goal mentions adding/typing
        has_add_action = any(a in keywords["action"] for a in ["add", "type", "enter"])
        has_value_to_type = len(keywords["value"]) > 0
        
        if has_add_action and has_value_to_type:
            if tag in ["input", "textarea"]:
                elem_type = elem.attributes.get("type", "text").lower()
                if elem_type in ["text", "search", "email", "password", ""]:
                    score += 0.7
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
            elif any(keyword in word for word in elem_text.split()):
                score += 0.2
        
        # Attribute matching
        important_attrs = ["id", "class", "name", "placeholder", "aria-label", "title"]
        for attr_key in important_attrs:
            attr_val = elem.attributes.get(attr_key, "")
            if not attr_val:
                continue
            attr_val_lower = attr_val.lower()
            for keyword in keywords["target"]:
                if keyword in attr_val_lower:
                    score += 0.3
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
        for past_decision in history[-5:]:
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
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", goal)
        if quoted:
            return quoted[0]
        
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
