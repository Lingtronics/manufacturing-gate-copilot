from dataclasses import dataclass
import os


@dataclass
class Settings:
    database_path: str = "data/copilot.sqlite3"
    app_mode: str = "demo"
    miro_mode: str = "mock"
    allow_live_miro: bool = False
    miro_token: str = ""
    miro_board: str = "mock-northstar"
    llm_enabled: bool = False
    llm_model: str = "llama3.2:1b"
    llm_timeout_seconds: float = 30
    demo_allow_private_clients: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_path=os.getenv("DATABASE_PATH", "data/copilot.sqlite3"),
            app_mode=os.getenv("APP_MODE", "demo"),
            miro_mode=os.getenv("MIRO_MODE", "mock"),
            allow_live_miro=os.getenv("ALLOW_LIVE_MIRO", "false").lower() == "true",
            miro_token=os.getenv("MIRO_OAUTH_TOKEN", ""),
            miro_board=os.getenv("MIRO_BOARD_ID", "mock-northstar"),
            llm_enabled=os.getenv("LLM_ENABLED", "false").lower() == "true",
            llm_model=os.getenv("LLM_MODEL", "llama3.2:1b"),
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            demo_allow_private_clients=os.getenv("DEMO_ALLOW_PRIVATE_CLIENTS", "false").lower() == "true",
        )
