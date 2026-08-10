from pathlib import Path
import os
from config import MODEL
from services.gemini_service import GeminiService


class BaseAgent:

    def __init__(self, skill_folder: str = None, api_key: str = None, model: str = None):
        self.api_key = api_key
        self.client = GeminiService.client(api_key=api_key)
        self.model = model or MODEL
        self.skill_folder = skill_folder
        self.skill = ""

        if skill_folder:
            base_dir = Path(__file__).resolve().parent.parent
            skill_path = base_dir / "skills" / skill_folder / "SKILL.md"

            if skill_path.exists():
                self.skill = skill_path.read_text(encoding="utf-8")

    def clean_repo_url(self, repository: str) -> str:
        repository = repository.strip()
        if repository.endswith(".git"):
            repository = repository[:-4]
        if "/tree/" in repository:
            repository = repository.split("/tree/")[0]
        return repository

    def create_interaction(
        self,
        prompt: str,
        repository: str = None,
        previous_interaction_id: str = None,
        extra_sources: list = None,
    ):
        sources = []

        if repository:
            clean_repo = self.clean_repo_url(repository)
            sources.append({
                "type": "repository",
                "source": clean_repo,
                "target": "/workspace/repo",
            })

        if self.skill_folder and self.skill:
            sources.append({
                "type": "inline",
                "target": f".agents/skills/{self.skill_folder}/SKILL.md",
                "content": self.skill,
            })

        if extra_sources:
            sources.extend(extra_sources)

        kwargs = {
            "input": prompt,
        }

        # Differentiate between agent (e.g. antigravity-preview-05-2026) vs model (e.g. gemini-2.5-flash)
        model_str = (self.model or "").lower()
        if "gemini" in model_str and "preview" not in model_str:
            kwargs["model"] = self.model
        else:
            kwargs["agent"] = self.model

        if previous_interaction_id:
            kwargs["previous_interaction_id"] = previous_interaction_id

        # Environment is mandatory in interactions.create API
        kwargs["environment"] = {
            "type": "remote",
            "sources": sources,
        }

        return self.client.interactions.create(**kwargs)