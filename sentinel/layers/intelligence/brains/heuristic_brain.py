from typing import List, Dict, Any, Optional, TYPE_CHECKING
import re
from .base import BrainInterface, Decision

if TYPE_CHECKING:
    from sentinel.core.goal_parser import GoalStep, ParsedGoal


class HeuristicBrain(BrainInterface):
    """
    Heuristic-based brain using keyword matching and scoring.
    Fast, robust, and works without any external models.
    """
    
    def decide(
        self,
        goal: "GoalStep",
        world_state: List[Any],
        history: List[Decision],
        full_goal: Optional["ParsedGoal"] = None
    ) -> Decision:
        """
        Make a decision using structured goal information.
        """
        # Score each element based on relevance to goal step
        scored_elements = []
        for elem in world_state:
            if not elem.is_visible or not elem.is_interactive:
                continue
            
            score = self._score_element(elem, goal, history)
            if score > 0:
                scored_elements.append((elem, score))
        
        # Sort by score (highest first)
        scored_elements.sort(key=lambda x: x[1], reverse=True)
        
        if not scored_elements:
            # For verify steps, if nothing found, it's just not done yet
            if goal.action == "verify":
                return Decision(
                    action="wait",
                    target="body",
                    reasoning=f"Waiting for verification target: {goal.value}",
                    confidence=0.5,
                    metadata={}
                )

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
        
        # Determine action type (use step action as primary hint)
        action = goal.action
        if action == "verify":
            # If we are in a 'verify' step, we don't necessarily click.
            # However, the brain might Decide to click something to GET to the verify state?
            # For now, let's assume if verify matches, the orchestrator handles completion.
            return Decision(
                action="wait",
                target="body",
                reasoning=f"Verification target '{goal.value}' potentially found",
                confidence=0.9,
                metadata={}
            )

        # Build metadata for type actions
        metadata = {}
        if action == "type":
            metadata["text"] = goal.value
        
        return Decision(
            action=action,
            target=best_elem.selector or best_elem.shadow_path or "",
            reasoning=f"Matched '{best_elem.text[:30]}' with goal target {goal.target}",
            confidence=best_score,
            metadata=metadata,
        )
    
    def _score_element(
        self,
        elem: Any,
        step: "GoalStep",
        history: List[Decision],
    ) -> float:
        """Score an element based on relevance to structured GoalStep."""
        score = 0.0
        tag = elem.tag.lower() if elem.tag else ""
        target = step.target
        
        # 1. Action compatibility boost
        if step.action == "click":
            if tag in ["button", "a"]:
                score += 0.2
            if elem.attributes.get("type") in ["submit", "button"]:
                score += 0.2
        elif step.action == "type":
            if tag in ["input", "textarea"]:
                score += 0.3
        
        # 2. Text matching (highest priority)
        if target.text:
            elem_text = (elem.text or "").lower()
            target_text = target.text.lower()
            if target_text in elem_text:
                score += 0.5
            
            # Check attributes for text match as well
            for attr in ["aria-label", "title", "placeholder", "name"]:
                attr_val = elem.attributes.get(attr, "").lower()
                if attr_val and target_text in attr_val:
                    score += 0.4

        # 3. Explicit ID match
        if target.id and elem.id == target.id:
            score += 0.9

        # 4. Explicit Class match
        if target.css_class:
            elem_classes = elem.attributes.get("class", "")
            if target.css_class in elem_classes:
                score += 0.8

        # 5. Role match
        if target.role:
            elem_role = elem.attributes.get("role", "").lower()
            if target.role.lower() == elem_role:
                score += 0.4

        # Enhanced loop prevention:
        # Penalize elements that have been targeted recently.
        # The penalty is higher if the same element was targeted multiple times.
        if history:
            recent_targets = [d.target for d in history[-10:] if d.target]
            target_count = recent_targets.count(elem.selector)
            if target_count > 0:
                # Significant penalty to force trying something else
                score -= (0.4 + (target_count * 0.1))
        
        return max(0, min(1.0, score))
