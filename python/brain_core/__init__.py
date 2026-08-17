"""Kato World — brain_core package.

Modular decomposition of the brain (v0.2). Modules are pure-ish: they
import the monolith lazily inside functions to avoid circular imports.
The monolith (brain_server.py) remains the composition root / API layer.
"""

from .cognition import (
    thought_pressure,
    parse_planner_json,
    system2_llm,
    PLANNER_ACTION_ALLOWLIST,
)
from .learning import learn_from_action, create_learning_module
from .global_workspace import GlobalWorkspace, create_global_workspace
from .predictive_processing import PredictiveProcessor, create_predictive_processor
from .metacognition import MetacognitionEngine, create_metacognition_engine
from .agency import AgencyEngine, create_agency_engine
from .theory_of_mind import TheoryOfMindEngine, create_theory_of_mind
from .narrative_self import NarrativeSelfEngine, create_narrative_self
from .phenomenal import PhenomenalEngine, create_phenomenal_engine

__all__ = [
    "thought_pressure",
    "parse_planner_json",
    "system2_llm",
    "PLANNER_ACTION_ALLOWLIST",
    "learn_from_action",
    "create_learning_module",
    "GlobalWorkspace",
    "create_global_workspace",
    "PredictiveProcessor",
    "create_predictive_processor",
    "MetacognitionEngine",
    "create_metacognition_engine",
    "AgencyEngine",
    "create_agency_engine",
    "TheoryOfMindEngine",
    "create_theory_of_mind",
    "NarrativeSelfEngine",
    "create_narrative_self",
    "PhenomenalEngine",
    "create_phenomenal_engine",
]
