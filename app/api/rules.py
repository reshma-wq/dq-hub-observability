from fastapi import APIRouter

from app.services.rule_service import RuleService
from app.models.rule_models import RuleRegistrationRequest, Rule
from app.utils.config import TARGET_DATASET

router = APIRouter()

service = RuleService()

@router.get("/{table_name}")
def get_rules(table_name: str):

    return service.get_rules(
        TARGET_DATASET,
        table_name
    )

@router.post("/")
def register_rules(
    request: RuleRegistrationRequest
):
    # Substitute placeholder values BEFORE passing to service
    processed_rules = []
    
    for rule in request.rules:
        sql_condition = rule.sql_condition
        
        print(f"\n=== API LAYER ===")
        print(f"Original condition: {sql_condition}")
        print(f"min_val: {rule.min_val}, max_val: {rule.max_val}")
        print(f"in_values: {rule.in_values}, pattern_val: {rule.pattern_val}")
        
        # Substitute min/max for BETWEEN
        if rule.min_val:
            print(f"Substituting <min> with {rule.min_val}")
            sql_condition = sql_condition.replace('<min>', str(rule.min_val))
        if rule.max_val:
            print(f"Substituting <max> with {rule.max_val}")
            sql_condition = sql_condition.replace('<max>', str(rule.max_val))
        
        # Substitute values for IN
        if rule.in_values:
            vals = [f"'{v.strip()}'" for v in rule.in_values.split(',')]
            quoted = ','.join(vals)
            print(f"Substituting <values> with {quoted}")
            sql_condition = sql_condition.replace('<values>', quoted)
        
        # Substitute pattern for REGEX
        if rule.pattern_val:
            print(f"Substituting <pattern> with {rule.pattern_val}")
            sql_condition = sql_condition.replace('<pattern>', str(rule.pattern_val))
        
        print(f"Final condition: {sql_condition}")
        
        # Create new rule with substituted condition
        processed_rule = Rule(
            rule_name=rule.rule_name,
            column_name=rule.column_name,
            description=rule.description,
            sql_condition=sql_condition,
            min_val=rule.min_val,
            max_val=rule.max_val,
            in_values=rule.in_values,
            pattern_val=rule.pattern_val
        )
        processed_rules.append(processed_rule)

    return service.register_rules(
        request.table_name,
        processed_rules
    )