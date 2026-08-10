from agents.base_agent import BaseAgent
from prompts.security_prompt import SECURITY_PROMPT


class SecurityAgent(BaseAgent):

    def __init__(self, api_key: str = None, model: str = None):
        super().__init__(skill_folder="security", api_key=api_key, model=model)

    def analyze(self, repo: str):
        prompt = f"""
{SECURITY_PROMPT}

Target Repository:
{repo}
"""
        return self.create_interaction(
            prompt=prompt,
            repository=repo,
        )