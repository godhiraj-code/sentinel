from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Decision:
    """Represents a decided action."""
    action: str
    target: str
    reasoning: str
    confidence: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

class BrainInterface(ABC):
    """Abstract base class for Intelligence Brains."""
    
    @abstractmethod
    def decide(
        self,
        goal: str,
        world_state: List[Any],
        history: List[Decision]
    ) -> Decision:
        """
        Make a decision based on the goal and world state.
        
        Args:
            goal: The user's natural language goal.
            world_state: List of ElementNodes representing the current page.
            history: List of previous decisions.
            
        Returns:
            Decision: The logical next step.
        """
        pass
