from __future__ import annotations

from src.agents.proposal_analyzer import ProposalAnalyzer
from src.agents.impact_simulator import ImpactSimulator
from src.agents.recommender import Recommender


class Orchestrator:
    def __init__(self):
        self.analyzer = ProposalAnalyzer()
        self.simulator = ImpactSimulator()
        self.recommender = Recommender()

    async def run(self, task: dict) -> dict:
        # Phase 1: Parse proposal
        proposal = await self.analyzer.run(task)

        # Phase 2: Simulate impact
        simulation = await self.simulator.run(proposal)

        # Phase 3: Synthesize recommendation
        result = await self.recommender.run({
            "proposal": proposal,
            "simulation": simulation,
            "protocol": task.get("protocol", "curve"),
        })

        return result

    def agent_status(self) -> dict:
        return {
            "orchestrator": "ready",
            "proposal_analyzer": self.analyzer.status(),
            "impact_simulator": self.simulator.status(),
            "recommender": self.recommender.status(),
        }
