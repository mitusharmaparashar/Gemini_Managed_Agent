from services.gemini_service import GeminiService

client = GeminiService.client()

interaction_id = input("Interaction ID: ")

interaction = client.interactions.get(interaction_id)

print("=" * 80)

print(type(interaction))

print("=" * 80)

print(dir(interaction))