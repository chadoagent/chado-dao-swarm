from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "CHADO_", "env_file": ".env"}

    # API keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Chain config (Base)
    chain_name: str = "base"
    rpc_url: str = "https://mainnet.base.org"
    chain_id: int = 8453

    # ERC-8004 contracts
    identity_registry: str = "0x8004A818BFB912233c491871b3d84c89A494BD9e"
    reputation_registry: str = "0x8004B663056A597Dffe9eCcC1965A193B7388713"

    # Agent identity
    agent_uri: str = "https://chado.studio/agent.json"
    private_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8716


settings = Settings()
