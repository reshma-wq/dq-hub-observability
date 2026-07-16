from fastapi import APIRouter
from pydantic import BaseModel

from app.services.rule_service import RuleService
from app.models.rule_models import RuleRegistrationRequest
from app.utils.config import TARGET_DATASET

router = APIRouter()

service = RuleService()

class PreviewRequest(BaseModel):
    table_name: str
    sql_condition: str

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

@router.post("/preview/data")
def preview_sql_condition(request: PreviewRequest):
    result = service.preview_data(
        request.table_name,
        request.sql_condition
    )
    if result.get("status") == "error":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result