"""
The Sentinel - Autonomous Web Testing Framework

A unified orchestrator combining specialized automation libraries
for testing "untestable" web environments.
"""

__version__ = "0.3.0"
__author__ = "Dhiraj Das"
__email__ = "contact@dhirajdas.dev"

from sentinel.core.orchestrator import SentinelOrchestrator

__all__ = [
    "SentinelOrchestrator",
    "__version__",
]
