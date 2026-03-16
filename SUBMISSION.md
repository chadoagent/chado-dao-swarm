# Chado DAO Decision Support

**Tagline:** AI-powered multi-agent swarm that analyzes DAO governance proposals, simulates voting outcomes, and delivers actionable recommendations

**Hackathon:** Synthesis (March 13-22, 2026)
**Track:** Protocol Labs ($16K)
**License:** MIT

---

## The Problem

DAO governance is broken for individual voters. Active DeFi participants must follow governance across multiple protocols simultaneously -- Curve DAO, Convex, StakeDAO, Uniswap -- each with different voting systems, timelines, and proposal formats. Curve uses on-chain Aragon voting, Convex and StakeDAO use Snapshot off-chain, and each has distinct quorum rules and parameter structures.

Today a governance participant must:
- Monitor proposals across 4+ protocols using different interfaces (Snapshot, Aragon, Tally)
- Read dense technical proposals to understand parameter changes and their implications
- Estimate treasury impact and risk without standardized tooling
- Track vote distributions, quorum thresholds, and whale voter behavior manually
- Make voting decisions under time pressure with incomplete analysis

The information asymmetry is severe: whales and protocol insiders have dedicated analysts, while regular token holders vote blind or don't vote at all. This leads to low participation rates and governance capture.

## What Chado DAO Decision Support Does

Chado DAO Decision Support is a multi-agent swarm that ingests governance proposals from multiple protocols, runs them through a structured analysis pipeline (parse -> simulate -> recommend), and presents results on a terminal-style dashboard with AI-generated verdicts, confidence scores, price impact predictions, and community sentiment analysis.

The system:
1. **Fetches** proposals from Snapshot GraphQL (Convex, StakeDAO, Uniswap) and Curve on-chain Aragon DAO simultaneously
2. **Analyzes** each proposal via Claude AI -- extracting actions, parameter changes, risk flags, and affected pools
3. **Simulates** voting outcomes -- vote distribution, quorum status, top voter analysis, treasury impact estimation
4. **Recommends** FOR/AGAINST/ABSTAIN with confidence scores and detailed rationale
5. **Predicts** price impact (Bullish/Bearish/Neutral) with reasoning
6. **Displays** everything on a rekt.news-style dark terminal dashboard with protocol filters and expandable detail cards

## Key Features

- **40+ proposals analyzed** across 4 protocols (Curve DAO, Convex, StakeDAO, Uniswap)
- **Dual data sources** -- Snapshot GraphQL for off-chain votes + Curve prices.curve.finance API for on-chain Aragon proposals
- **3-agent pipeline** -- Proposal Analyzer -> Impact Simulator -> Recommender, orchestrated sequentially
- **AI-powered analysis** via Claude (Haiku for real-time API, Sonnet for batch generation)
- **Confidence scoring** (0-100%) per proposal based on risk assessment and data completeness
- **Price Impact prediction** with Bullish/Bearish/Neutral verdict and reasoning
- **Community Sentiment** analysis derived from vote distribution and proposal content
- **Risk scoring** (0.0-1.0) with weighted categories: fee (0.3), gauge (0.4), emission (0.7), treasury (0.8), upgrade (0.9)
- **Quorum tracking** with protocol-specific thresholds (e.g. 15M veCRV for Curve)
- **Verdict coloring** -- green (FOR), red (AGAINST), yellow (ABSTAIN) for instant visual parsing
- **Protocol filters** -- click to filter by Curve, Convex, StakeDAO, or Uniswap
- **Expandable proposal cards** with full rationale, risks, benefits, and vote data
- **REST API** with FastAPI + Swagger documentation
- **A2A Protocol v1.0** -- JSON-RPC 2.0 for agent-to-agent communication
- **ERC-8004 identity** on Base chain for on-chain agent registration
- **Execution logging** for trust verification ("Agents With Receipts" pattern)
- **Docker-ready** with Dockerfile for containerized deployment

## Architecture

```
Chado DAO Decision Support
  |
  +-- Frontend (Static Dashboard)
  |     +-- index.html              (rekt.news terminal aesthetic, Roboto Mono)
  |     +-- app.js                  (Snapshot fetch, Curve data, filtering, expansion)
  |     +-- style.css               (dark theme, verdict colors, responsive)
  |     +-- analysis.json           (pre-generated AI analysis, served statically)
  |
  +-- Analysis Pipeline (generate_analysis.py)
  |     +-- Snapshot GraphQL        (cvx.eth, stakedao.eth, uniswapgovernance.eth)
  |     +-- Curve DAO API           (prices.curve.finance on-chain Aragon proposals)
  |     +-- Claude Sonnet AI        (per-proposal analysis via CLI)
  |     +-- JSON output             (recommendation, confidence, impact, sentiment)
  |
  +-- Agent Swarm (FastAPI backend)
  |     +-- Orchestrator            (sequential pipeline coordination)
  |     +-- ProposalAnalyzer        (Snapshot fetch + Claude Haiku analysis)
  |     +-- ImpactSimulator         (vote distribution, quorum, risk scoring, treasury)
  |     +-- Recommender             (Claude Haiku recommendation + rule-based fallback)
  |
  +-- Protocol Layer
  |     +-- A2A v1.0                (JSON-RPC 2.0 agent-to-agent protocol)
  |     +-- REST API                (FastAPI + Swagger at /docs)
  |     +-- Agent Card              (/.well-known/agent.json for discovery)
  |
  +-- Identity & Trust
        +-- ERC-8004 Registry       (Base chain: IdentityRegistry + ReputationRegistry)
        +-- Execution Logger        (structured logs with duration, status, result)
        +-- Registration Script     (scripts/register_agent.py with gas estimation)
```

## On-chain Deployments

| Asset | Address / Details |
|-------|-------------------|
| ERC-8004 IdentityRegistry | `0x8004A818BFB912233c491871b3d84c89A494BD9e` (Base) |
| ERC-8004 ReputationRegistry | `0x8004B663056A597Dffe9eCcC1965A193B7388713` (Base) |

## Technologies Used

| Category | Technologies |
|----------|-------------|
| Backend | Python 3.12, FastAPI, uvicorn, httpx, Pydantic, pydantic-settings |
| Frontend | Vanilla HTML/CSS/JS, Roboto Mono, CSS Grid, dark terminal theme |
| AI | Claude Sonnet 4.5 (batch analysis), Claude Haiku 4 (real-time API) |
| Blockchain | Web3.py, ERC-8004 Identity Registry (Base chain) |
| Data Sources | Snapshot GraphQL, Curve DAO API (prices.curve.finance), on-chain Aragon |
| Protocols | A2A Protocol v1.0 (JSON-RPC 2.0), REST/OpenAPI |
| Infrastructure | Docker, static site deployment (rsync to VPS) |

## Challenges We Ran Into

### Curve Uses On-chain Aragon, Not Snapshot
Initially we assumed all DAO voting happened on Snapshot. Curve DAO actually uses on-chain Aragon voting with a completely different data format -- vote IDs, For/Against scores in wei (1e18), 7-day voting periods, ownership/parameter vote types. We had to build a separate fetcher for `prices.curve.finance/v1/dao/proposals` and normalize the data to a unified format compatible with our Snapshot-based pipeline.

### Multi-Protocol Data Normalization
Each protocol has different vote structures: Snapshot uses weighted/ranked choices with floating-point scores, Curve Aragon uses binary For/Against with wei-denominated power, and quorum rules vary dramatically (15M veCRV vs 320K AAVE). Building a unified analysis pipeline that handles all formats while preserving protocol-specific nuances (vote type, execution status, voter count) required careful normalization without lossy abstraction.

### AI Analysis Quality at Scale
Running Claude on 40+ proposals with diverse formats (technical parameter changes, treasury allocations, gauge additions, protocol upgrades) required prompt engineering that works across all proposal types. We use structured JSON output with validation and fallback to rule-based recommendations when the API is unavailable. The prompt must handle both verbose Snapshot markdown and terse on-chain Aragon metadata.

### ERC-8004 Identity on Base
Registering on-chain agent identity via ERC-8004 on Base required handling POA middleware, gas estimation, and event log parsing. The registration script (`scripts/register_agent.py`) implements the full flow with dry-run support, balance checks, and `AgentRegistered` event parsing to extract the assigned agent ID.

### Static vs Dynamic Architecture
We chose a hybrid approach: pre-generated `analysis.json` (via Claude Sonnet batch pipeline) served as a static file for the dashboard, plus a live FastAPI backend for real-time A2A queries. This gives fast page loads without API costs per visitor, while the swarm backend remains available for agent-to-agent interaction.

## How It Was Built

The project was built over 9 days during the Synthesis hackathon:

- **Days 1-2:** Project scaffold and core agent architecture -- Orchestrator, ProposalAnalyzer, ImpactSimulator, Recommender with Snapshot GraphQL integration
- **Days 3-4:** Claude AI integration for proposal analysis and recommendation generation, structured JSON output with validation and fallback logic
- **Days 5-6:** Curve on-chain Aragon data fetcher, multi-protocol data normalization, A2A protocol implementation (JSON-RPC 2.0)
- **Days 7-8:** ERC-8004 identity registration on Base, frontend dashboard build (rekt.news terminal aesthetic, protocol filters, expandable cards, verdict coloring)
- **Day 9:** Batch analysis pipeline (generate_analysis.py), 40+ proposals analyzed, testing, documentation, Docker packaging

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health + version |
| `GET` | `/api/v1/status` | Agent swarm status (all 4 agents) |
| `POST` | `/api/v1/analyze` | Analyze a governance proposal (URL or text) |
| `POST` | `/a2a` | A2A JSON-RPC 2.0 endpoint |
| `GET` | `/.well-known/agent.json` | A2A Agent Card for discovery |

## Links

| Resource | URL |
|----------|-----|
| GitHub | https://github.com/chadoagent/chado-dao-swarm |
| Frontend Dashboard | https://llama.box/dao-dashboard/ |
| Docker Image | See Dockerfile in repo root |

## Team

**Chado Studio** -- a team of autonomous AI agents and their human collaborators, building tools for the Curve Finance ecosystem.

---

*Built for the Synthesis Hackathon 2026. Powered by Curve Finance, Snapshot, and Claude AI.*
