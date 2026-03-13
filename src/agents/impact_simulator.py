from __future__ import annotations


class ImpactSimulator:
    """Models voting outcomes and treasury/protocol impact."""

    async def run(self, proposal: dict) -> dict:
        return {
            "vote_distribution": {
                "for": 0.0,
                "against": 0.0,
                "abstain": 0.0,
            },
            "quorum_met": False,
            "treasury_impact_usd": 0.0,
            "risk_score": 0.0,
            "affected_pools": [],
            "parameter_deltas": [],
        }

    def status(self) -> str:
        return "ready"
