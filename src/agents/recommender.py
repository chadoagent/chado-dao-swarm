from __future__ import annotations

import json
import logging
import re

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

RECOMMENDATION_PROMPT = """You are a DeFi governance advisor for {protocol}.
Given the proposal analysis and impact simulation below, provide a voting recommendation.

Return ONLY valid JSON with these fields:
- "recommendation": one of "for", "against", "abstain"
- "confidence": float 0.0-1.0 (how confident in the recommendation)
- "rationale": 2-4 sentences explaining why
- "key_risks": list of top 1-3 risks (strings)
- "key_benefits": list of top 1-3 benefits (strings)

Proposal Analysis:
- Title: {title}
- Summary: {summary}
- Actions: {actions}
- Parameters Changed: {parameters}
- Risk Flags: {risk_flags}
- Affected Pools: {affected_pools}

Impact Simulation:
- Vote Distribution: {vote_dist}
- Total Voting Power: {total_vp}
- Quorum Met: {quorum_met}
- Risk Score: {risk_score}/1.0
- Treasury Impact: ${treasury_impact:,.0f}

Provide your recommendation as JSON only."""


class Recommender:
    """Synthesizes analysis and simulation into an actionable recommendation.

    Uses Claude API to generate a structured recommendation based on
    ProposalAnalyzer output and ImpactSimulator results.
    """

    def __init__(self) -> None:
        self._api_key = settings.anthropic_api_key

    async def run(self, data: dict) -> dict:
        """Generate recommendation from proposal analysis + simulation.

        Args:
            data: dict with keys:
                - proposal: ProposalAnalyzer output
                - simulation: ImpactSimulator output
                - protocol: e.g. "curve"
        """
        proposal = data.get("proposal", {})
        simulation = data.get("simulation", {})
        protocol = data.get("protocol", "curve")

        # Build recommendation via Claude if API key available
        if self._api_key:
            recommendation = await self._recommend_with_claude(
                proposal, simulation, protocol
            )
        else:
            recommendation = self._rule_based_recommendation(proposal, simulation)

        # Attach source data summary
        recommendation["source"] = {
            "proposal_title": proposal.get("title", ""),
            "protocol": protocol,
            "risk_score": simulation.get("risk_score", 0.0),
            "treasury_impact_usd": simulation.get("treasury_impact_usd", 0.0),
            "quorum_met": simulation.get("quorum_met"),
            "total_voting_power": simulation.get("total_voting_power", 0),
        }

        return recommendation

    async def _recommend_with_claude(
        self, proposal: dict, simulation: dict, protocol: str
    ) -> dict:
        """Generate recommendation using Claude API."""
        prompt = RECOMMENDATION_PROMPT.format(
            protocol=protocol,
            title=proposal.get("title", "Unknown"),
            summary=proposal.get("summary", "No summary available"),
            actions=json.dumps(proposal.get("actions", []))[:500],
            parameters=json.dumps(proposal.get("parameters_changed", []))[:500],
            risk_flags=json.dumps(proposal.get("risk_flags", []))[:300],
            affected_pools=json.dumps(proposal.get("affected_pools", []))[:300],
            vote_dist=json.dumps(simulation.get("vote_distribution", {})),
            total_vp=simulation.get("total_voting_power", 0),
            quorum_met=simulation.get("quorum_met", "unknown"),
            risk_score=simulation.get("risk_score", 0.0),
            treasury_impact=simulation.get("treasury_impact_usd", 0.0),
        )

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-4-20250514",
                        "max_tokens": 512,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            raw = data["content"][0]["text"]
            return self._parse_recommendation(raw)

        except httpx.HTTPStatusError as e:
            logger.error(
                "Claude API error: %s %s",
                e.response.status_code,
                e.response.text[:200],
            )
            return self._rule_based_recommendation(proposal, simulation)
        except Exception as e:
            logger.error("Recommendation failed: %s", e)
            return self._rule_based_recommendation(proposal, simulation)

    @staticmethod
    def _parse_recommendation(raw: str) -> dict:
        """Parse JSON recommendation from Claude response."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse recommendation JSON: %s", raw[:200])
            return {
                "recommendation": "abstain",
                "confidence": 0.0,
                "rationale": "Could not generate recommendation (parse error)",
                "key_risks": [],
                "key_benefits": [],
            }

        valid_recs = {"for", "against", "abstain"}
        rec = str(parsed.get("recommendation", "abstain")).lower()
        if rec not in valid_recs:
            rec = "abstain"

        return {
            "recommendation": rec,
            "confidence": min(max(float(parsed.get("confidence", 0.0)), 0.0), 1.0),
            "rationale": parsed.get("rationale", ""),
            "key_risks": parsed.get("key_risks", []),
            "key_benefits": parsed.get("key_benefits", []),
        }

    @staticmethod
    def _rule_based_recommendation(proposal: dict, simulation: dict) -> dict:
        """Fallback rule-based recommendation when no API key."""
        risk_score = simulation.get("risk_score", 0.5)
        risk_flags = proposal.get("risk_flags", [])

        if risk_score >= 0.8:
            rec, confidence = "against", 0.7
            rationale = f"High risk score ({risk_score:.2f}). {len(risk_flags)} risk flags identified."
        elif risk_score >= 0.5:
            rec, confidence = "abstain", 0.5
            rationale = f"Moderate risk ({risk_score:.2f}). Recommend further review before voting."
        else:
            rec, confidence = "for", 0.6
            rationale = f"Low risk ({risk_score:.2f}). No significant concerns identified."

        return {
            "recommendation": rec,
            "confidence": confidence,
            "rationale": rationale,
            "key_risks": risk_flags[:3],
            "key_benefits": proposal.get("actions", [])[:3],
        }

    def status(self) -> str:
        return "ready" if self._api_key else "no_api_key_fallback_rules"
