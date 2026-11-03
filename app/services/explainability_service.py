import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from app.models.explainability_models import ExplanationResult
from app.services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

_TEXT_FIELDS = (
    "executive_summary",
    "current_business_context",
    "financial_impact",
    "operational_impact",
    "recommended_response",
    "executive_conclusion",
    "business_impact",
    "risk_explanation",
    "recommendation_rationale",
)
_LIST_FIELDS = ("key_risks", "key_drivers")
def _short_text(value: Any, max_characters: int = 160) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, ensure_ascii=False, default=str)
    else:
        text = " ".join(str(value).split())
    return text[:max_characters] + ("…" if len(text) > max_characters else "")


def _estimate_tokens(text: str) -> int:
    tokens = 0
    for token in re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE):
        tokens += max(1, (len(token) + 3) // 4) if token.isalnum() else 1
    return tokens


def _model_parts(financial_model: Any) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    if not isinstance(financial_model, dict):
        return {}, {}, {}
    current = financial_model.get(
        "current_exposure",
        financial_model.get("existing_enterprise_exposure", {}),
    )
    scenario = financial_model.get(
        "scenario_exposure",
        financial_model.get("scenario_incremental_exposure", {}),
    )
    combined = financial_model.get(
        "combined_outlook",
        financial_model.get("combined_risk_outlook", {}),
    )
    return (
        current if isinstance(current, dict) else {},
        scenario if isinstance(scenario, dict) else {},
        combined if isinstance(combined, dict) else {},
    )


def build_executive_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce workflow state to bounded, executive-relevant evidence for the LLM."""
    scenario = state.get("scenario", {})
    if not isinstance(scenario, dict):
        scenario = {}
    query = _short_text(
        state.get("query") or scenario.get("description") or scenario.get("query"),
        260,
    )
    impact = state.get("impact_result", {})
    if not isinstance(impact, dict):
        impact = {}
    simulation = state.get("simulation_result", {})
    if not isinstance(simulation, dict):
        simulation = {}
    metrics = simulation.get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
    financial_model = impact.get("financial_model") or simulation.get(
        "financial_model"
    ) or metrics.get("financial_model", {})
    current_model, scenario_model, combined_model = _model_parts(financial_model)

    primary_kpi = state.get("primary_kpi")
    selected_kpis = (
        ([primary_kpi] if isinstance(primary_kpi, dict) else [])
        + [
            item
            for item in state.get("supporting_kpis", [])
            if isinstance(item, dict)
        ]
    )
    top_kpis = [
        {
            "name": _short_text(item.get("name"), 80),
            "value": _short_text(item.get("value"), 50),
            "reasoning": _short_text(
                item.get("why_it_matters") or item.get("evidence"), 80
            ),
            "confidence": _short_text(item.get("confidence"), 12),
        }
        for item in selected_kpis
    ]
    selected_risks = [
        item
        for item in (state.get("primary_risk"), state.get("secondary_risk"))
        if isinstance(item, dict)
    ]
    top_risks = [
        {
            "title": _short_text(item.get("name"), 70),
            "severity": _short_text(item.get("severity"), 12),
            "consequence": _short_text(
                item.get("business_impact") or item.get("reason"), 130
            ),
        }
        for item in selected_risks
    ]
    top_actions = [
        {
            "title": _short_text(
                item.get("title") or item.get("action_title") or item.get("action"), 80
            ),
            "priority": _short_text(item.get("priority") or item.get("severity"), 12),
            "rationale": _short_text(
                item.get("business_benefit")
                or item.get("expected_outcome")
                or item.get("rationale"),
                100,
            ),
        }
        for item in state.get("selected_actions", [])
        if isinstance(item, dict)
    ]

    roots = impact.get("root_cause_analysis", [])
    root_causes = []
    if isinstance(roots, list):
        for item in roots[:5]:
            if not isinstance(item, dict):
                continue
            evidence = item.get("evidence", [])
            if not isinstance(evidence, list):
                evidence = [evidence] if evidence else []
            root_causes.append({
                "root_cause": _short_text(item.get("root_cause"), 90),
                "confidence": _short_text(item.get("confidence"), 12),
                "evidence": [_short_text(value, 100) for value in evidence[:3]],
                "business_consequence": _short_text(
                    item.get("business_consequence"), 100
                ),
                "recommended_mitigation": _short_text(
                    item.get("recommended_mitigation"), 100
                ),
            })

    causal = impact.get("causal_analysis", {})
    if not isinstance(causal, dict):
        causal = {}
    causal_context = {
        "primary_impact_path": _short_text(causal.get("primary_impact_path"), 180),
        "primary_kpi": _short_text(
            (state.get("primary_kpi") or {}).get("name")
            if isinstance(state.get("primary_kpi"), dict)
            else "",
            70,
        ),
        "category": _short_text(causal.get("primary_kpi_category"), 20),
        "confidence": _short_text(causal.get("confidence"), 12),
        "basis": [
            {
                "source": _short_text(item.get("kpi") or item.get("source"), 70),
                "reasoning": _short_text(item.get("reasoning"), 100),
            }
            for item in causal.get("causal_basis", [])[:2]
            if isinstance(item, dict)
        ] if isinstance(causal.get("causal_basis"), list) else [],
        "graph_evidence": [
            _short_text(item, 100) for item in causal.get("graph_evidence", [])[:2]
        ] if isinstance(causal.get("graph_evidence"), list) else [],
    }

    current_items = current_model.get("items", [])
    financial_summary: Dict[str, Any] = {
        "current_exposure": [],
        "scenario_exposure": {},
        "combined_outlook": {},
        "confidence": _short_text(financial_model.get("confidence"), 12)
        if isinstance(financial_model, dict)
        else "",
    }
    if isinstance(current_items, list):
        financial_summary["current_exposure"] = [
            {
                "name": _short_text(item.get("name"), 70),
                "amount": _short_text(item.get("formatted_amount") or item.get("value"), 50),
            }
            for item in current_items[:3]
            if isinstance(item, dict)
        ]
    scenario_amounts = scenario_model.get("estimated_amount_by_currency")
    if not isinstance(scenario_amounts, dict):
        scenario_amounts = scenario_model.get("amount_by_currency", {})
    if not isinstance(scenario_amounts, dict):
        scenario_amounts = {}
    scenario_impacts = scenario_model.get("impacts", [])
    amount_evidence = scenario_model.get("amount_evidence", [])
    financial_summary["scenario_exposure"] = {
        "severity": _short_text(scenario_model.get("severity"), 12),
        "direction": _short_text(scenario_model.get("direction"), 12),
        "confidence": _short_text(scenario_model.get("confidence"), 12),
        "estimated_amount_by_currency": {
            _short_text(currency, 8): _short_text(amount, 30)
            for currency, amount in list(scenario_amounts.items())[:3]
        },
        "amount_evidence": [
            {
                "kpi": _short_text(item.get("kpi"), 70),
                "baseline": _short_text(item.get("baseline"), 35),
                "estimate": _short_text(item.get("estimated_scenario_amount"), 35),
                "derivation": _short_text(item.get("derivation"), 90),
                "why": _short_text(item.get("why"), 100),
                "assumptions": [
                    _short_text(value, 80)
                    for value in item.get("assumptions", [])[:2]
                ] if isinstance(item.get("assumptions"), list) else [],
            }
            for item in amount_evidence[:3]
            if isinstance(item, dict)
        ] if isinstance(amount_evidence, list) else [],
        "impacts": [
            {
                "category": _short_text(item.get("category"), 20),
                "impact": _short_text(item.get("impact"), 55),
                "severity": _short_text(item.get("severity"), 12),
            }
            for item in scenario_impacts[:5]
            if isinstance(item, dict)
        ] if isinstance(scenario_impacts, list) else [],
        "reasoning": _short_text(scenario_model.get("financial_reasoning"), 180),
        "assumptions": [
            _short_text(value, 100)
            for value in scenario_model.get("assumptions", [])[:3]
        ] if isinstance(scenario_model.get("assumptions"), list) else [],
    }
    financial_summary["combined_outlook"] = {
        "severity": _short_text(combined_model.get("severity"), 12),
        "summary": _short_text(combined_model.get("summary"), 140),
    }

    matched_records = state.get(
        "matched_dashboard_records",
        state.get("dashboard_rows", []),
    )
    context_facts = []
    if isinstance(matched_records, list):
        preferred = (
            "entity", "entity_name", "name", "status", "risk", "risk_rating",
            "planned_handover", "planned_handover_date", "forecast_date",
            "business_context", "description", "summary",
        )
        for record in matched_records[:3]:
            if not isinstance(record, dict):
                continue
            facts = [
                f"{key}: {_short_text(record[key], 70)}"
                for key in preferred
                if record.get(key) not in (None, "")
                and not isinstance(record[key], (dict, list))
            ][:4]
            if facts:
                context_facts.append("; ".join(facts))

    graph_summary = state.get("graph_summary", {})
    if not isinstance(graph_summary, dict):
        graph_summary = {}
    graph_is_available = bool(
        graph_summary.get("graph_exists")
        and graph_summary.get("total_nodes", 0)
        and graph_summary.get("total_edges", 0)
    )
    if graph_is_available:
        related_entities = state.get("related_entities", [])
        if isinstance(related_entities, list):
            names = [
                _short_text(item.get("name") or item.get("entity_name"), 50)
                for item in related_entities[:3]
                if isinstance(item, dict) and (item.get("name") or item.get("entity_name"))
            ]
            if names:
                context_facts.insert(0, "Related business entities: " + ", ".join(names))
        paths = state.get("dependency_paths", [])
        if isinstance(paths, list):
            for path in paths[:2]:
                if not isinstance(path, dict):
                    continue
                entities = path.get("entities", [])
                if isinstance(entities, list) and entities:
                    context_facts.insert(
                        0,
                        "Dependency chain: "
                        + " -> ".join(_short_text(entity, 35) for entity in entities[:4])
                    )
    elif state.get("knowledge_graph_data") is not None:
        context_facts.append("Knowledge Graph relationships are unavailable.")

    severity = _short_text(impact.get("overall_severity"), 12) or "Unclassified"
    executive_summary = (
        f"Scenario: {query or 'Not specified'}. "
        f"Assessed overall severity: {severity}. "
        "Explain likely business consequences and a proportionate leadership response."
    )
    context = {
        "executive_summary": executive_summary,
        "key_business_context": " ".join(context_facts) or "No concise matched business context available.",
        "causal_analysis": causal_context,
        "top_kpis": top_kpis,
        "top_risks": top_risks,
        "top_actions": top_actions,
        "financial_summary": financial_summary,
        "root_causes": root_causes,
    }
    serialized = json.dumps(context, ensure_ascii=False, separators=(",", ":"), default=str)
    while _estimate_tokens(serialized) > 1500:
        if context["key_business_context"]:
            context_text = context["key_business_context"]
            context["key_business_context"] = (
                _short_text(context_text, len(context_text) // 2)
                if len(context_text) > 10
                else ""
            )
        elif context["top_kpis"]:
            context["top_kpis"].pop()
        elif context["top_risks"]:
            context["top_risks"].pop()
        elif context["top_actions"]:
            context["top_actions"].pop()
        elif context["root_causes"]:
            context["root_causes"].pop()
        else:
            context["financial_summary"] = _short_text(context["financial_summary"], 600)
        serialized = json.dumps(context, ensure_ascii=False, separators=(",", ":"), default=str)
    return context


def _build_executive_prompt(executive_context: Dict[str, Any]) -> str:
    bounded_context = json.loads(json.dumps(executive_context, default=str))

    def render() -> str:
        serialized = json.dumps(
            bounded_context,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        return f"""You are an enterprise strategy advisor. Use only the summarized evidence below.

Executive context:
{serialized}

Write an executive-ready response with:
- executive_summary: what changed, why it matters, severity, and a clear leadership recommendation
- causal_analysis: explain the likely business chain and its evidence; distinguish the causal path from existing problems
- current_business_context: one concise paragraph
- business_impact: material enterprise consequences
- financial_impact: separate current exposure from incremental scenario estimates; do not imply causation
- operational_impact: evidence-supported operational consequences
- key_risks: restate only the selected risks supplied in executive context
- recommended_response: restate only the selected actions supplied in executive context
- executive_conclusion: concise decision-oriented conclusion

Treat root causes and the supplied category-based impact path as hypotheses, not proven facts.
Use supplied confidence and assumptions; do not extend the causal path beyond supplied evidence.
When a monetary estimate is present, explain its matched KPI baseline, calculation, and assumptions.
Connect the user's scenario to the likely business consequence and the supplied impact path in the executive summary.
Keep executive_summary under 120 words. Do not invent monetary amounts, causal relationships, business facts, or actions. Do not mention KPI counts,
record counts, node counts, or workflow information. Avoid telemetry, raw JSON, and
repetition. Keep the whole response under 250 words.
Return only a JSON object with the requested fields."""

    prompt = render()
    while _estimate_tokens(prompt) > 2800:
        for field in ("top_risks", "top_actions", "root_causes", "top_kpis"):
            if bounded_context.get(field):
                bounded_context[field].pop()
                break
        else:
            context_text = bounded_context.get("key_business_context", "")
            if context_text:
                bounded_context["key_business_context"] = (
                    _short_text(context_text, len(context_text) // 2)
                    if len(context_text) > 10
                    else ""
                )
            else:
                financial = bounded_context.get("financial_summary", {})
                if isinstance(financial, dict):
                    financial["scenario_exposure"] = {}
                    financial["current_exposure"] = []
                    financial["combined_outlook"] = {}
                else:
                    bounded_context["financial_summary"] = ""
        prompt = render()
    return prompt


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(
            text for item in value
            if (text := _coerce_text(item))
        )
    if isinstance(value, dict):
        return "\n".join(
            f"{key}: {text}"
            for key, item in value.items()
            if (text := _coerce_text(item))
        )
    return str(value)


def _coerce_text_list(value: Any) -> List[str]:
    values = value if isinstance(value, list) else [value]
    return [
        text for item in values
        if (text := _coerce_text(item))
    ]


def _normalize_explanation_payload(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, ExplanationResult):
        payload = payload.model_dump()
    if not isinstance(payload, dict):
        raise TypeError("The explanation response must be a JSON object.")

    normalized = dict(payload)
    for field in _TEXT_FIELDS:
        normalized[field] = _coerce_text(normalized.get(field))
    for field in _LIST_FIELDS:
        normalized[field] = _coerce_text_list(normalized.get(field))
    return normalized


def _word_limited(explanation: Dict[str, Any], max_words: int = 400) -> Dict[str, Any]:
    fields = (
        "executive_summary",
        "current_business_context",
        "business_impact",
        "financial_impact",
        "operational_impact",
        "key_risks",
        "recommended_response",
        "executive_conclusion",
        "key_drivers",
        "risk_explanation",
        "recommendation_rationale",
    )
    remaining = max_words
    for field in fields:
        value = explanation.get(field)
        if isinstance(value, list):
            limited_items = []
            for item in value:
                words = str(item).split()
                if not remaining:
                    break
                limited_items.append(" ".join(words[:remaining]))
                remaining -= min(len(words), remaining)
            explanation[field] = limited_items
        elif isinstance(value, str):
            limited_lines = []
            for line in value.splitlines() or [value]:
                words = line.split()
                if not remaining:
                    break
                limited_lines.append(" ".join(words[:remaining]))
                remaining -= min(len(words), remaining)
            explanation[field] = "\n".join(limited_lines)
    return explanation


def _complete_explanation(payload: Dict[str, Any]) -> Dict[str, Any]:
    explanation = dict(payload)
    explanation.setdefault("current_business_context", "")
    explanation.setdefault("financial_impact", "")
    explanation.setdefault("operational_impact", "")
    explanation.setdefault("key_risks", explanation.get("key_drivers", []))
    explanation.setdefault("recommended_response", explanation.get("recommendation_rationale", ""))
    explanation.setdefault("executive_conclusion", "")
    if not explanation.get("key_drivers"):
        explanation["key_drivers"] = explanation.get("key_risks", [])[:3]
    if not explanation.get("risk_explanation"):
        explanation["risk_explanation"] = "See the key risks for material exposures."
    if not explanation.get("recommendation_rationale"):
        explanation["recommendation_rationale"] = "See the recommended response."
    return _word_limited(explanation)


class ExplainabilityService:
    """Create a concise, executive-focused narrative grounded in workflow evidence."""

    def __init__(self, llm_service: Optional[LLMGateway] = None):
        self.llm_service = llm_service or LLMGateway.get_service()

    async def explain(
        self,
        scenario_or_state: Union[Dict[str, Any], Any],
        semantic_entities: Optional[List[Dict[str, Any]]] = None,
        simulation_result: Optional[Dict[str, Any]] = None,
        impact_result: Optional[Dict[str, Any]] = None,
        recommendations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate an executive narrative from the workflow state or legacy arguments."""
        state: Dict[str, Any] = {}
        if isinstance(scenario_or_state, dict) and "simulation_result" in scenario_or_state:
            state = scenario_or_state
            scenario = state.get("scenario", {})
            sim_res = state.get("simulation_result", {})
            imp_res = state.get("impact_result", {})
        else:
            scenario = scenario_or_state if isinstance(scenario_or_state, dict) else {}
            sim_res = simulation_result or {}
            imp_res = impact_result or {}

        metrics = sim_res.get("metrics", {})
        selected_kpi_items = (
            ([state["primary_kpi"]] if isinstance(state.get("primary_kpi"), dict) else [])
            + [
                item
                for item in state.get("supporting_kpis", [])
                if isinstance(item, dict)
            ]
        )
        top_kpis = [
            {
                "name": item.get("name"),
                "value": item.get("value"),
                "reasoning": item.get("why_it_matters") or item.get("evidence"),
                "confidence": item.get("confidence"),
            }
            for item in selected_kpi_items
        ]
        top_actions = [
            {
                "title": item.get("title") or item.get("action_title") or item.get("action"),
                "priority": item.get("priority"),
                "rationale": item.get("business_benefit") or item.get("expected_outcome"),
            }
            for item in state.get("selected_actions", [])
            if isinstance(item, dict)
        ]

        probability = metrics.get("impact_probability")
        probability_description = self._likelihood_description(probability)
        if not state:
            state = {
                "query": scenario.get("description") or scenario.get("query", ""),
                "scenario": scenario,
                "impact_result": imp_res,
                "simulation_result": sim_res,
                "selected_actions": [],
            }
        executive_context = build_executive_context(state)
        prompt = _build_executive_prompt(executive_context)
        system_instruction = (
            "You are an enterprise strategy advisor writing for senior decision-makers. "
            "Be precise, evidence-based, concise, and commercially focused. Return only valid JSON."
        )
        try:
            if self.llm_service.is_configured:
                raw_result = await self.llm_service.generate_json(
                    prompt=prompt,
                    system_instruction=system_instruction,
                )
                normalized_result = _normalize_explanation_payload(raw_result)
                normalized_result = self._preserve_selected_decisions(
                    normalized_result,
                    state,
                )
                result = ExplanationResult.model_validate(normalized_result).model_dump()
                return _complete_explanation(result)
            logger.warning(
                "[ExplainabilityService] No LLM provider is configured; using an evidence-based fallback narrative."
            )
            return self._fallback(
                state=state,
                scenario=scenario,
                impact=imp_res,
                kpis=top_kpis,
                actions=top_actions,
                probability_description=probability_description,
            )
        except Exception as exc:
            logger.error(
                "[ExplainabilityService] Executive narrative generation failed: %s",
                exc,
                exc_info=True,
            )
            return self._fallback(
                state=state,
                scenario=scenario,
                impact=imp_res,
                kpis=top_kpis,
                actions=top_actions,
                probability_description=probability_description,
            )

    @staticmethod
    def _likelihood_description(probability: Any) -> str:
        try:
            value = float(probability)
        except (TypeError, ValueError):
            return "not quantified"
        if value < 0.1:
            return "low likelihood"
        if value < 0.35:
            return "moderate likelihood"
        if value < 0.65:
            return "high likelihood"
        return "very high likelihood"

    def _fallback(
        self,
        state: Dict[str, Any],
        scenario: Dict[str, Any],
        impact: Dict[str, Any],
        kpis: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        probability_description: str,
    ) -> Dict[str, Any]:
        query = state.get("query") or scenario.get("description") or "The requested scenario"
        current_context = self._context_summary(state.get("matched_dashboard_records", []))
        severity = str(impact.get("overall_severity") or "Unclassified").capitalize()
        causal = impact.get("causal_analysis", {})
        if not isinstance(causal, dict):
            causal = {}
        causal_path = causal.get("primary_impact_path")
        if not causal_path and isinstance(causal.get("causal_chain"), list):
            causal_path = " → ".join(map(str, causal["causal_chain"]))

        simulation_result = state.get("simulation_result", {})
        if not isinstance(simulation_result, dict):
            simulation_result = {}
        financial_model = impact.get("financial_model") or simulation_result.get(
            "financial_model", {}
        )
        if not isinstance(financial_model, dict):
            financial_model = {}
        existing_model = financial_model.get(
            "current_exposure",
            financial_model.get("existing_enterprise_exposure", {}),
        )
        existing_items = existing_model.get("items", []) if isinstance(existing_model, dict) else []
        scenario_model = financial_model.get(
            "scenario_exposure",
            financial_model.get("scenario_incremental_exposure", {}),
        )
        financial_parts = []
        if existing_items:
            financial_parts.append(
                "Current enterprise exposure includes "
                + "; ".join(
                    f"{item.get('name')}: {item.get('formatted_amount')}"
                    for item in existing_items[:3]
                    if isinstance(item, dict)
                )
                + ". These are existing indicators, not scenario losses."
            )
        if isinstance(scenario_model, dict):
            severity_label = scenario_model.get("severity", "UNQUANTIFIED")
            confidence_label = float(scenario_model.get("confidence", 0.0) or 0.0)
            amounts = scenario_model.get("estimated_amount_by_currency", {})
            amount_summary = (
                "; ".join(
                    f"{currency} {amount:,.2f}"
                    for currency, amount in amounts.items()
                )
                if isinstance(amounts, dict) and amounts
                else "no monetary increment was quantified"
            )
            drivers = scenario_model.get("impact_drivers", [])
            driver_summary = "; ".join(
                f"{item.get('kpi')} ({item.get('category')})"
                for item in drivers[:3]
                if isinstance(item, dict)
            ) if isinstance(drivers, list) else ""
            financial_parts.append(
                f"Scenario impact is assessed as {severity_label} severity "
                f"({confidence_label:.0%} confidence): {amount_summary}."
                + (f" Principal drivers are {driver_summary}." if driver_summary else "")
                + " Estimates are evidence-based indicators, not realized losses."
            )
            amount_evidence = scenario_model.get("amount_evidence", [])
            if isinstance(amount_evidence, list):
                for evidence in amount_evidence[:2]:
                    if not isinstance(evidence, dict):
                        continue
                    financial_parts.append(
                        f"Estimate basis: {evidence.get('why', 'Matched monetary KPI evidence')} "
                        f"Calculation: {evidence.get('derivation', 'Proportional scenario estimate')}."
                    )
                    assumptions = evidence.get("assumptions", [])
                    if assumptions:
                        financial_parts.append(
                            "Estimate assumptions: " + "; ".join(map(str, assumptions[:2])) + "."
                        )
            reasoning = scenario_model.get("financial_reasoning")
            if reasoning:
                financial_parts.append(str(reasoning))
        else:
            financial_parts.append(
                "Scenario-attributable impact is not quantified; current enterprise exposures "
                "are not treated as scenario losses."
            )

        risk_items = [
            f"{risk.get('name')}: {risk.get('business_impact') or risk.get('reason') or ''}".strip()
            for risk in (state.get("primary_risk"), state.get("secondary_risk"))
            if isinstance(risk, dict) and risk.get("name")
        ]
        graph_data = state.get("knowledge_graph_data", {})
        if not isinstance(graph_data, dict):
            graph_data = {}
        related_entities = state.get("related_entities") or graph_data.get(
            "related_entities", []
        )
        dependency_paths = state.get("dependency_paths") or graph_data.get(
            "dependency_paths", []
        )
        root_causes = impact.get("root_cause_analysis", [])
        causal_analysis = impact.get("causal_analysis", {})
        if not isinstance(causal_analysis, dict):
            causal_analysis = {}
        causal_path = causal_analysis.get("primary_impact_path")
        if not causal_path and isinstance(causal_analysis.get("causal_chain"), list):
            causal_path = " → ".join(map(str, causal_analysis["causal_chain"]))
        business_consequence = causal_analysis.get("business_consequence")
        related_names = [
            str(item.get("name") or item.get("entity_name"))
            for item in related_entities
            if isinstance(item, dict) and (item.get("name") or item.get("entity_name"))
        ] if isinstance(related_entities, list) else []
        path_summaries = []
        if isinstance(dependency_paths, list):
            for path in dependency_paths[:3]:
                if isinstance(path, dict) and isinstance(path.get("entities"), list):
                    path_summaries.append(" -> ".join(map(str, path["entities"])))
        graph_summary = state.get("graph_summary") or graph_data.get("graph_summary", {})
        if not isinstance(graph_summary, dict):
            graph_summary = {}
        graph_nodes = graph_summary.get(
            "total_nodes",
            graph_data.get(
                "total_nodes",
                len(graph_data.get("nodes", []))
                if isinstance(graph_data.get("nodes"), list)
                else 0,
            ),
        )
        graph_edges = graph_summary.get(
            "total_edges",
            graph_data.get(
                "total_edges",
                len(graph_data.get("edges", []))
                if isinstance(graph_data.get("edges"), list)
                else 0,
            ),
        )
        graph_available = bool(
            graph_summary.get("graph_exists") is not False
            and isinstance(graph_nodes, (int, float))
            and isinstance(graph_edges, (int, float))
            and graph_nodes > 0
            and graph_edges > 0
        )
        if not risk_items:
            risk_items = []
        response_items = [
            str(action["title"])
            for action in actions
            if isinstance(action, dict) and action.get("title")
        ]
        kpi_context = "; ".join(
            f"{item['name']}: {item['value']}" for item in kpis[:3]
        )
        business_impact = (
            f"{business_consequence or 'The scenario may affect business performance through the assessed impact pathway.'} "
            f"{'Relevant indicators include ' + kpi_context + '.' if kpi_context else 'Assess downstream effects against current operating priorities.'}"
            f"{' Graph-linked entities include ' + ', '.join(related_names[:5]) + '.' if related_names and graph_available else ''}"
        )
        graph_impact = (
            f" The graph identifies {len(related_names)} related entities and "
            f"{len(path_summaries)} dependency paths in the supplied topology."
            f"{' Representative path: ' + path_summaries[0] + '.' if path_summaries else ''}"
            if graph_available and (related_names or path_summaries)
            else (
                " Knowledge Graph data is currently unavailable for this scenario."
                if not graph_available
                else ""
            )
        )
        operational_impact = (
            f"There is a {probability_description} of operational pressure under this scenario. "
            "Leadership should validate resource capacity, process dependencies, and commitments "
            "supported by the available evidence."
            f"{graph_impact}"
        )
        recommended_response = "; ".join(response_items[:5]) or "No action was selected."
        conclusion = f"Overall impact is assessed as {severity}. Prioritize evidence-based mitigation and monitor the indicators most relevant to the scenario."
        result = {
            "executive_summary": (
                f"{query} may lead to {business_consequence or 'downstream business consequences'}"
                + (f" through {causal_path}. " if causal_path else ". ")
                + f"The overall impact is assessed as {severity.casefold()}. "
                + (
                    f"A potential contributing factor is {root_causes[0].get('root_cause')}; "
                    if root_causes and isinstance(root_causes[0], dict)
                    else ""
                )
                + (
                    "Leadership should prioritize the selected mitigation actions."
                    if response_items
                    else "No mitigation action was selected."
                )
            ),
            "current_business_context": current_context or "No directly matched business context was available.",
            "business_impact": business_impact,
            "financial_impact": " ".join(financial_parts),
            "operational_impact": operational_impact,
            "key_risks": risk_items[:5],
            "recommended_response": recommended_response,
            "executive_conclusion": conclusion,
            "key_drivers": risk_items[:3],
            "risk_explanation": "See the key risks for material exposures.",
            "recommendation_rationale": "See the recommended response.",
        }
        return _word_limited(result, max_words=300)

    @staticmethod
    def _preserve_selected_decisions(
        explanation: Dict[str, Any],
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        risks = [
            item
            for item in (state.get("primary_risk"), state.get("secondary_risk"))
            if isinstance(item, dict)
        ]
        actions = [
            item
            for item in state.get("selected_actions", [])
            if isinstance(item, dict)
        ]
        risk_statements = [
            f"{item.get('name')}: {item.get('business_impact') or item.get('reason') or ''}".strip()
            for item in risks
            if item.get("name")
        ]
        action_statements = [
            str(item.get("title") or item.get("action_title") or item.get("action"))
            for item in actions
            if item.get("title") or item.get("action_title") or item.get("action")
        ]
        explanation["key_risks"] = risk_statements
        explanation["key_drivers"] = [item.get("name") for item in risks if item.get("name")]
        explanation["risk_explanation"] = "; ".join(risk_statements)
        explanation["recommended_response"] = (
            "; ".join(action_statements) or "No action was selected."
        )
        explanation["recommendation_rationale"] = explanation["recommended_response"]
        return explanation

    @staticmethod
    def _number(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _context_summary(records: Any) -> str:
        if not isinstance(records, list):
            return ""
        summaries = []
        for record in records[:3]:
            if not isinstance(record, dict):
                summaries.append(str(record))
                continue
            facts = []
            for key, value in list(record.items())[:8]:
                if isinstance(value, (str, int, float)) and value not in ("", None):
                    label = str(key).replace("_", " ")
                    display_value = str(value)
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", display_value):
                        try:
                            display_value = datetime.strptime(
                                display_value, "%Y-%m-%d"
                            ).strftime("%d %B %Y").lstrip("0")
                        except ValueError:
                            pass
                    facts.append(f"{label}: {display_value}")
            if facts:
                summaries.append("; ".join(facts))
        return " ".join(summaries)
