from services.gemini_service import GeminiService

client = GeminiService.client()

print(dir(client.interactions))