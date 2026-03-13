from __future__ import annotations


class Recommender:
    """Synthesizes analysis and simulation into an actionable recommendation."""

    async def run(self, data: dict) -> dict:
        proposal = data.get("proposal", {})
        simulation = data.get("simulation", {})

        return {
            "recommendation": "abstain",
            "confidence": 0.0,
            "analysis": {
                "summary": proposal.get("summary", ""),
                "risk_score": simulation.get("risk_score", 0.0),
                "treasury_impact_usd": simulation.get("treasury_impact_usd", 0.0),
                "rationale": "",
            },
        }

    def status(self) -> str:
        return "ready"
