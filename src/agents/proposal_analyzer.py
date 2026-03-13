from __future__ import annotations

import httpx


class ProposalAnalyzer:
    """Parses governance proposals and extracts structured data."""

    async def run(self, task: dict) -> dict:
        proposal_text = task.get("proposal_text", "")
        proposal_url = task.get("proposal_url")

        if proposal_url and not proposal_text:
            proposal_text = await self._fetch_proposal(proposal_url)

        return {
            "raw_text": proposal_text,
            "protocol": task.get("protocol", "curve"),
            "summary": "",
            "actions": [],
            "parameters_changed": [],
            "risk_flags": [],
        }

    async def _fetch_proposal(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    def status(self) -> str:
        return "ready"
