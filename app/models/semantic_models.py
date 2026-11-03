from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SemanticRegistryMetadata(BaseModel):
    version: str = "1.0"
    project: Optional[str] = None
    datasets: Optional[Dict[str, str]] = None


class SemanticEntityAttribute(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False


class SemanticEntityDefinition(BaseModel):
    entity_name: str
    table_name: Optional[str] = None
    description: Optional[str] = None
    attributes: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)


class SemanticRegistryResponse(BaseModel):
    metadata: SemanticRegistryMetadata
    entities: List[Dict[str, Any]]
    entity_count: int
