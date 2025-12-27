"""
Visual Agent - Vision-Language Model Integration.

Uses Moondream2 (or other VLMs) to analyze screenshots and provide
visual understanding of UI state when DOM analysis is insufficient.
"""

import logging
import os
import base64
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VisualElement:
    """Represents an element found via visual analysis."""
    description: str
    x: int
    y: int
    width: int
    height: int
    confidence: float


class VisualAgent:
    """
    Bridge to Vision-Language Models (VLM) for UI analysis.
    
    This class enables Sentinel to "see" the page through screenshots,
    identifying elements and verifying actions when DOM analysis fails.
    
    Supported backends:
    - moondream: Local Moondream2 model via transformers
    - openai: OpenAI GPT-4o Vision API
    - mock: Returns placeholder responses (for testing)
    
    Example:
        >>> agent = VisualAgent(backend="moondream")
        >>> description = agent.describe_state("screenshot.png")
        >>> element = agent.find_element("screenshot.png", "the login button")
    """
    
    def __init__(self, backend: str = "auto"):
        """
        Initialize the VisualAgent.
        
        Args:
            backend: VLM backend to use ('moondream', 'openai', 'mock', 'auto')
        """
        self.backend = backend.lower()
        self._model = None
        self._processor = None
        self._device = None
        
        if self.backend == "auto":
            self.backend = self._detect_best_backend()
            
        logger.info(f"[VisualAgent] Initialized with backend: {self.backend}")
    
    def _detect_best_backend(self) -> str:
        """Auto-detect the best available backend."""
        # Check for OpenAI API key
        if os.environ.get("OPENAI_API_KEY"):
            return "openai"
        
        # Check for torch/transformers
        try:
            import torch
            import transformers
            return "moondream"
        except ImportError:
            pass
        
        # Fall back to mock
        return "mock"
    
    def _ensure_model_loaded(self) -> bool:
        """Lazy-load the model on first use."""
        if self._model is not None:
            return True
            
        if self.backend == "mock":
            return True
            
        if self.backend == "moondream":
            return self._load_moondream()
            
        if self.backend == "openai":
            return True  # No model to load, uses API
            
        return False
    
    def _load_moondream(self) -> bool:
        """Load the Moondream2 model."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            logger.info("[VisualAgent] Loading Moondream2 model (this may take a moment)...")
            
            model_id = "vikhyatk/moondream2"
            revision = "2025-01-09"  # Latest stable revision
            
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            
            self._model = AutoModelForCausalLM.from_pretrained(
                model_id,
                trust_remote_code=True,
                revision=revision,
                torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
            ).to(self._device)
            
            self._processor = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True,
                revision=revision,
            )
            
            logger.info(f"[VisualAgent] Moondream2 loaded on {self._device}")
            return True
            
        except Exception as e:
            logger.error(f"[VisualAgent] Failed to load Moondream2: {e}")
            self.backend = "mock"
            return False
    
    def describe_state(self, screenshot_path: str) -> str:
        """
        Analyze a screenshot and describe the UI state.
        
        Args:
            screenshot_path: Path to the UI screenshot.
            
        Returns:
            Textual description of the UI state.
        """
        if not os.path.exists(screenshot_path):
            return "Error: Screenshot not found."
        
        self._ensure_model_loaded()
        
        if self.backend == "mock":
            return self._mock_describe()
            
        if self.backend == "moondream":
            return self._moondream_query(
                screenshot_path,
                "Describe this web page UI. What are the main interactive elements?"
            )
            
        if self.backend == "openai":
            return self._openai_query(
                screenshot_path,
                "Describe this web page UI. List the main interactive elements you see."
            )
        
        return "Error: Unknown backend"
    
    def find_element(self, screenshot_path: str, element_description: str) -> Optional[VisualElement]:
        """
        Find an element in the screenshot by description.
        
        Args:
            screenshot_path: Path to the UI screenshot.
            element_description: Natural language description of the element.
            
        Returns:
            VisualElement with coordinates, or None if not found.
        """
        if not os.path.exists(screenshot_path):
            return None
        
        self._ensure_model_loaded()
        
        prompt = f"Find the {element_description} in this image. Describe its location (top/bottom, left/right) and approximate position."
        
        if self.backend == "mock":
            return VisualElement(
                description=element_description,
                x=100, y=100, width=80, height=30,
                confidence=0.8
            )
            
        if self.backend == "moondream":
            response = self._moondream_query(screenshot_path, prompt)
            return self._parse_element_response(response, element_description)
            
        if self.backend == "openai":
            response = self._openai_query(screenshot_path, prompt)
            return self._parse_element_response(response, element_description)
        
        return None
    
    def verify_action(self, before_path: str, after_path: str, action_description: str) -> float:
        """
        Compare two screenshots to verify if an action had the intended effect.
        
        Args:
            before_path: Screenshot before the action.
            after_path: Screenshot after the action.
            action_description: Description of what the action should have done.
        
        Returns:
            Confidence score (0.0-1.0) that the action succeeded.
        """
        if not os.path.exists(before_path) or not os.path.exists(after_path):
            return 0.0
        
        self._ensure_model_loaded()
        
        if self.backend == "mock":
            return 0.85  # Optimistic mock
        
        # For now, use a simple approach: describe both and compare
        before_desc = self.describe_state(before_path)
        after_desc = self.describe_state(after_path)
        
        # Ask the VLM to compare
        prompt = f"""Compare these two UI states:
BEFORE: {before_desc}
AFTER: {after_desc}

Did the action "{action_description}" succeed? Rate confidence from 0 to 100."""
        
        if self.backend == "moondream":
            response = self._moondream_query(after_path, prompt)
        elif self.backend == "openai":
            response = self._openai_query(after_path, prompt)
        else:
            return 0.5
        
        # Parse confidence from response
        try:
            import re
            numbers = re.findall(r'\d+', response)
            if numbers:
                confidence = min(100, max(0, int(numbers[0]))) / 100.0
                return confidence
        except:
            pass
        
        return 0.5  # Default medium confidence
    
    def _moondream_query(self, image_path: str, prompt: str) -> str:
        """Query the Moondream model."""
        try:
            from PIL import Image
            
            image = Image.open(image_path)
            
            # Encode the image
            enc_image = self._model.encode_image(image)
            
            # Generate response
            response = self._model.answer_question(enc_image, prompt, self._processor)
            
            return response
            
        except Exception as e:
            logger.error(f"[VisualAgent] Moondream query failed: {e}")
            return f"Error: {e}"
    
    def _openai_query(self, image_path: str, prompt: str) -> str:
        """Query OpenAI GPT-4o Vision."""
        try:
            import openai
            from PIL import Image
            import io
            
            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_data}"}
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"[VisualAgent] OpenAI query failed: {e}")
            return f"Error: {e}"
    
    def _mock_describe(self) -> str:
        """Return a mock description for testing."""
        return """Web page UI analysis:
- Header: Navigation bar with logo and menu items
- Main content: Form with input fields and buttons
- Interactive elements: Login button, signup link, text inputs
- Footer: Copyright and links"""
    
    def _parse_element_response(self, response: str, description: str) -> Optional[VisualElement]:
        """Parse VLM response to extract element location."""
        # This is a simplified parser - real implementation would be more robust
        response_lower = response.lower()
        
        # Estimate position from keywords
        x, y = 400, 300  # Default center
        
        if "top" in response_lower:
            y = 100
        elif "bottom" in response_lower:
            y = 600
        elif "middle" in response_lower or "center" in response_lower:
            y = 350
            
        if "left" in response_lower:
            x = 100
        elif "right" in response_lower:
            x = 700
        elif "center" in response_lower:
            x = 400
        
        return VisualElement(
            description=description,
            x=x, y=y,
            width=100, height=40,
            confidence=0.7
        )
