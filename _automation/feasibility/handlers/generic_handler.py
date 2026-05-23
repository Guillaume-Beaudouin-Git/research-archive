"""
Fallback handler for hypotheses that don't match a specialised class.
Always classifies True. Runs the standard 3-level pipeline without
asset-class-specific pre-processing or custom IC computation.
"""
from .base import HypothesisHandler


class GenericHandler(HypothesisHandler):
    @classmethod
    def classify(cls, promising_md_path: str) -> bool:
        return True

    def run_level_A(self) -> dict: ...
    def run_level_B(self) -> dict: ...
    def run_level_C(self) -> dict: ...
    def generate_report(self) -> str: ...
