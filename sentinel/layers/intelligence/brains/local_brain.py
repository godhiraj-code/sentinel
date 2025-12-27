import os
import json
import logging
from typing import List, Any, Dict, Optional
from .base import BrainInterface, Decision

logger = logging.getLogger(__name__)

class LocalBrain(BrainInterface):
    """
    Local SLM-based brain using llama-cpp-python.
    
    Supports GGUF models (e.g., Phi-3, Mistral, Llama-3).
    """
    def __init__(self, model_path: str = None):
        """
        Initialize the local brain.
        
        Args:
            model_path: Path to the GGUF model file.
        """
        self.model_path = model_path
        self.llm = None
        self._init_model()
        
    def _init_model(self):
        """Initialize the llama-cpp model."""
        if not self.model_path:
            logger.warning("[LocalBrain] No model path provided.")
            return

        if not os.path.exists(self.model_path):
            logger.error(f"[LocalBrain] Model file not found: {self.model_path}")
            return

        try:
            from llama_cpp import Llama
            logger.info(f"[LocalBrain] Loading model from {self.model_path}...")
            # Initialize with default settings optimized for speed/SLM
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,  # Context window
                n_threads=os.cpu_count() or 4,
                verbose=False
            )
            logger.info("[LocalBrain] Model loaded successfully.")
        except ImportError:
            logger.error("[LocalBrain] llama-cpp-python not installed. Run: pip install llama-cpp-python")
        except Exception as e:
            logger.error(f"[LocalBrain] Error loading model: {e}")

    def decide(
        self, 
        goal: str, 
        world_state: List[Any], 
        history: List[Decision]
    ) -> Decision:
        """
        Make a decision using the local SLM.
        """
        if not self.llm:
            return Decision(
                action="wait", 
                target="body", 
                reasoning="LocalBrain model not loaded", 
                confidence=0.0, 
                metadata={}
            )

        # 1. Serialize World State
        dom_representation = self._serialize_world_state(world_state)
        
        # 2. Serialize History
        history_text = "\n".join([f"- {d.action} on {d.target} ({d.reasoning})" for d in history[-5:]])
        
        # 3. Build Prompt (Optimized for SLMs like Phi-3)
        system_prompt = self._get_system_prompt()
        prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\nGOAL: {goal}\n\nCURRENT STATE:\n{dom_representation}\n\nHISTORY:\n{history_text or 'None'}\n\nWhat is the next best action? Respond in JSON.<|end|>\n<|assistant|>\n"
        
        # 4. Query LLM
        try:
            response = self.llm(
                prompt,
                max_tokens=256,
                stop=["<|end|>", "}"], # Stop at end tag or close brace to help JSON parsing
                echo=False
            )
            
            content = response["choices"][0]["text"].strip()
            if not content.endswith("}"):
                content += "}"
            
            # Extract JSON
            if "{" in content:
                content = content[content.find("{"):]
            
            response_json = json.loads(content)
            
            return Decision(
                action=response_json.get("action", "wait"),
                target=response_json.get("target", "body"),
                reasoning=response_json.get("reasoning", "Local SLM decision"),
                confidence=response_json.get("confidence", 0.5),
                metadata=response_json.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"[LocalBrain] Inference error: {e}")
            return Decision(
                action="wait", 
                target="body", 
                reasoning=f"Error in LocalBrain: {str(e)}", 
                confidence=0.0, 
                metadata={}
            )

    def _serialize_world_state(self, world_state: List[Any]) -> str:
        """Convert element list to a simplified text format."""
        lines = []
        for i, elem in enumerate(world_state[:30]): # SLMs have smaller context
            if not elem.is_visible: 
                continue
                
            ref = elem.selector
            attrs = []
            if elem.tag == "input":
                attrs.append(f"type='{elem.attributes.get('type','text')}'")
            if elem.text:
                attrs.append(f"text='{elem.text[:30].strip()}'")
                
            attr_str = " ".join(attrs)
            lines.append(f"[{i}] {elem.tag} ({ref}) {attr_str}")
            
        return "\n".join(lines)

    def _get_system_prompt(self) -> str:
        return """You are a web automation agent. Goal: Achievement.
Output JSON:
{
  "action": "click" | "type" | "scroll" | "wait" | "goal_achieved",
  "target": "selector",
  "reasoning": "why",
  "confidence": 0.0-1.0,
  "metadata": {"text": "to type"}
}"""
