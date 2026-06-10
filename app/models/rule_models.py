from pydantic import BaseModel
from typing import List, Optional

class Rule(BaseModel):
    rule_name: str
    column_name: str
    description: str
    sql_condition: str
    # Template rule specific fields
    min_val: Optional[str] = None
    max_val: Optional[str] = None
    in_values: Optional[str] = None
    pattern_val: Optional[str] = None

class RuleRegistrationRequest(BaseModel):
    table_name: str
    rules: List[Rule]