import os
import json
import logging
from typing import List, Any, Dict, Optional
from .base import BrainInterface, Decision

logger = logging.getLogger(__name__)

class CloudBrain(BrainInterface):
    """
    Cloud-based brain using OpenAI or Anthropic APIs.
    
    Requires OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables.
    """
    
    def __init__(self, provider: str = "auto", model: str = None):
        self.provider = provider
        self.model = model
        self.client = None
        self._init_client()
        
    def _init_client(self):
        """Initialize the API client."""
        openai_key = os.environ.get("OPENAI_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        
        # Auto-select provider if not specified
        if self.provider == "auto":
            if openai_key:
                self.provider = "openai"
            elif anthropic_key:
                self.provider = "anthropic"
            else:
                raise ValueError("No API keys found for CloudBrain. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.")
        
        if self.provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=openai_key)
                self.model = self.model or "gpt-4-turbo-preview"
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
                
        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=anthropic_key)
                self.model = self.model or "claude-3-opus-20240229"
            except ImportError:
                raise ImportError("Please install anthropic: pip install anthropic")
                
        logger.info(f"[CloudBrain] Initialized using {self.provider} ({self.model})")

    def decide(
        self,
        goal: Any,
        world_state: List[Any],
        history: List[Decision],
        full_goal: Optional[Any] = None,
        blacklist: Optional[List[str]] = None
    ) -> Decision:
        """
        Make a decision using an LLM.
        """
        # 1. Serialize World State
        dom_representation = self._serialize_world_state(world_state)
        
        # 2. Serialize History
        history_text = "\n".join([f"- {d.action} on {d.target} ({d.reasoning})" for d in history[-5:]])
        
        # 3. Build Prompt
        system_prompt = self._get_system_prompt()
        user_prompt = f"""
GOAL: {goal}

CURRENT STATE (Interactive Elements):
{dom_representation}

HISTORY (Last 5 actions):
{history_text or "None"}

What is the next best action? Respond in JSON.
"""
        
        # 4. Query LLM
        try:
            response_json = self._query_llm(system_prompt, user_prompt)
            
            return Decision(
                action=response_json.get("action", "wait"),
                target=response_json.get("target", "body"),
                reasoning=response_json.get("reasoning", "LLM decision"),
                confidence=response_json.get("confidence", 0.5),
                metadata=response_json.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"[CloudBrain] Error: {e}")
            # Fallback
            return Decision(
                action="wait", 
                target="body", 
                reasoning=f"Error in CloudBrain: {str(e)}", 
                confidence=0.0, 
                metadata={}
            )

    def _serialize_world_state(self, world_state: List[Any]) -> str:
        """Convert element list to a simplified text format for the LLM."""
        lines = []
        for i, elem in enumerate(world_state[:50]): # Limit to top 50 to fit context
            if not elem.is_visible: 
                continue
                
            # Create a unique ID/Selector reference
            ref = elem.selector
            if not ref and elem.attributes.get("id"):
                ref = f"#{elem.attributes['id']}"
            
            # Simplified attributes
            attrs = []
            if elem.tag == "input":
                attrs.append(f"type='{elem.attributes.get('type','text')}'")
                attrs.append(f"placeholder='{elem.attributes.get('placeholder','')}'")
            if elem.text:
                attrs.append(f"text='{elem.text[:50].strip()}'")
            if elem.attributes.get("aria-label"):
                attrs.append(f"aria='{elem.attributes.get('aria-label')}'")
                
            attr_str = " ".join(attrs)
            lines.append(f"[{i}] {elem.tag} ({ref}) {attr_str}")
            
        return "\n".join(lines)

    def _get_system_prompt(self) -> str:
        return """You are an autonomous web automation agent.
Your job is to navigate a web page to achieve the user's GOAL.

You will receive:
1. The GOAL.
2. A list of interactive elements on the screen.
3. Your history of previous actions.

Output a valid JSON object with:
- "action": One of ["click", "type", "scroll", "wait", "navigate", "goal_achieved"]
- "target": The CSS selector or element identifier from the list.
- "reasoning": Brief explanation of why you chose this action.
- "confidence": Float 0.0-1.0.
- "metadata": Optional dict (e.g., {"text": "hello"} for type action).

GUIDELINES:
- If the goal is achieved, use action "goal_achieved".
- If you need to type, include "text" in metadata.
- If you can't find the element, try "scroll".
"""

    def _query_llm(self, system: str, user: str) -> Dict[str, Any]:
        """Send request to the configured provider."""
        
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
            
        elif self.provider == "anthropic":
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system,
                messages=[
                    {"role": "user", "content": user}
                ]
            )
            content = message.content[0].text
            # Extract JSON from response (Claude often wraps in markdown)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
                
            return json.loads(content)
            
        return {}
