from agents.base_agent import BaseAgent
from prompts.documentation_prompt import DOCUMENTATION_PROMPT


class DocumentationAgent(BaseAgent):

    def __init__(self, api_key: str = None, model: str = None):
        super().__init__(skill_folder="documentation", api_key=api_key, model=model)

    def analyze(self, repo: str):
        prompt = f"""
{DOCUMENTATION_PROMPT}

Target Repository:
{repo}
"""
        return self.create_interaction(
            prompt=prompt,
            repository=repo,
        )