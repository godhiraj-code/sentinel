"""
DecisionEngine - Intelligence Layer Router.

This module now acts as a router/manager that selects the best 
"Brain" implementation based on system resources and configuration.
"""

from typing import Any, Dict, List, Optional
import logging

from sentinel.core.system_profiler import SystemProfiler, SystemProfile
from .brains.base import Decision, BrainInterface
from .brains.heuristic_brain import HeuristicBrain
from .brains.cloud_brain import CloudBrain
from .brains.local_brain import LocalBrain

logger = logging.getLogger(__name__)

# Re-export Decision for compatibility
Decision = Decision


class DecisionEngine:
    """
    Intelligent decision making router.
    
    Selects the optimal intelligence backend (Heuristic, Cloud, or Local)
    and delegates decision making to it.
    """
    
    def __init__(
        self,
        mock_mode: bool = True,  # Legacy flag, maps to 'heuristic' if True
        model_path: Optional[str] = None,
        brain_type: str = "auto",  # 'auto', 'heuristic', 'cloud', 'local'
    ):
        """
        Initialize the decision engine.
        
        Args:
            mock_mode: Legacy flag. If True, forces heuristic brain.
            model_path: Path to local SLM model.
            brain_type: Strategy for selecting brain ('auto', 'heuristic', 'cloud', 'local').
        """
        self.brain: BrainInterface = None
        self.brain_type = brain_type.lower()
        
        # Backward compatibility
        if mock_mode:
            self.brain_type = "heuristic"
        
        self._init_brain(model_path)
    
    def _init_brain(self, model_path: Optional[str]) -> None:
        """Initialize the selected brain."""
        
        # If auto, ask the profiler
        if self.brain_type == "auto":
            profile = SystemProfiler.get_profile()
            self.brain_type = SystemProfiler.recommend_brain_type(profile)
            logger.info(f"[DecisionEngine] Auto-selected brain: {self.brain_type}")
        
        logger.info(f"[DecisionEngine] Initializing {self.brain_type} brain...")
        
        if self.brain_type == "heuristic":
            self.brain = HeuristicBrain()
            
        elif self.brain_type == "cloud":
            self.brain = CloudBrain(model=model_path)
            
        elif self.brain_type == "local":
            self.brain = LocalBrain(model_path=model_path)
            
        else:
            logger.warning(f"Unknown brain type '{self.brain_type}', falling back to heuristic")
            self.brain = HeuristicBrain()
            
    def decide(
        self,
        goal: Any,  # Now accepts GoalStep
        world_state: List[Any],
        history: List[Decision],
        full_goal: Optional[Any] = None  # Now accepts ParsedGoal
    ) -> Decision:
        """
        Delegate decision to the active brain.
        """
        return self.brain.decide(goal, world_state, history, full_goal=full_goal)
