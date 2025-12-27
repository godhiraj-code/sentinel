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
            
            # Direct match or partial match
            if target_text in elem_text or elem_text in target_text:
                score += 0.5
            
            # Check attributes for text match as well
            for attr in ["aria-label", "title", "placeholder", "name"]:
                attr_val = elem.attributes.get(attr, "").lower()
                if attr_val and (target_text in attr_val or attr_val in target_text):
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

        # 6. Semantic Context match (NLP-style overlap)
        # 6a. Explicit Context Hint match (High Precision)
        if step.context_hint and elem.context_text:
            context_hint_lower = step.context_hint.lower()
            if context_hint_lower in elem.context_text.lower():
                score += 0.8  # Strong discriminator for grid item disambiguation
        
        # 6b. Generic Description overlap (NLP-style)
        if step.description and elem.context_text:
             context_score = self._score_context_relevance(step.description, elem.context_text)
             # Boost context score weight - it should be the primary tie-breaker
             score += (context_score * 1.5)
             
        # Enhanced loop prevention:
        if history:
            recent_targets = [d.target for d in history[-10:] if d.target]
            target_count = recent_targets.count(elem.selector)
            if target_count > 0:
                # Scalable penalty
                score -= (0.5 * target_count)
        
        # RETURN UNCLAMPED: Important for sorting tie-breakers
        return max(0, score)
    
    def _score_context_relevance(self, goal_description: str, element_context: str) -> float:
        """
        Advanced semantic relevance scoring.
        Uses weighted token overlap and handling for common naming conventions.
        """
        if not element_context or not goal_description:
            return 0.0
            
        def tokenize(text: str) -> List[str]:
            # Normalize and split while preserving technical symbols
            text = text.lower()
            # Catch alphanumeric sequences including technical chars like - and .
            raw_tokens = re.findall(r'[a-z0-9\-\.]+', text)
            
            return raw_tokens
            
            stop_words = {
                "click", "type", "verify", "navigate", "wait", "check", "select", "press",
                "the", "a", "an", "in", "on", "at", "for", "with", "to", "of", "by", "from",
                "button", "link", "input", "field", "text", "page", "site", "app", "recent", "insights",
                "is", "are", "be", "was", "were", "and", "or", "but"
            }
            
            combined = set(raw_tokens) | set(compounds)
            return [t for t in combined if len(t) > 2 and t not in stop_words]

        goal_tokens = tokenize(goal_description)
        context_tokens = tokenize(element_context)
        
        if not goal_tokens:
            return 0.0
            
        common_matches = [t for t in goal_tokens if t in context_tokens]
        
        if not common_matches:
            return 0.0
            
        # Calculate score based on keyword "significance" 
        # (Longer words and words with digits/symbols are usually more significant identifiers)
        score = 0.0
        for token in common_matches:
            # Base significance from length
            weight = 0.1
            if len(token) > 8:
                weight += 0.1
            if len(token) > 12:
                weight += 0.1
            
            # Boost for mixed alpha-numeric (likely product IDs, versions, or specific slugs)
            if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
                weight += 0.1
                
            # Boost for compound segments
            if "-" in token or "_" in token:
                weight += 0.1
                
            score += weight
            
        # Context boost capped to avoid overshadowing direct text matches entirely
        # but high enough to be the definitive tie-breaker for identical text labels.
        return min(0.7, 0.2 + score)
