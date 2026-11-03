from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RuleResponse(BaseModel):
    rule_id: str
    name: str
    nl_description: str
    rule_type: str
    category: str
    severity: str
    target_entity: str
    executable_logic: Dict[str, Any] = Field(default_factory=dict)
    sql_query: Optional[str] = None
    semantic_query: Optional[str] = None
    graph_query: Optional[str] = None
    status: str = "active"
    created_by: str = "api_user"
    created_at: str = ""
    updated_at: str = ""
    trigger_count: int = 0
    actions: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class RuleListResponse(BaseModel):
    rules: List[RuleResponse] = Field(default_factory=list)
    total: int
    filters: Optional[Dict[str, Any]] = None


class RuleExplanationResponse(BaseModel):
    rule_id: str
    explanation: str
    breakdown: Optional[Dict[str, Any]] = None


class CompileRuleRequest(BaseModel):
    nl_description: str
    created_by: str = "api_user"


class CompileRuleResponse(BaseModel):
    success: bool
    rule: Optional[RuleResponse] = None
    error: Optional[str] = None
    message: Optional[str] = None