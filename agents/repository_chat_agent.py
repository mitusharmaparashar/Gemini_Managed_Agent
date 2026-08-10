from agents.base_agent import BaseAgent
from prompts.repository_chat_prompt import REPOSITORY_CHAT_PROMPT


class RepositoryChatAgent(BaseAgent):

    def __init__(self, api_key: str = None, model: str = None):
        super().__init__(skill_folder="repository", api_key=api_key, model=model)

    def chat(self, user_question: str, repo: str = None, previous_interaction_id: str = None):
        if previous_interaction_id:
            # Continuing an existing interaction session
            prompt = user_question
            return self.create_interaction(
                prompt=prompt,
                previous_interaction_id=previous_interaction_id,
            )
        else:
            # Initializing a new chat session with repository context
            prompt = f"""
{REPOSITORY_CHAT_PROMPT}

Target Repository:
{repo}

User Question:
{user_question}
"""
            return self.create_interaction(
                prompt=prompt,
                repository=repo,
            )