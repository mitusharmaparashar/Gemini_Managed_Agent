from agents.base_agent import BaseAgent
from prompts.architecture_prompt import ARCHITECTURE_PROMPT


class ArchitectureAgent(BaseAgent):

    def __init__(self, api_key: str = None, model: str = None):
        super().__init__(skill_folder="architecture", api_key=api_key, model=model)

    def analyze(self, repo: str):
        prompt = f"""
{ARCHITECTURE_PROMPT}

Target Repository:
{repo}
"""
        return self.create_interaction(
            prompt=prompt,
            repository=repo,
        )