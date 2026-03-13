from __future__ import annotations

import httpx


class YieldOptimizer:
    """crvUSD yield monitoring and optimization for Olas Pearl track."""

    CURVE_API = "https://prices.curve.finance"

    async def run(self, task: dict) -> dict:
        pools = await self._fetch_crvusd_pools()

        return {
            "pools": pools,
            "best_yield": max(pools, key=lambda p: p["apy"]) if pools else None,
            "strategy": "hold",
            "rebalance_needed": False,
        }

    async def _fetch_crvusd_pools(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{self.CURVE_API}/v1/crvusd/markets/ethereum")
                resp.raise_for_status()
                data = resp.json().get("data", [])
                return [
                    {
                        "name": m.get("name", ""),
                        "address": m.get("address", ""),
                        "apy": float(m.get("lend_apy", 0)),
                        "tvl": float(m.get("total_debt", 0)),
                    }
                    for m in data
                ]
        except Exception:
            return []

    def status(self) -> str:
        return "ready"
