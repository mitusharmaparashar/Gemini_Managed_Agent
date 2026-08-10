from services.gemini_service import GeminiService

client = GeminiService.client()

previous_id = input("Interaction ID: ")

try:
    interaction = client.interactions.create(
        agent="antigravity-preview-05-2026",
        input="Summarize the repository in one paragraph.",
        previous_interaction_id=previous_id,
    )

    print(interaction.output_text)

except Exception as e:
    import traceback
    traceback.print_exc()