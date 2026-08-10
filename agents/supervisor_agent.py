import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.repository_agent import RepositoryAgent
from agents.architecture_agent import ArchitectureAgent
from agents.security_agent import SecurityAgent
from agents.documentation_agent import DocumentationAgent


class SupervisorAgent:

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key
        self.model = model
        self.agent_classes = {
            "Repository": RepositoryAgent,
            "Architecture": ArchitectureAgent,
            "Security": SecurityAgent,
            "Documentation": DocumentationAgent,
        }

    def _run_single_agent(self, agent_name: str, repo: str):
        start_time = time.time()
        agent_cls = self.agent_classes.get(agent_name)
        if not agent_cls:
            return agent_name, {
                "output": f"❌ Unknown agent: {agent_name}",
                "environment_id": "",
                "interaction_id": "",
                "duration": 0,
            }

        try:
            agent = agent_cls(api_key=self.api_key, model=self.model)
            interaction = agent.analyze(repo)
            duration = round(time.time() - start_time, 2)
            return agent_name, {
                "output": getattr(interaction, "output_text", str(interaction)),
                "environment_id": getattr(interaction, "environment_id", ""),
                "interaction_id": getattr(interaction, "id", ""),
                "duration": duration,
            }
        except Exception as e:
            duration = round(time.time() - start_time, 2)
            return agent_name, {
                "output": f"❌ Error executing {agent_name} agent:\n\n`{str(e)}`",
                "environment_id": "",
                "interaction_id": "",
                "duration": duration,
            }

    def run(self, selected_agents: list, repo: str, parallel: bool = True):
        results = {}

        if parallel and len(selected_agents) > 1:
            with ThreadPoolExecutor(max_workers=min(len(selected_agents), 4)) as executor:
                future_to_agent = {
                    executor.submit(self._run_single_agent, name, repo): name
                    for name in selected_agents
                    if name in self.agent_classes
                }
                for future in as_completed(future_to_agent):
                    agent_name, result = future.result()
                    results[agent_name] = result
        else:
            for agent_name in selected_agents:
                if agent_name in self.agent_classes:
                    _, result = self._run_single_agent(agent_name, repo)
                    results[agent_name] = result

        return results