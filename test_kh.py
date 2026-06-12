from app.services.ai_service import AIService

ai = AIService()

ai.create_knowledge_hub_entry(
    "marketing_campaigns"
)

print(
    "Knowledge Hub Created"
)