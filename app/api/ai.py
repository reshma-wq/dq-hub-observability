from fastapi import APIRouter

from app.services.ai_service import AIService

router = APIRouter()


@router.post("/generate/{table_name}")
@router.post("/generate/{table_name}/")
def generate_rules(table_name: str):

    service = AIService()

    return service.generate_rules(
        table_name
    )