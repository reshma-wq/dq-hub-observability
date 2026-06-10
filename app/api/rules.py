from fastapi import APIRouter

from app.services.rule_service import RuleService
from app.models.rule_models import RuleRegistrationRequest, TemplateRuleRequest
from app.utils.config import TARGET_DATASET

router = APIRouter()

service = RuleService()

# GET /rules/template-info/{rule_type} - get placeholder info for template type
@router.get("/template-info/{rule_type}", response_model=dict)
def get_template_info(rule_type: str):
    """
    Gets placeholder information for a template rule type.
    
    Returns placeholder fields that need to be filled by user.
    """
    info = service.get_template_info(rule_type)
    if info is None:
        return {"status": "error", "message": f"Unknown rule type: {rule_type}"}
    return info

# POST /rules/create - template rule creation (specific, won't conflict with /{table_name})
@router.post("/create", response_model=dict)
def create_template_rule(request: TemplateRuleRequest):
    """
    Creates a template-based rule and saves to BigQuery.
    """
    return service.create_template_rule(
        request.table_name,
        request.column_name,
        request.rule_type,
        request.description,
        request.placeholder_values
    )

# POST /rules/ - register multiple rules
@router.post("/", response_model=dict)
def register_rules(
    request: RuleRegistrationRequest
):
    return service.register_rules(
        request.table_name,
        request.rules
    )

# GET /rules/{table_name} - fetch rules for a table (generic, comes last)
@router.get("/{table_name}", response_model=list)
def get_rules(table_name: str):
    return service.get_rules(
        TARGET_DATASET,
        table_name
    )