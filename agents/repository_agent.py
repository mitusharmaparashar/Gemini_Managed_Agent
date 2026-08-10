from agents.base_agent import BaseAgent
from prompts.repository_prompt import REPOSITORY_PROMPT


class RepositoryAgent(BaseAgent):

    def __init__(self, api_key: str = None, model: str = None):
        super().__init__(skill_folder="repository", api_key=api_key, model=model)

    def analyze(self, repo: str):
        prompt = f"""
{REPOSITORY_PROMPT}

Target Repository:
{repo}
"""
        return self.create_interaction(
            prompt=prompt,
            repository=repo,
        )