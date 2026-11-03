import pytest

from app.services.explainability_service import ExplainabilityService
from app.services.causal_reasoning_service import (
    CausalReasoningService,
    classify_scenario,
    score_kpi_relevance,
)
from app.services.impact_analysis_service import ImpactAnalysisService
from app.services.report_service import ReportService
from app.services.root_cause_analysis_service import RootCauseAnalysisService


def test_root_cause_uses_generic_dashboard_and_control_evidence_without_kpis():
    findings = RootCauseAnalysisService().analyze(
        scenario="What if data integrity declines?",
        dashboard_data={},
        matched_dashboard_records=[{
            "metric_name": "Data Integrity Rate",
            "value": 0.82,
            "status": "Below target",
        }],
        kpi_insights={},
        rules=[{"name": "Data integrity threshold", "severity": "HIGH"}],
        actions=[],
        impact_result={"dimensions": [{
            "dimension_name": "Data quality",
            "severity": "HIGH",
            "impact_description": "Indicator is below target.",
        }]},
    )

    assert findings
    assert findings[0]["root_cause"] == "Risk control or resilience weakness"
    assert len(findings[0]["evidence"]) <= 3
    assert any("Dashboard:" in item for item in findings[0]["evidence"])
    assert any("Context:" in item or "Scenario:" in item for item in findings[0]["evidence"])


def test_scenario_only_root_cause_is_cautious_and_domain_agnostic():
    findings = RootCauseAnalysisService().analyze(
        scenario={
            "query": "What would happen if average CSAT falls from 3.42 to 2.8?"
        },
        dashboard_data={},
        matched_dashboard_records=[],
        kpi_insights={},
        rules=[],
        actions=[],
        impact_result={},
    )

    assert len(findings) == 1
    assert findings[0]["root_cause"] == "Service-quality or issue-resolution shortfall"
    assert all(finding["evidence"] for finding in findings)
    assert all(len(finding["evidence"]) <= 3 for finding in findings)
    assert all(len(evidence) <= 180 for finding in findings for evidence in finding["evidence"])
    assert all(0 <= finding["confidence"] <= 1 for finding in findings)
    assert all(finding["business_consequence"] for finding in findings)
    assert all(finding["recommended_mitigation"] for finding in findings)


def test_kpi_confidence_and_dashboard_evidence_strengthen_root_cause():
    findings = RootCauseAnalysisService().analyze(
        scenario={"query": "Assess project budget overrun."},
        dashboard_data={"projects": [{"name": "Tower A", "cost_overrun": "AED 2M"}]},
        matched_dashboard_records=[{"construction_variance": "AED 2M"}],
        kpi_insights={
            "kpis": [{
                "kpi_name": "Construction Cost Variance",
                "kpi_value": "AED 2M",
                "reasoning": "Actual committed cost is above the approved budget.",
                "confidence_score": 0.94,
            }]
        },
        rules=[{"name": "Cost approval threshold", "description": "Budget overrun approvals required."}],
        actions=[{"action_title": "Review change orders", "category": "cost overrun"}],
        impact_result={"dimensions": [{
            "dimension_name": "Financial & Liquidity Exposure",
            "severity": "HIGH",
            "score": 72,
        }]},
    )

    assert findings
    assert findings[0]["confidence"] > 0.8
    assert any("Construction Cost Variance" in item for item in findings[0]["evidence"])
    assert any("Rule:" in item for item in findings[0]["evidence"])


def test_root_cause_is_nonempty_but_explicitly_cautious_without_evidence():
    findings = RootCauseAnalysisService().analyze(
        scenario="",
        dashboard_data={},
        matched_dashboard_records=[],
        kpi_insights={},
        rules=[],
        actions=[],
        impact_result={},
    )

    assert len(findings) == 1
    assert findings[0]["confidence"] == 0.1
    assert "Insufficient evidence" in findings[0]["root_cause"]
    assert findings[0]["evidence"]


@pytest.mark.asyncio
async def test_impact_report_and_explainability_use_root_causes_without_graph():
    state = {
        "query": "What would happen if average CSAT falls from 3.42 to 2.8?",
        "scenario": {"description": "Customer satisfaction decline"},
        "dashboard_data": {},
        "dashboard_rows": [],
        "matched_dashboard_records": [],
        "kpi_insights": {"kpis": [{
            "kpi_name": "Customer Satisfaction",
            "kpi_value": 2.8,
            "kpi_unit": "score",
            "reasoning": "Customer satisfaction is declining.",
            "confidence_score": 0.9,
        }]},
        "rules": [],
        "actions": [],
        "action_stats": {},
        "knowledge_graph_data": {"nodes": [], "edges": []},
        "graph_summary": {"graph_exists": False, "total_nodes": 0, "total_edges": 0},
        "simulation_result": {"metrics": {"impact_probability": 0.4}},
        "include_full_state": True,
    }

    impact = await ImpactAnalysisService().analyze(state)
    state["impact_result"] = impact
    assert impact["root_cause_analysis"]
    assert impact["causal_analysis"]["causal_chain"]
    assert impact["financial_model"]["scenario_exposure"]["causal_chain"] == (
        impact["causal_analysis"]["causal_chain"]
    )

    class CapturingLLM:
        is_configured = True
        prompt = ""

        async def generate_json(self, prompt, system_instruction):
            self.prompt = prompt
            return {
                "executive_summary": "Customer confidence is at risk due to service delivery pressure.",
                "current_business_context": "Customer satisfaction is weakening.",
                "business_impact": "Retention and referrals may decline.",
                "financial_impact": "No financial estimate is available.",
                "operational_impact": "Delivery and resolution performance need review.",
                "key_risks": ["Customer confidence may weaken."],
                "recommended_response": "Review service and delivery issues.",
                "executive_conclusion": "Act quickly to protect customer commitments.",
            }

    llm = CapturingLLM()
    state["explanation"] = await ExplainabilityService(llm_service=llm).explain(state)
    report = await ReportService().generate_report(state)

    assert '"root_causes"' in llm.prompt
    assert "Service-quality or issue-resolution shortfall" in llm.prompt
    assert "## Root Cause Analysis" in report["markdown_report"]
    assert "## Causal Impact Analysis" in report["markdown_report"]
    assert "Selected KPI impact path:" in report["markdown_report"]
    assert "## Financial Impact" not in report["markdown_report"]
    assert report["financial_impact"] is None
    assert "Confidence:" in report["markdown_report"]
    assert "Mitigation:" in report["markdown_report"]
    assert "## Affected Entities" not in report["markdown_report"]
    assert len(report["root_cause_analysis"][0]["evidence"]) <= 3
    assert report["root_cause_analysis"][0]["mitigation"]
    assert impact["root_cause_analysis"][0]["root_cause"] != (
        impact["causal_analysis"]["primary_kpi"]
    )
    assert all(
        len(item.split()) <= 22
        for item in report["root_cause_analysis"][0]["evidence"]
    )


@pytest.mark.asyncio
async def test_root_cause_analysis_survives_knowledge_graph_unavailable():
    impact = await ImpactAnalysisService().analyze({
        "query": "What if the project budget overruns by 20%?",
        "scenario": {"description": "Budget overrun"},
        "dashboard_data": {},
        "matched_dashboard_records": [],
        "kpi_insights": {"kpis": [{
            "kpi_name": "Construction Budget Overrun",
            "kpi_value": "AED 12M",
            "reasoning": "Committed costs exceed the approved budget.",
            "confidence_score": 0.88,
        }]},
        "rules": [],
        "actions": [],
        "simulation_result": {"metrics": {}},
    })

    assert impact["root_cause_analysis"]
    assert impact["root_cause_analysis"][0]["root_cause"] == (
        "Cost-control or margin pressure"
    )
    assert impact["causal_analysis"]["graph_available"] is False


def test_available_graph_relationships_support_causal_context_without_claiming_causation():
    result = CausalReasoningService().analyze(
        scenario="What if operating performance declines?",
        dashboard_data={},
        matched_dashboard_records=[],
        kpi_insights={"kpis": [{
            "kpi_name": "Operational throughput",
            "reasoning": "Throughput is below target.",
            "confidence_score": .8,
        }]},
        actions=[],
        rules=[],
        impact_result={},
        graph_summary={"graph_exists": True, "total_nodes": 3, "total_edges": 2},
        dependency_paths=[{
            "entities": ["Operation A", "Process B", "Output C"],
            "relationships": ["DEPENDS_ON", "PRODUCES"],
        }],
        related_entities=[{"name": "Process B"}],
    )

    assert result["graph_available"] is True
    assert result["graph_evidence"] == [
        "Operation A -[DEPENDS_ON]-> Process B -[PRODUCES]-> Output C"
    ]
    assert result["graph_evidence"][0] in result["root_cause_analysis"][0]["evidence"]


@pytest.mark.parametrize(
    ("kpi", "scenario", "expected_category"),
    [
        (
            {"kpi_name": "Customer experience score", "reasoning": "Retention risk is rising.", "confidence_score": .9},
            "What if customer experience declines?",
            "CUSTOMER_EXPERIENCE",
        ),
        (
            {"kpi_name": "Cash flow margin", "reasoning": "Liquidity is weakening.", "confidence_score": .9},
            "What if cash flow decreases?",
            "FINANCIAL",
        ),
        (
            {"kpi_name": "Production throughput", "reasoning": "Output is below target.", "confidence_score": .9},
            "What if production throughput falls?",
            "OPERATIONAL",
        ),
        (
            {"kpi_name": "Regulatory violations", "reasoning": "Control requirements are not met.", "confidence_score": .9},
            "What if regulatory violations rise?",
            "COMPLIANCE",
        ),
        (
            {"kpi_name": "Business continuity exposure", "reasoning": "Continuity risk is increasing.", "confidence_score": .9},
            "What if business continuity exposure rises?",
            "RISK",
        ),
        (
            {"kpi_name": "Strategic value realization", "reasoning": "Delivery milestones are at risk.", "confidence_score": .9},
            "What if strategic value realization declines?",
            "STRATEGIC",
        ),
    ],
)
def test_causal_paths_are_category_based_and_domain_agnostic(
    kpi, scenario, expected_category
):
    result = CausalReasoningService().analyze(
        scenario=scenario,
        dashboard_data={},
        matched_dashboard_records=[],
        kpi_insights={"kpis": [kpi]},
        actions=[],
        rules=[],
        impact_result={},
    )

    assert result["primary_kpi_category"] == expected_category
    assert result["causal_chain"][0] != kpi["kpi_name"]
    assert len(result["causal_chain"]) >= 3
    assert result["causal_chain"][-1] == "Enterprise Risk"
    assert not any(
        name == kpi["kpi_name"]
        for name in result["causal_chain"]
    )
    assert result["primary_impact_path"] == " → ".join(result["causal_chain"])


def test_causal_path_uses_scenario_linked_kpis_and_modeled_impact_evidence():
    result = CausalReasoningService().analyze(
        scenario="What if customer satisfaction declines?",
        dashboard_data={},
        matched_dashboard_records=[],
        kpi_insights={"kpis": [
            {
                "kpi_name": "Customer Satisfaction",
                "reasoning": "Customer satisfaction is declining.",
                "category": "CUSTOMER",
            },
            {
                "kpi_name": "Contract Variance",
                "reasoning": "Customer escalations are linked to contract variances.",
                "category": "FINANCIAL",
            },
        ]},
        primary_kpi={
            "kpi_name": "Customer Satisfaction",
            "reasoning": "Customer satisfaction is declining.",
            "category": "CUSTOMER",
        },
        supporting_kpis=[{
            "kpi_name": "Contract Variance",
            "reasoning": "Customer escalations are linked to contract variances.",
            "category": "FINANCIAL",
        }],
        actions=[],
        rules=[],
        impact_result={"financial_model": {"scenario_exposure": {"impacts": [
            {"category": "FINANCIAL", "impact": "Financial Risk"},
        ]}}},
    )

    assert result["scenario_category"] == "customer_experience"
    assert result["causal_chain"] == [
        "Customer Experience Deterioration",
        "Customer Retention Risk",
        "Revenue Risk",
        "Enterprise Risk",
    ]
    assert result["causal_basis"][1]["relevance_rationale"]


def test_causal_analysis_uses_selected_kpi_instead_of_reranking_insights():
    result = CausalReasoningService().analyze(
        scenario="What if customer experience declines?",
        dashboard_data={},
        matched_dashboard_records=[],
        kpi_insights={"kpis": [
            {
                "kpi_name": "Customer experience score",
                "kpi_value": 2.8,
                "reasoning": "Customer experience is declining due to delayed issue resolution.",
                "confidence_score": 0.9,
            },
            {
                "kpi_name": "Existing contract exposure",
                "kpi_value": 2_100_000_000,
                "reasoning": "Current financial exposure remains elevated.",
                "confidence_score": 0.99,
            },
        ]},
        primary_kpi={
            "kpi_name": "Existing contract exposure",
            "kpi_value": 2_100_000_000,
            "reasoning": "Current financial exposure remains elevated.",
            "confidence_score": 0.99,
        },
        actions=[],
        rules=[],
        impact_result={},
    )

    assert result["primary_kpi"] == "Existing contract exposure"
    assert result["root_cause_analysis"]


@pytest.mark.parametrize(
    ("scenario", "expected_category"),
    [
        ({"domain": "Sales", "change_description": "conversion rate falls"}, "FINANCIAL"),
        ({"domain": "Finance", "change_description": "cash availability weakens"}, "FINANCIAL"),
        ({"domain": "Construction", "change_description": "delivery schedule slips"}, "OPERATIONAL"),
        ({"domain": "Manufacturing", "change_description": "production output falls"}, "OPERATIONAL"),
        ({"domain": "Procurement", "change_description": "supplier lead time increases"}, "OPERATIONAL"),
        ({"domain": "Compliance", "change_description": "control breach risk rises"}, "COMPLIANCE"),
        ({"domain": "Customer", "change_description": "satisfaction falls"}, "CUSTOMER_EXPERIENCE"),
    ],
)
def test_scenario_classification_uses_parsed_domain_and_change(
    scenario, expected_category
):
    assert classify_scenario(scenario) == expected_category


def test_kpi_relevance_uses_matched_entity_evidence():
    scenario = "What if customer satisfaction declines?"
    matching = score_kpi_relevance(
        scenario=scenario,
        record={
            "kpi_name": "Customer Satisfaction",
            "category": "CUSTOMER",
            "customer": "Northwind",
        },
        matched_entities={"target_entity": "Northwind"},
    )
    nonmatching = score_kpi_relevance(
        scenario=scenario,
        record={
            "kpi_name": "Customer Satisfaction",
            "category": "CUSTOMER",
            "customer": "Contoso",
        },
        matched_entities={"target_entity": "Northwind"},
    )

    assert matching["score"] > nonmatching["score"]
