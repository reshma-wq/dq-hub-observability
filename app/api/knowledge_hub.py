from fastapi import APIRouter

from app.services.ai_service import AIService

router = APIRouter()


@router.post("/sync")
def sync_knowledge_hub():

    service = AIService()

    result = (
        service.onboard_new_tables_to_knowledge_hub()
    ) or {
        "new_tables_found": 0
    }

    return {
        "status": "success",
        "message":
            f"{result['new_tables_found']} new tables synchronized"
    }