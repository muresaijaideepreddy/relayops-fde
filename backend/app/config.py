"""Configuration fails closed before an application accepts requests."""

from dataclasses import dataclass, field
import json
import os


DEMO_KEYS = {
    "northstar-demo-key": {"id": "northstar", "name": "Northstar Logistics"},
    "meridian-demo-key": {"id": "meridian", "name": "Meridian Retail"},
}


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./relayops.db"
    demo_mode: bool = True
    ai_provider: str = "demo"
    openai_api_key: str = field(default="", repr=False)
    openai_model: str = ""
    tenant_api_keys: dict[str, dict[str, str]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.ai_provider not in {"demo", "openai"}:
            raise ValueError("AI_PROVIDER must be demo or openai")
        if self.ai_provider == "openai" and (
            not self.openai_api_key.strip() or not self.openai_model.strip()
        ):
            raise ValueError("OpenAI mode requires OPENAI_API_KEY and OPENAI_MODEL")
        if not self.database_url.startswith(("sqlite:", "postgresql+psycopg:")):
            raise ValueError("DATABASE_URL must use sqlite or postgresql+psycopg")
        if not self.demo_mode and not self.tenant_api_keys:
            raise ValueError("DEMO_MODE=false requires TENANT_API_KEYS")
        for key, tenant in self.tenant_api_keys.items():
            if key in DEMO_KEYS or not isinstance(key, str) or len(key) < 24:
                raise ValueError(
                    "Custom API keys must be at least 24 characters and cannot be demo keys"
                )
            if (
                not isinstance(tenant, dict)
                or set(tenant) != {"id", "name"}
                or not all(isinstance(v, str) and v.strip() for v in tenant.values())
                or len(tenant["id"]) > 80
                or len(tenant["name"]) > 200
            ):
                raise ValueError("Each TENANT_API_KEYS entry needs nonempty id and name")

    @property
    def keys(self) -> dict[str, dict[str, str]]:
        return {**(DEMO_KEYS if self.demo_mode else {}), **self.tenant_api_keys}

    @classmethod
    def from_env(cls) -> "Settings":
        raw_demo = os.getenv("DEMO_MODE", "true").lower()
        if raw_demo not in {"true", "false"}:
            raise ValueError("DEMO_MODE must be true or false")
        try:
            keys = json.loads(os.getenv("TENANT_API_KEYS", "{}"))
        except json.JSONDecodeError as exc:
            raise ValueError("TENANT_API_KEYS must be a JSON object") from exc
        if not isinstance(keys, dict):
            raise ValueError("TENANT_API_KEYS must be a JSON object")
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./relayops.db"),
            demo_mode=raw_demo == "true",
            ai_provider=os.getenv("AI_PROVIDER", "demo"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", ""),
            tenant_api_keys=keys,
        )
