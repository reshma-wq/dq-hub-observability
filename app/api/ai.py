from fastapi import APIRouter

from app.services.ai_service import AIService

router = APIRouter()

service = AIService()


@router.post("/generate/{table_name}")
@router.post("/generate/{table_name}/")
def generate_rules(table_name: str):

    return service.generate_rules(table_name)