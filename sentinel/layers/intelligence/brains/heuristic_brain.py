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
        full_goal: Optional["ParsedGoal"] = None,
        blacklist: Optional[List[str]] = None
    ) -> Decision:
        """
        Make a decision using structured goal information.
        """
        # Score each element based on relevance to goal step
        scored_elements = []
        for elem in world_state:
            if not elem.is_visible or not elem.is_interactive:
                continue
            
            # Explicit Blacklist check (Adaptive Recovery)
            if blacklist and elem.selector in blacklist:
                continue
            
            score, details = self._score_element(elem, goal, history, world_state)
            if score > 0:
                scored_elements.append((elem, score, details))
        
        # Sort by score (highest first)
        scored_elements.sort(key=lambda x: x[1], reverse=True)
        
        # DEBUG: Log top 5 candidates with detailed scores
        if scored_elements:
            print(f"DEBUG: Goal Action: {goal.action}, Target: {goal.target.text}, Context: {goal.context_hint}")
            for i, (elem, score, details) in enumerate(scored_elements[:5]):
                detail_str = ", ".join([f"{k}: {v:.2f}" for k, v in details.items()])
                print(f"   Candidate {i+1} [Score {score:.2f}]: <{elem.tag}> '{elem.text[:30]}' | {detail_str} | Context: {elem.context_text[:50]}")

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
        best_elem, best_score, _ = scored_elements[0]
        
        # World-Class Requirement: Discovery over Guessing
        # If the score is mediocre and we have a context hint but NO context match,
        # we should SCROLL to find the real target rather than clicking a generic one.
        if goal.context_hint and best_score < 1.0:
             # Check if our best match actually contains the hint (handled by absolute penalty, 
             # but here we decide whether to click if it's borderline)
             pass
        
        # Determine action type (use step action as primary hint)
        action = goal.action
        if action == "verify":
            # Signal verification success by returning action="verify" with max confidence
            return Decision(
                action="verify",
                target="body",
                reasoning=f"Verification target '{goal.value}' found in world state",
                confidence=1.0,
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
        world_state: List[Any],
    ) -> tuple[float, dict]:
        """Score an element and return breakdown."""
        score = 0.0
        details = {}
        tag = elem.tag.lower() if elem.tag else ""
        target = step.target
        
        # 1. Action compatibility boost
        action_boost = 0.0
        if step.action == "click":
            if tag in ["button", "a"]:
                action_boost += 0.2
            if elem.attributes.get("type") in ["submit", "button"]:
                action_boost += 0.2
        elif step.action == "type":
            if tag in ["input", "textarea"]:
                action_boost += 0.3
        score += action_boost
        details["action"] = action_boost
        
        # 2. Text matching (highest priority)
        text_boost = 0.0
        if target.text:
            target_text = target.text.lower()
            elem_text = (elem.text or "").lower()
            
            text_score = self._score_context_relevance(target_text, elem_text, use_stop_words=False)
            if text_score > 0.2:
                text_boost += (text_score * 2.5)
                if target_text == elem_text:
                    text_boost += 0.5
            else:
                text_boost -= 1.0
            
            # Attribute-based text matching
            attr_boost = 0.0
            for attr in ["aria-label", "title", "placeholder", "name"]:
                attr_val = elem.attributes.get(attr, "").lower()
                if attr_val:
                    if target_text == attr_val:
                        attr_boost += 1.2
                    elif target_text in attr_val or attr_val in target_text:
                        attr_boost += 0.8
            text_boost += attr_boost
        score += text_boost
        details["text"] = text_boost

        # 3. ID/Class Match
        meta_boost = 0.0
        if target.id and elem.id == target.id:
            meta_boost += 0.9
        if target.css_class:
            elem_classes = elem.attributes.get("class", "")
            if target.css_class in elem_classes:
                meta_boost += 0.8
        score += meta_boost
        details["meta"] = meta_boost

        # 4. Context Hint match (World-Class Precision)
        context_boost = 0.0
        if step.context_hint:
             context_text = (elem.context_text or "").lower()
             if not context_text:
                 context_text = self._find_spatial_context(elem, world_state)
                 
             context_hint_lower = step.context_hint.lower()
             c_score = self._score_context_relevance(context_hint_lower, context_text)
             
             if c_score > 0.35:
                 context_boost += (c_score * 2.5)  # Significant boost for context match
             else:
                 # ABSOLUTE PENALTY: Prevent clicking buttons in the wrong section
                 context_boost -= 10.0
        else:
            # If no context hint, but element has context, maybe small boost for description?
            if step.description and elem.context_text:
                c_score = self._score_context_relevance(step.description, elem.context_text)
                context_boost += (c_score * 0.5)

        score += context_boost
        details["context"] = context_boost
             
        # 5. Generic Penalties
        penalty = 0.0
        if step.action == "click" and target.text:
            lower_label = (elem.text or "").lower() + (elem.attributes.get("aria-label") or "").lower()
            if "menu" in lower_label or "navigation" in lower_label or "toggle" in lower_label:
                if "menu" not in target.text.lower() and "navigation" not in target.text.lower():
                    penalty -= 1.5
        
        if history:
            recent_targets = [d.target for d in history[-10:] if d.target]
            target_count = recent_targets.count(elem.selector)
            if target_count > 0:
                penalty -= (1.0 * target_count)
        
        score += penalty
        details["penalty"] = penalty
        
        return max(0, score), details
    
    def _find_spatial_context(self, target_elem: Any, world_state: List[Any]) -> str:
        """Find nearby text context using spatial proximity."""
        target_rect = target_elem.bounding_box or {}
        if not target_rect:
            return ""
            
        tx, ty = target_rect.get('x', 0), target_rect.get('y', 0)
        
        candidates = []
        for elem in world_state:
            if elem == target_elem: continue
            rect = elem.bounding_box or {}
            if not rect: continue
            
            ex, ey = rect.get('x', 0), rect.get('y', 0)
            y_diff = ty - ey
            if 0 < y_diff < 400: 
                x_diff = abs(tx - ex)
                if x_diff < 300:
                    is_header = elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong']
                    dist = (y_diff * 0.5) if is_header else y_diff
                    candidates.append((elem.text, dist))
        
        if not candidates:
            return ""
        candidates.sort(key=lambda x: x[1])
        return " | ".join([c[0] for c in candidates[:2]])

    def _score_context_relevance(self, goal_description: str, element_context: str, use_stop_words: bool = True) -> float:
        """Semantic relevance scoring with token overlap."""
        if not element_context or not goal_description:
            return 0.0
            
        def tokenize(text: str) -> List[str]:
            text = text.lower()
            raw_tokens = re.findall(r'[a-z0-9\-\.]+', text)
            if not use_stop_words:
                return [t for t in raw_tokens if len(t) > 1]
            
            stop_words = {
                "click", "type", "verify", "navigate", "wait", "check", "select", "press",
                "the", "a", "an", "in", "on", "at", "for", "with", "to", "of", "by", "from",
                "button", "link", "input", "field", "text", "page", "site", "app",
                "is", "are", "be", "was", "were", "and", "or", "but"
            }
            return [t for t in raw_tokens if len(t) > 2 and t not in stop_words]

        goal_tokens = tokenize(goal_description)
        goal_sub_tokens = set(goal_tokens)
        for t in goal_tokens:
            if '-' in t or '_' in t or '.' in t:
                goal_sub_tokens.update(re.split(r'[\-\_\.]', t))
        
        context_tokens = tokenize(element_context)
        context_sub_tokens = set(context_tokens)
        for t in context_tokens:
            if '-' in t or '_' in t or '.' in t:
                context_sub_tokens.update(re.split(r'[\-\_\.]', t))
        
        common_matches = [t for t in goal_sub_tokens if t in context_sub_tokens and len(t) > 2]
        if not common_matches:
            return 0.0
            
        score = 0.0
        for token in common_matches:
            weight = 0.3
            if len(token) > 5: weight += 0.1
            if len(token) > 8: weight += 0.2
            if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
                weight += 0.3
            if "-" in token or "_" in token or "." in token:
                weight += 0.2
            score += weight
            
        return min(0.7, score)
