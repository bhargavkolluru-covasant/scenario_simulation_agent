import pytest
from app.services.gemini_service import GeminiService, get_gemini_service, get_llm
from app.services.scenario_parser_service import ScenarioParserService
from app.services.explainability_service import ExplainabilityService
from app.services.rule_compilation_service import RuleCompilationService
from app.nodes.scenario_parser_node import scenario_parser_node
from app.nodes.strategy_selector_node import (
    SimulationStrategy,
    determine_strategy,
    strategy_selector_node,
)
from app.nodes.explainability_node import explainability_node
from app.nodes.compile_rule_node import compile_rule_node
from app.state.simulation_state import SimulationState


@pytest.mark.asyncio
async def test_gemini_service_initialization():
    service = get_gemini_service()
    assert isinstance(service, GeminiService)
    assert service.model == "gemini-1.5-pro"
    llm = get_llm()
    assert llm.model == "gemini-1.5-pro"


@pytest.mark.asyncio
async def test_scenario_parser_service():
    parser = ScenarioParserService()
    query = "What if supplier ABC fails next quarter?"
    scenario = await parser.parse(query)

    assert isinstance(scenario, dict)
    assert scenario.get("scenario_type") == "enterprise_scenario"
    assert "abc" in scenario.get("target_entity", "").lower()
    assert scenario.get("change_type") == "scenario_change"
    assert scenario.get("change_percentage") == 0
    assert scenario.get("time_horizon") == "next quarter"
    assert scenario.get("domain") == "unspecified"


@pytest.mark.asyncio
async def test_scenario_parser_node():
    state: SimulationState = {
        "query": "What if supplier ABC fails next quarter?",
    }
    result = await scenario_parser_node(state)
    assert "scenario" in result
    assert result["scenario"]["scenario_type"] == "vendor_failure"
    assert result["current_node"] == "scenario_parser"


@pytest.mark.asyncio
async def test_strategy_selector_node():
    # Vendor failure scenario -> SUPPLY_CHAIN
    vendor_scenario = {
        "scenario_type": "vendor_failure",
        "domain": "supply_chain",
        "target_entity": "Supplier Acme",
        "change_type": "failure",
    }
    semantic_entities = [{"entity_type": "vendor", "entity_name": "Supplier Acme"}]
    rules = [{"category": "vendor_risk", "rule_type": "operational"}]

    strategy = determine_strategy(vendor_scenario, semantic_entities, rules)
    assert strategy in (SimulationStrategy.SUPPLY_CHAIN, SimulationStrategy.HYBRID)

    # Financial scenario -> FINANCIAL_IMPACT
    fin_scenario = {
        "scenario_type": "financial_impact",
        "domain": "finance",
        "target_entity": "Accounts Payable",
        "change_type": "default",
    }
    fin_entities = [{"entity_type": "invoice", "entity_name": "INV-101"}]
    fin_rules = [{"category": "financial_exposure", "rule_type": "payment"}]

    fin_strategy = determine_strategy(fin_scenario, fin_entities, fin_rules)
    assert fin_strategy in (SimulationStrategy.FINANCIAL_IMPACT, SimulationStrategy.HYBRID)

    # Node execution
    state: SimulationState = {
        "scenario": vendor_scenario,
        "semantic_entities": semantic_entities,
        "rules": rules,
    }
    node_result = await strategy_selector_node(state)
    assert "strategy" in node_result
    assert node_result["current_node"] == "strategy_selector"


@pytest.mark.asyncio
async def test_rule_compilation_service_and_node():
    compilation_service = RuleCompilationService()
    scenario = {
        "scenario_type": "vendor_failure",
        "target_entity": "Supplier Acme",
        "change_type": "failure",
        "change_percentage": 100,
        "time_horizon": "next quarter",
        "domain": "supply_chain",
    }
    compiled = await compilation_service.compile_rule(scenario)
    assert isinstance(compiled, dict)
    assert compiled.get("success") is True
    assert "rule" in compiled
    assert compiled["rule"]["target_entity"] == "Supplier Acme"

    state: SimulationState = {
        "scenario": scenario,
    }
    node_result = await compile_rule_node(state)
    assert "compiled_rules" in node_result
    assert node_result["compiled_rules"]["success"] is True
    assert node_result["current_node"] == "compile_rule"


@pytest.mark.asyncio
async def test_explainability_service_and_node():
    service = ExplainabilityService()
    state: SimulationState = {
        "scenario": {
            "scenario_type": "vendor_failure",
            "target_entity": "Supplier Acme",
            "change_type": "failure",
            "change_percentage": 100,
            "time_horizon": "next quarter",
            "domain": "supply_chain",
        },
        "simulation_result": {
            "metrics": {
                "baseline_financial_exposure": 50000.0,
                "simulated_financial_exposure": 120000.0,
                "exposure_variance_percentage": 140.0,
                "impact_probability": 0.85,
            }
        },
        "impact_result": {
            "overall_impact_score": 82.5,
            "overall_severity": "CRITICAL",
            "dimensions": [],
            "blast_radius_entities": ["Acme Plant", "PO-9002"],
        },
        "recommendations": [
            {
                "recommendation_id": "REC-01",
                "action_title": "Activate Alternate Supplier",
                "priority": "CRITICAL",
                "urgency": "IMMEDIATE",
            }
        ],
    }

    explanation = await service.explain(state)
    assert isinstance(explanation, dict)
    assert "executive_summary" in explanation
    assert "key_drivers" in explanation
    assert len(explanation["key_drivers"]) > 0
    assert "business_impact" in explanation
    assert "risk_explanation" in explanation
    assert "recommendation_rationale" in explanation

    node_result = await explainability_node(state)
    assert "explanation" in node_result
    assert node_result["current_node"] == "explainability"
