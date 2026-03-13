from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SNAPSHOT_GQL = "https://hub.snapshot.org/graphql"

VOTES_QUERY = """
query Votes($proposal: String!, $first: Int!) {
  votes(
    where: {proposal: $proposal},
    first: $first,
    orderBy: "vp",
    orderDirection: desc
  ) {
    voter
    choice
    vp
  }
}
"""


class ImpactSimulator:
    """Models voting outcomes and treasury/protocol impact.

    Fetches actual vote data from Snapshot, calculates distributions,
    quorum status, and estimates risk based on proposal parameters.
    """

    # Known quorum thresholds (veCRV voting power)
    QUORUM_THRESHOLDS = {
        "curve.eth": 15_000_000,  # ~15M veCRV
        "aave.eth": 320_000,  # ~320K AAVE
    }

    # Risk weights for different parameter types
    RISK_WEIGHTS = {
        "fee": 0.3,
        "gauge": 0.4,
        "emission": 0.7,
        "treasury": 0.8,
        "upgrade": 0.9,
        "default": 0.5,
    }

    async def run(self, proposal: dict) -> dict:
        """Simulate impact of a governance proposal.

        Args:
            proposal: Output from ProposalAnalyzer with keys:
                - metadata.id: Snapshot proposal ID
                - metadata.space: Snapshot space
                - metadata.scores: Current vote scores
                - metadata.choices: Vote choices
                - actions, parameters_changed, risk_flags, affected_pools
        """
        metadata = proposal.get("metadata", {})
        proposal_id = metadata.get("id", "")
        space = metadata.get("space", "curve.eth")
        scores = metadata.get("scores", [])
        choices = metadata.get("choices", [])

        # Fetch top voters if we have a proposal ID
        top_voters = []
        if proposal_id:
            top_voters = await self._fetch_top_voters(proposal_id)

        # Calculate vote distribution
        vote_dist = self._calc_vote_distribution(scores, choices)
        total_vp = sum(scores) if scores else sum(v.get("vp", 0) for v in top_voters)

        # Check quorum
        quorum_threshold = self.QUORUM_THRESHOLDS.get(space, 0)
        quorum_met = total_vp >= quorum_threshold if quorum_threshold else None

        # Estimate risk
        risk_score = self._calc_risk_score(proposal)

        # Estimate treasury impact from parameter changes
        treasury_impact = self._estimate_treasury_impact(proposal)

        return {
            "vote_distribution": vote_dist,
            "total_voting_power": total_vp,
            "quorum_met": quorum_met,
            "quorum_threshold": quorum_threshold,
            "top_voters": top_voters[:10],
            "treasury_impact_usd": treasury_impact,
            "risk_score": risk_score,
            "affected_pools": proposal.get("affected_pools", []),
            "parameter_deltas": proposal.get("parameters_changed", []),
            "risk_flags": proposal.get("risk_flags", []),
        }

    async def _fetch_top_voters(
        self, proposal_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Fetch top voters by voting power from Snapshot."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    SNAPSHOT_GQL,
                    json={
                        "query": VOTES_QUERY,
                        "variables": {"proposal": proposal_id, "first": limit},
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            votes = data.get("data", {}).get("votes", [])
            return [
                {
                    "voter": v["voter"],
                    "choice": v["choice"],
                    "vp": v["vp"],
                }
                for v in votes
            ]
        except Exception as exc:
            logger.error("Failed to fetch voters for %s: %s", proposal_id, exc)
            return []

    @staticmethod
    def _calc_vote_distribution(
        scores: list[float], choices: list[str]
    ) -> dict[str, float]:
        """Calculate percentage distribution across vote choices."""
        if not scores:
            return {"for": 0.0, "against": 0.0, "abstain": 0.0}

        total = sum(scores)
        if total == 0:
            return {"for": 0.0, "against": 0.0, "abstain": 0.0}

        dist = {}
        for i, choice in enumerate(choices):
            key = choice.lower().strip()
            pct = (scores[i] / total * 100) if i < len(scores) else 0.0
            dist[key] = round(pct, 2)

        # Ensure standard keys exist
        for key in ("for", "against", "abstain"):
            if key not in dist:
                # Try to match similar keys
                for k, v in dist.items():
                    if key in k or k in key:
                        dist[key] = v
                        break
                else:
                    dist.setdefault(key, 0.0)

        return dist

    def _calc_risk_score(self, proposal: dict) -> float:
        """Calculate 0-1 risk score based on proposal content."""
        risk_flags = proposal.get("risk_flags", [])
        params_changed = proposal.get("parameters_changed", [])

        if not risk_flags and not params_changed:
            return 0.1  # minimal risk for info-only proposals

        score = 0.0
        count = 0

        # Weight by risk flag keywords
        for flag in risk_flags:
            flag_lower = flag.lower()
            weight = self.RISK_WEIGHTS["default"]
            for keyword, w in self.RISK_WEIGHTS.items():
                if keyword in flag_lower:
                    weight = max(weight, w)
            score += weight
            count += 1

        # Weight by number of parameter changes
        for param in params_changed:
            param_name = str(param.get("parameter", "")).lower()
            weight = self.RISK_WEIGHTS["default"]
            for keyword, w in self.RISK_WEIGHTS.items():
                if keyword in param_name:
                    weight = max(weight, w)
            score += weight
            count += 1

        return round(min(score / max(count, 1), 1.0), 3)

    @staticmethod
    def _estimate_treasury_impact(proposal: dict) -> float:
        """Rough USD estimate of treasury impact from parameter changes.

        Returns 0 if no meaningful estimate can be made.
        """
        params = proposal.get("parameters_changed", [])
        if not params:
            return 0.0

        # Simple heuristic: count significant changes
        # Real implementation would query on-chain TVL/volume data
        significant = sum(
            1
            for p in params
            if p.get("new_value") and p.get("old_value") != p.get("new_value")
        )
        # Placeholder: each significant param change ~$10K-$100K impact range
        return significant * 50_000.0 if significant else 0.0

    def status(self) -> str:
        return "ready"
