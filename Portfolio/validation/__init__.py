"""
Portfolio.validation — CPCV meta-methodology for strategy validation.

Public API
----------
from Portfolio.validation.cpcv import run_cpcv
from Portfolio.validation.multi_test import deflated_sharpe, harvey_liu_bhy
from Portfolio.validation.pipeline import generate_cpcv_report
"""
from Portfolio.validation.cpcv import run_cpcv
from Portfolio.validation.multi_test import deflated_sharpe, harvey_liu_bhy
from Portfolio.validation.pipeline import generate_cpcv_report

__all__ = ["run_cpcv", "deflated_sharpe", "harvey_liu_bhy", "generate_cpcv_report"]
