# Chado Studio

Multi-agent swarm for DAO decision support. Synthesis Hackathon 2026 submission.

## Tracks

1. **Protocol Labs "Let the Agent Cook"** — DAO proposal analysis, impact simulation, voting recommendations
2. **Olas Pearl** — crvUSD yield optimizer

## Architecture

```
Orchestrator
  ├── Proposal Analyzer  — parse & extract governance proposals
  ├── Impact Simulator   — model voting outcomes & treasury impact
  ├── Recommender        — synthesize analysis into actionable recommendation
  └── Yield Optimizer    — crvUSD yield monitoring (Olas track)
```

ERC-8004 identity on Base chain. Execution logs for trust verification.

## Run

```bash
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8716
```

## API

- `GET /health` — healthcheck
- `GET /api/v1/status` — agent status
- `POST /api/v1/analyze` — analyze a governance proposal

## ERC-8004

- IdentityRegistry: `0x8004A818BFB912233c491871b3d84c89A494BD9e` (Base)
- ReputationRegistry: `0x8004B663056A597Dffe9eCcC1965A193B7388713` (Base)

## License

MIT
