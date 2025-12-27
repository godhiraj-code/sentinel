from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from sentinel.core.goal_parser import GoalStep, ParsedGoal

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
        goal: "GoalStep",
        world_state: List[Any],
        history: List[Decision],
        full_goal: Optional["ParsedGoal"] = None
    ) -> Decision:
        """
        Make a decision based on the goal and world state.
        
        Args:
            goal: The structured current step to achieve.
            world_state: List of ElementNodes representing the current page.
            history: List of previous decisions.
            full_goal: The complete parsed goal context.
            
        Returns:
            Decision: The logical next step.
        """
        pass
