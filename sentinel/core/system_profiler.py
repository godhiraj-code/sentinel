"""
System Profiler for adaptive brain selection.

Detects hardware capabilities (RAM, CPU) and available API keys 
to recommend the optimal intelligence backend.
"""

import os
import psutil
import shutil
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

@dataclass
class SystemProfile:
    """Hardware and environment profile."""
    total_ram_gb: float
    available_ram_gb: float
    cpu_count: int
    has_gpu: bool
    has_openai_key: bool
    has_anthropic_key: bool
    
    @property
    def can_run_local_slm(self) -> bool:
        """
        Check if the system can comfortably run a local SLM (e.g. Phi-3).
        
        Requirements:
        - At least 8GB RAM (SLM acts as ~4GB overhead)
        - Or a GPU (not strictly checked here, but helps)
        """
        # Conservative check: Needs 8GB+ RAM to run OS + Browser + Model
        return self.total_ram_gb >= 8.0

class SystemProfiler:
    """Detects system capabilities."""
    
    @staticmethod
    def get_profile() -> SystemProfile:
        """Get the current system profile."""
        
        # RAM
        vm = psutil.virtual_memory()
        total_gb = vm.total / (1024 ** 3)
        available_gb = vm.available / (1024 ** 3)
        
        # CPU
        cpu_count = psutil.cpu_count(logical=True)
        
        # GPU (Basic check for NVIDIA)
        has_gpu = shutil.which("nvidia-smi") is not None
        
        # Keys
        has_openai = "OPENAI_API_KEY" in os.environ and os.environ["OPENAI_API_KEY"].strip()
        has_anthropic = "ANTHROPIC_API_KEY" in os.environ and os.environ["ANTHROPIC_API_KEY"].strip()
        
        return SystemProfile(
            total_ram_gb=round(total_gb, 2),
            available_ram_gb=round(available_gb, 2),
            cpu_count=cpu_count or 1,
            has_gpu=bool(has_gpu),
            has_openai_key=bool(has_openai),
            has_anthropic_key=bool(has_anthropic)
        )
    
    @staticmethod
    def recommend_brain_type(profile: Optional[SystemProfile] = None) -> str:
        """
        Recommend the best brain type based on the profile.
        
        Returns:
            str: 'cloud', 'local', or 'heuristic'
        """
        if profile is None:
            profile = SystemProfiler.get_profile()
            
        logger.info(f"System Profile: RAM={profile.total_ram_gb}GB, Keys=OA:{profile.has_openai_key}/AN:{profile.has_anthropic_key}")
        
        # 1. Prefer Cloud if keys are available (Highest Intelligence)
        if profile.has_openai_key or profile.has_anthropic_key:
            return "cloud"
        
        # 2. Prefer Local if hardware is sufficient (Privacy/Free)
        if profile.can_run_local_slm:
            return "local"
            
        # 3. Fallback to Heuristic (Low resource / Simple tasks)
        return "heuristic"

if __name__ == "__main__":
    # Debug run
    logging.basicConfig(level=logging.INFO)
    profile = SystemProfiler.get_profile()
    print(f"Profile: {profile}")
    recommendation = SystemProfiler.recommend_brain_type(profile)
    print(f"Recommended Brain: {recommendation}")
