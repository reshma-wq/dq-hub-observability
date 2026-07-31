from fastapi import APIRouter, Body

from app.services.rule_service import RuleService
from app.services.ai_service import AIService
from app.models.rule_models import RuleRegistrationRequest, PreviewRequest
from app.utils.config import TARGET_DATASET

router = APIRouter()

service = RuleService()
ai_service = AIService()

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
    return service.preview_data(
        request.table_name,
        request.sql_condition
    )

@router.post("/trigger-scan/{table_name}")
def trigger_scan(table_name: str):
    trigger_result = service.trigger_scan(table_name)
    
    if trigger_result["status"] == "error":
        return trigger_result
    
    wait_result = service.wait_for_scan_completion(table_name)
    
    return wait_result

@router.post("/anomalies/generate/{table_name}")
def generate_anomalies(table_name: str):
    """Generate AI-suggested anomalies for a table"""
    return ai_service.generate_anomalies(table_name)

@router.post("/anomalies/register")
def register_anomalies(request: dict = Body(...)):
    """Register selected anomalies for a table"""
    table_name = request.get("table_name")
    anomalies = request.get("anomalies", [])
    return service.register_anomalies(table_name, anomalies)

@router.get("/profile/{table_name}/{column_name}")
def get_column_profile(table_name: str, column_name: str):
    return service.get_column_profile(table_name, column_name)

@router.get("/profile/{table_name}")
def get_table_profile(table_name: str):
    return service.get_table_profile(table_name)

@router.get("/{table_name}")
def get_rules(table_name: str):

    return service.get_rules(
        TARGET_DATASET,
        table_name
    )