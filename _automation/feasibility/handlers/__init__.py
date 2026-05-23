"""
Handler registry for the feasibility pipeline.
Handlers are tried in order; first classify() returning True wins.
"""
from .skip_month_handler import SkipMonthHandler
from .exit_rule_handler import ExitRuleHandler
from .regime_filter_handler import RegimeFilterHandler
from .generic_handler import GenericHandler

HANDLER_REGISTRY = [
    SkipMonthHandler,
    ExitRuleHandler,
    RegimeFilterHandler,
    GenericHandler,
]
