from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

SNAPSHOT_GQL = "https://hub.snapshot.org/graphql"

SNAPSHOT_PROPOSAL_QUERY = """
query Proposal($id: String!) {
  proposal(id: $id) {
    id
    title
    body
    choices
    start
    end
    state
    scores
    space { id name }
  }
}
"""

SNAPSHOT_LIST_QUERY = """
query Proposals($space: String!, $first: Int!) {
  proposals(
    where: {space_in: [$space]},
    first: $first,
    orderBy: "created",
    orderDirection: desc
  ) {
    id
    title
    body
    choices
    start
    end
    state
    scores
  }
}
"""

ANALYSIS_PROMPT = """You are a DeFi governance analyst specializing in Curve Finance.
Analyze this governance proposal and return a JSON object with exactly these fields:

- "summary": 2-3 sentence plain-English summary of what the proposal does
- "actions": list of strings describing concrete actions (e.g. "Add gauge for pool X", "Change fee to 0.04%")
- "parameters_changed": list of objects {"parameter": str, "old_value": str|null, "new_value": str} for any protocol parameter changes
- "risk_flags": list of strings describing potential risks (e.g. "New unaudited pool", "Large emission increase")
- "affected_pools": list of pool names/addresses mentioned

If a field has no items, use an empty list. Return ONLY valid JSON, no markdown fences.

Proposal title: {title}
Proposal text:
{body}"""


class ProposalAnalyzer:
    """Parses governance proposals and extracts structured data via Snapshot API + Claude."""

    def __init__(self) -> None:
        self._api_key = settings.anthropic_api_key

    async def run(self, task: dict) -> dict:
        proposal_text = task.get("proposal_text", "")
        proposal_url = task.get("proposal_url")
        title = task.get("title", "")
        metadata: dict[str, Any] = {}

        # Fetch from Snapshot if URL provided
        if proposal_url and not proposal_text:
            fetched = await self._fetch_proposal(proposal_url)
            proposal_text = fetched.get("body", "")
            title = title or fetched.get("title", "")
            metadata = fetched

        if not proposal_text:
            return self._empty_result(task, error="No proposal text provided")

        # Analyze with Claude
        analysis = await self._analyze_with_claude(title, proposal_text)

        return {
            "raw_text": proposal_text[:2000],
            "title": title,
            "protocol": task.get("protocol", "curve"),
            "metadata": metadata,
            **analysis,
        }

    async def list_recent(self, space: str = "curve.eth", count: int = 5) -> list[dict]:
        """Fetch recent proposals from Snapshot for a given space."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                SNAPSHOT_GQL,
                json={
                    "query": SNAPSHOT_LIST_QUERY,
                    "variables": {"space": space, "first": count},
                },
            )
            resp.raise_for_status()
            data = resp.json()
        proposals = data.get("data", {}).get("proposals", [])
        return [
            {
                "id": p["id"],
                "title": p["title"],
                "state": p["state"],
                "choices": p["choices"],
                "scores": p["scores"],
            }
            for p in proposals
        ]

    async def _fetch_proposal(self, url: str) -> dict[str, Any]:
        """Fetch proposal by Snapshot URL or raw proposal ID."""
        proposal_id = self._extract_proposal_id(url)
        if proposal_id:
            return await self._fetch_snapshot_proposal(proposal_id)

        # Fallback: treat as raw URL, fetch HTML/text
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return {"body": resp.text, "title": "", "source": "raw_url"}

    async def _fetch_snapshot_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Fetch a single proposal from Snapshot GraphQL."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                SNAPSHOT_GQL,
                json={
                    "query": SNAPSHOT_PROPOSAL_QUERY,
                    "variables": {"id": proposal_id},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        proposal = data.get("data", {}).get("proposal")
        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        return {
            "id": proposal["id"],
            "title": proposal["title"],
            "body": proposal["body"],
            "choices": proposal["choices"],
            "state": proposal["state"],
            "scores": proposal["scores"],
            "start": proposal["start"],
            "end": proposal["end"],
            "space": proposal.get("space", {}).get("id", ""),
            "source": "snapshot",
        }

    async def _analyze_with_claude(self, title: str, body: str) -> dict[str, Any]:
        """Send proposal text to Claude API for structured analysis."""
        if not self._api_key:
            logger.warning("No Anthropic API key configured, returning empty analysis")
            return self._empty_analysis()

        # Truncate body to avoid excessive token usage
        truncated_body = body[:8000]
        prompt = ANALYSIS_PROMPT.format(title=title, body=truncated_body)

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
                        "max_tokens": 1024,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            raw_text = data["content"][0]["text"]
            return self._parse_analysis_json(raw_text)

        except httpx.HTTPStatusError as e:
            logger.error("Claude API error: %s %s", e.response.status_code, e.response.text[:200])
            return self._empty_analysis(error=f"Claude API {e.response.status_code}")
        except Exception as e:
            logger.error("Analysis failed: %s", e)
            return self._empty_analysis(error=str(e))

    @staticmethod
    def _parse_analysis_json(raw: str) -> dict[str, Any]:
        """Parse JSON from Claude response, handling markdown fences."""
        cleaned = raw.strip()
        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Claude response as JSON: %s", raw[:200])
            return ProposalAnalyzer._empty_analysis(error="JSON parse failed")

        # Validate expected keys
        return {
            "summary": parsed.get("summary", ""),
            "actions": parsed.get("actions", []),
            "parameters_changed": parsed.get("parameters_changed", []),
            "risk_flags": parsed.get("risk_flags", []),
            "affected_pools": parsed.get("affected_pools", []),
        }

    @staticmethod
    def _extract_proposal_id(url: str) -> str | None:
        """Extract Snapshot proposal ID from URL or return as-is if it looks like an ID."""
        # Direct ID (0x-prefixed hash)
        if url.startswith("0x") and len(url) >= 60:
            return url

        # Snapshot URL: https://snapshot.org/#/curve.eth/proposal/0x...
        m = re.search(r"proposal/(0x[a-fA-F0-9]+)", url)
        if m:
            return m.group(1)

        return None

    @staticmethod
    def _empty_analysis(error: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "summary": "",
            "actions": [],
            "parameters_changed": [],
            "risk_flags": [],
            "affected_pools": [],
        }
        if error:
            result["error"] = error
        return result

    @staticmethod
    def _empty_result(task: dict, error: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "raw_text": "",
            "title": "",
            "protocol": task.get("protocol", "curve"),
            "metadata": {},
            "summary": "",
            "actions": [],
            "parameters_changed": [],
            "risk_flags": [],
            "affected_pools": [],
        }
        if error:
            result["error"] = error
        return result

    def status(self) -> str:
        return "ready" if self._api_key else "no_api_key"
