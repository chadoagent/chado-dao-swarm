import importlib


def test_imports():
    """All modules importable without errors."""
    modules = [
        "src.config",
        "src.utils.logging",
        "src.agents.proposal_analyzer",
        "src.agents.impact_simulator",
        "src.agents.recommender",
        "src.agents.yield_optimizer",
        "src.agents.orchestrator",
        "src.registry.erc8004",
        "src.main",
    ]
    for mod in modules:
        importlib.import_module(mod)


def test_config_defaults():
    from src.config import Settings
    s = Settings()
    assert s.chain_id == 8453
    assert s.port == 8716
    assert "8004" in s.identity_registry


def test_execution_logger():
    from src.utils.logging import ExecutionLogger
    logger = ExecutionLogger()
    entry = logger.start("test_action", {"key": "value"})
    assert entry["status"] == "running"
    logger.end(entry, {"result": True})
    assert entry["status"] == "ok"
    assert entry["duration_ms"] >= 0
    assert len(logger.get_logs()) == 1


def test_agent_status():
    from src.agents.orchestrator import Orchestrator
    o = Orchestrator()
    status = o.agent_status()
    assert status["orchestrator"] == "ready"
    assert "proposal_analyzer" in status
