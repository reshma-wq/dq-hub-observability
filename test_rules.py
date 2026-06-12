from app.services.ai_service import AIService
import json

ai = AIService()

rules = ai.generate_rules(
    "marketing_campaigns"
)

print(
    json.dumps(
        rules,
        indent=2
    )
)