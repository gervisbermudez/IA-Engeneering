import os
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator


class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


_MODELO_DEFAULT = {
    Provider.OPENAI: "gpt-4o-mini",
    Provider.ANTHROPIC: "claude-3-5-sonnet-20241022",
    Provider.GEMINI: "gemini-flash-latest",
}


class ChatMessage(BaseModel):
    role: str = Field(description="'user', 'assistant' o 'system'")
    content: str

    @field_validator("role")
    @classmethod
    def rol_valido(cls, v: str) -> str:
        roles_permitidos = {"user", "assistant", "system"}
        if v not in roles_permitidos:
            raise ValueError(f"role debe ser uno de {roles_permitidos}, recibido: '{v}'")
        return v


class LLMConfig(BaseModel):
    provider: Provider
    model: str
    openai_api_key: Optional[SecretStr] = None
    anthropic_api_key: Optional[SecretStr] = None
    google_api_key: Optional[SecretStr] = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, gt=0)

    @model_validator(mode="after")
    def clave_del_proveedor(self) -> "LLMConfig":
        if self.provider == Provider.OPENAI and not self.openai_api_key:
            raise ValueError("Falta openai_api_key para el proveedor openai")
        if self.provider == Provider.ANTHROPIC and not self.anthropic_api_key:
            raise ValueError("Falta anthropic_api_key para el proveedor anthropic")
        if self.provider == Provider.GEMINI and not self.google_api_key:
            raise ValueError("Falta google_api_key para el proveedor gemini")
        return self

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Arma la config desde .env: LLM_PROVIDER elige el cliente del factory."""
        raw = os.getenv("LLM_PROVIDER", "openai").strip().lower()
        try:
            provider = Provider(raw)
        except ValueError as e:
            raise ValueError(
                f"LLM_PROVIDER inválido: {raw!r}. Use openai, anthropic o gemini."
            ) from e

        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")
        return cls(
            provider=provider,
            model=_MODELO_DEFAULT[provider],
            openai_api_key=SecretStr(openai_key) if openai_key else None,
            anthropic_api_key=SecretStr(anthropic_key) if anthropic_key else None,
            google_api_key=SecretStr(google_key) if google_key else None,
        )


class ModelResponse(BaseModel):
    provider: Provider
    model: str
    content: str
    error: Optional[str] = None
