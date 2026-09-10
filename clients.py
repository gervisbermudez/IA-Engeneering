from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, List, Optional

from anthropic import (
    APIConnectionError as AnthropicConnectionError,
    APIError as AnthropicAPIError,
    AsyncAnthropic,
    RateLimitError as AnthropicRateLimitError,
)
from google import genai
from google.genai import types
try:
    from google.genai.errors import APIError as GeminiAPIError
    from google.genai.errors import ClientError as GeminiClientError
except ImportError:  # google-genai muy antiguo
    GeminiAPIError = Exception
    GeminiClientError = Exception
from openai import (
    APIConnectionError as OpenAIConnectionError,
    APIError as OpenAIAPIError,
    AsyncOpenAI,
    RateLimitError as OpenAIRateLimitError,
)

from schemas import ChatMessage, LLMConfig, ModelResponse, Provider


def _separar_system(messages: List[ChatMessage]) -> tuple[Optional[str], List[ChatMessage]]:
    """Anthropic y Gemini no aceptan role=system dentro de messages."""
    system_parts = [m.content for m in messages if m.role == "system"]
    resto = [m for m in messages if m.role != "system"]
    system = "\n\n".join(system_parts) if system_parts else None
    return system, resto


class BaseLLMClient(ABC):
    """Contrato común: cualquier proveedor implementa generate y generate_stream."""

    @abstractmethod
    async def generate(self, messages: List[ChatMessage]) -> ModelResponse:
        raise NotImplementedError

    @abstractmethod
    async def generate_stream(self, messages: List[ChatMessage]) -> AsyncGenerator[str, None]:
        raise NotImplementedError
        yield


class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate(self, messages: List[ChatMessage]) -> ModelResponse:
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[m.model_dump() for m in messages],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            if not response.choices:
                return ModelResponse(
                    provider=Provider.OPENAI,
                    model=self.model,
                    content="",
                    error="La API de OpenAI no devolvió choices",
                )
            content = response.choices[0].message.content or ""
            return ModelResponse(provider=Provider.OPENAI, model=self.model, content=content)
        except OpenAIRateLimitError as e:
            return ModelResponse(
                provider=Provider.OPENAI,
                model=self.model,
                content="",
                error=f"Límite de cuota excedido: {e}",
            )
        except OpenAIConnectionError as e:
            return ModelResponse(
                provider=Provider.OPENAI,
                model=self.model,
                content="",
                error=f"Error de conexión: {e}",
            )
        except OpenAIAPIError as e:
            return ModelResponse(
                provider=Provider.OPENAI,
                model=self.model,
                content="",
                error=f"Error de la API de OpenAI: {e}",
            )
        except Exception as e:
            return ModelResponse(
                provider=Provider.OPENAI,
                model=self.model,
                content="",
                error=f"Error inesperado de OpenAI: {e}",
            )

    async def generate_stream(self, messages: List[ChatMessage]) -> AsyncGenerator[str, None]:
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=[m.model_dump() for m in messages],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except (OpenAIRateLimitError, OpenAIConnectionError, OpenAIAPIError) as e:
            yield f"\n[Error durante el streaming de OpenAI: {e}]"
        except Exception as e:
            yield f"\n[Error inesperado durante el streaming de OpenAI: {e}]"


class AnthropicClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self._client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _kwargs_mensajes(self, messages: List[ChatMessage]) -> dict[str, Any]:
        system, resto = _separar_system(messages)
        # Anthropic acepta temperature en 0–1; el esquema unificado permite 0–2.
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": min(self.temperature, 1.0),
            "messages": [m.model_dump() for m in resto],
        }
        if system:
            payload["system"] = system
        return payload

    async def generate(self, messages: List[ChatMessage]) -> ModelResponse:
        try:
            response = await self._client.messages.create(**self._kwargs_mensajes(messages))
            content = response.content[0].text if response.content else ""
            return ModelResponse(provider=Provider.ANTHROPIC, model=self.model, content=content)
        except AnthropicRateLimitError as e:
            return ModelResponse(
                provider=Provider.ANTHROPIC,
                model=self.model,
                content="",
                error=f"Límite de cuota excedido: {e}",
            )
        except AnthropicConnectionError as e:
            return ModelResponse(
                provider=Provider.ANTHROPIC,
                model=self.model,
                content="",
                error=f"Error de conexión: {e}",
            )
        except AnthropicAPIError as e:
            return ModelResponse(
                provider=Provider.ANTHROPIC,
                model=self.model,
                content="",
                error=f"Error de la API de Anthropic: {e}",
            )
        except Exception as e:
            return ModelResponse(
                provider=Provider.ANTHROPIC,
                model=self.model,
                content="",
                error=f"Error inesperado de Anthropic: {e}",
            )

    async def generate_stream(self, messages: List[ChatMessage]) -> AsyncGenerator[str, None]:
        try:
            async with self._client.messages.stream(**self._kwargs_mensajes(messages)) as stream:
                async for texto in stream.text_stream:
                    yield texto
        except (AnthropicRateLimitError, AnthropicConnectionError, AnthropicAPIError) as e:
            yield f"\n[Error durante el streaming de Anthropic: {e}]"
        except Exception as e:
            yield f"\n[Error inesperado durante el streaming de Anthropic: {e}]"


class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _convertir_mensajes(self, messages: List[ChatMessage]):
        system, resto = _separar_system(messages)
        contents = []
        for m in resto:
            rol = "model" if m.role == "assistant" else "user"
            contents.append(types.Content(role=rol, parts=[types.Part.from_text(text=m.content)]))
        return contents, system

    def _error_gemini(self, exc: Exception) -> str:
        if isinstance(exc, GeminiClientError) and getattr(exc, "code", None) == 429:
            return f"Límite de cuota excedido: {exc}"
        if isinstance(exc, (OSError, TimeoutError, ConnectionError)):
            return f"Error de conexión: {exc}"
        if isinstance(exc, GeminiAPIError):
            return f"Error de la API de Gemini: {exc}"
        nombre = type(exc).__name__.lower()
        if "connect" in nombre or "timeout" in nombre:
            return f"Error de conexión: {exc}"
        return f"Error de la API de Gemini: {exc}"

    async def generate(self, messages: List[ChatMessage]) -> ModelResponse:
        try:
            contents, system_instruction = self._convertir_mensajes(messages)
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                    system_instruction=system_instruction,
                ),
            )
            return ModelResponse(
                provider=Provider.GEMINI,
                model=self.model,
                content=response.text or "",
            )
        except Exception as e:
            return ModelResponse(
                provider=Provider.GEMINI,
                model=self.model,
                content="",
                error=self._error_gemini(e),
            )

    async def generate_stream(self, messages: List[ChatMessage]) -> AsyncGenerator[str, None]:
        try:
            contents, system_instruction = self._convertir_mensajes(messages)
            stream = await self._client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                    system_instruction=system_instruction,
                ),
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"\n[Error durante el streaming de Gemini: {self._error_gemini(e)}]"


class AsyncLLMManager:
    """Factory: instancia OpenAI, Anthropic o Gemini según LLMConfig.provider."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client: BaseLLMClient = self._crear_cliente()

    @classmethod
    def from_env(cls) -> "AsyncLLMManager":
        """Carga el proveedor indicado por LLM_PROVIDER sin tocar código de negocio."""
        return cls(LLMConfig.from_env())

    def _crear_cliente(self) -> BaseLLMClient:
        if self.config.provider == Provider.OPENAI:
            if not self.config.openai_api_key:
                raise ValueError("Falta openai_api_key en la configuración")
            return OpenAIClient(
                api_key=self.config.openai_api_key.get_secret_value(),
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

        if self.config.provider == Provider.ANTHROPIC:
            if not self.config.anthropic_api_key:
                raise ValueError("Falta anthropic_api_key en la configuración")
            return AnthropicClient(
                api_key=self.config.anthropic_api_key.get_secret_value(),
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

        if self.config.provider == Provider.GEMINI:
            if not self.config.google_api_key:
                raise ValueError("Falta google_api_key en la configuración")
            return GeminiClient(
                api_key=self.config.google_api_key.get_secret_value(),
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

        raise ValueError(f"Proveedor no soportado: {self.config.provider}")

    async def generate(self, messages: List[ChatMessage]) -> ModelResponse:
        return await self._client.generate(messages)

    async def generate_stream(self, messages: List[ChatMessage]) -> AsyncGenerator[str, None]:
        async for chunk in self._client.generate_stream(messages):
            yield chunk
