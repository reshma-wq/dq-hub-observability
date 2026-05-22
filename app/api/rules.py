from fastapi import APIRouter

from app.services.rule_service import RuleService
from app.models.rule_models import RuleRegistrationRequest
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

    return service.register_rules(
        request.table_name,
        request.rules
    )