from typing import Any, Dict, List, Optional, TypedDict


class SimulationState(TypedDict, total=False):
    """
    SimulationState carries the evolving scenario context through all LangGraph nodes.
    Maintains raw & canonical domain discoveries, analytics, and final executive report.
    """
    query: str
    include_full_state: bool
    access_token: Optional[str]
    enterprise_id: str
    domain_ids: List[str]
    scope_id: Optional[str]
    dashboard_id: str
    context: Dict[str, Any]
    scenario: Dict[str, Any]
    scenario_context: Dict[str, Any]
    scenario_semantics: Dict[str, Any]
    primary_business_entity: Optional[str]
    dashboard_data: Dict[str, Any]
    dashboard_definition: Dict[str, Any]
    dashboard_rows: List[Any]
    dashboard_context: Dict[str, Any]
    dashboard_semantics: Dict[str, Any]
    dashboard_category: str
    allowed_kpi_groups: List[str]
    allowed_risk_groups: List[str]
    allowed_action_groups: List[str]
    allowed_kpi_terms: List[str]
    selected_dashboard_kpi_names: List[str]
    dashboard_kpi_records: List[Dict[str, Any]]
    dashboard_widget_kpis: List[Dict[str, Any]]
    causal_support_kpis: List[Dict[str, Any]]
    strict_dashboard_filter: bool
    matched_dashboard_records: List[Any]
    entity_match_summary: Dict[str, Any]
    kpi_insights: Dict[str, Any]
    primary_kpi: Dict[str, Any]
    supporting_kpis: List[Dict[str, Any]]
    risk_context: Dict[str, Any]
    primary_risk: Dict[str, Any]
    secondary_risk: Optional[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    action_stats: Dict[str, Any]
    selected_actions: List[Dict[str, Any]]
    available_actions: List[Dict[str, Any]]
    investment_prioritization: List[Dict[str, Any]]
    financial_reasoning: Dict[str, Any]
    investment_prioritization: List[Dict[str, Any]]
    semantic_entities: List[Dict[str, Any]]
    knowledge_graph_data: Dict[str, Any]
    graph_summary: Dict[str, Any]
    related_entities: List[Dict[str, Any]]
    dependency_paths: List[Dict[str, Any]]
    blast_radius: Dict[str, Any]
    root_cause_candidates: List[Dict[str, Any]]
    compiled_rules: Dict[str, Any]
    rules: List[Dict[str, Any]]
    strategy: str
    simulation_strategy_context: Dict[str, Any]
    semantic_reasoning: Dict[str, Any]
    vendors: List[Dict[str, Any]]
    procurement_data: Dict[str, Any]
    invoice_data: Dict[str, Any]
    expense_data: Dict[str, Any]
    market_risk_data: Dict[str, Any]
    simulation_result: Dict[str, Any]
    impact_result: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    explanation: Dict[str, Any]
    final_report: Dict[str, Any]
    

    # Operational lifecycle metadata
    current_node: Optional[str]
    status: Optional[str]
    error: Optional[str]