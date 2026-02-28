"""
Agent 04 — Upstream Finance Calculator.

A pure financial calculation engine for upstream oil & gas M&A due diligence.
Architecture-agnostic: callable from CLI, FastAPI, LangGraph, or other agents.

Public API:
    from aigis_agents.agent_04_finance_calculator.agent import finance_calculator_agent
    from aigis_agents.agent_04_finance_calculator.calculator import (
        calculate_npv, calculate_lifting_cost, calculate_netback, build_cash_flow_schedule
    )
    from aigis_agents.agent_04_finance_calculator.fiscal_engine import (
        calculate_royalty_payment, get_fiscal_profile
    )
    from aigis_agents.agent_04_finance_calculator.models import FinancialInputs
"""
