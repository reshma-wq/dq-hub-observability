from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Rule(BaseModel):
    rule_name: str
    column_name: str
    description: str
    sql_condition: str

class RuleRegistrationRequest(BaseModel):
    table_name: str
    rules: List[Rule]

class TemplateRuleRequest(BaseModel):
    """Request model for creating template-based rules"""
    table_name: str
    column_name: str
    rule_type: str
    description: str
    placeholder_values: Optional[Dict[str, Any]] = None
