from pydantic import BaseModel
from typing import List

class Rule(BaseModel):

    rule_name: str
    rule_category: str
    column_name: str
    description: str
    sql_condition: str

class RuleRegistrationRequest(BaseModel):
    table_name: str
    rules: List[Rule]

class PreviewRequest(BaseModel):
    table_name: str
    sql_condition: str
    