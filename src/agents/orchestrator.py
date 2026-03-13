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
        rec = await self.recommender.run({
            "proposal": proposal,
            "simulation": simulation,
            "protocol": task.get("protocol", "curve"),
        })

        return {
            "recommendation": rec.get("recommendation", "abstain"),
            "confidence": rec.get("confidence", 0.0),
            "analysis": {
                "summary": proposal.get("summary", ""),
                "rationale": rec.get("rationale", ""),
                "key_risks": rec.get("key_risks", []),
                "key_benefits": rec.get("key_benefits", []),
                "risk_score": simulation.get("risk_score", 0.0),
                "treasury_impact_usd": simulation.get("treasury_impact_usd", 0.0),
                "vote_distribution": simulation.get("vote_distribution", {}),
                "quorum_met": simulation.get("quorum_met"),
                "affected_pools": proposal.get("affected_pools", []),
                "parameters_changed": proposal.get("parameters_changed", []),
            },
        }

    def agent_status(self) -> dict:
        return {
            "orchestrator": "ready",
            "proposal_analyzer": self.analyzer.status(),
            "impact_simulator": self.simulator.status(),
            "recommender": self.recommender.status(),
        }
