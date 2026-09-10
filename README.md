# Unified Async LLM Client — Pre-entrega 1

Cliente asíncrono unificado para **OpenAI**, **Anthropic** y **Gemini** (Python 3.12).

## Arquitectura

El código de negocio (`main.py`) nunca instancia un SDK. Habla solo con `AsyncLLMManager`.

```text
BaseLLMClient (ABC)
  generate() / generate_stream()
        ▲
        │  mismo contrato
        │
  OpenAIClient    AnthropicClient    GeminiClient
  (AsyncOpenAI)   (AsyncAnthropic)   (genai.aio)
        ▲
        │
  AsyncLLMManager  ← factory
        │
  LLMConfig.provider  ← variable LLM_PROVIDER en .env
```

- **Intercambiabilidad:** cambiar `LLM_PROVIDER` (openai | anthropic | gemini) cambia el cliente sin tocar `main.py`.
- **Asincronía:** todas las llamadas de red usan `await` (`AsyncOpenAI`, `AsyncAnthropic`, `client.aio`).
- **Streaming:** `generate_stream` es un generador asíncrono (`yield` dentro de `async for`).
- **Validación:** Pydantic valida `ChatMessage`, `LLMConfig` (temperatura 0–2, `max_tokens > 0`) y `ModelResponse`. Las claves van en `SecretStr`.
- **Resiliencia:** `RateLimitError` y `APIConnectionError` se empaquetan en `ModelResponse.error`; no tumban el proceso.

## Requisitos

- Python 3.12
- Al menos la API key del proveedor indicado en `LLM_PROVIDER`

## Cómo correrlo

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Completá `.env`:

```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=tu_clave_de_openai
ANTHROPIC_API_KEY=tu_clave_de_anthropic
GOOGLE_API_KEY=tu_clave_de_gemini
```

`AsyncLLMManager.from_env()` lee `LLM_PROVIDER` y la clave asociada. Para probar Anthropic, cambiá a `LLM_PROVIDER=anthropic` (y así con `gemini`).

```bash
python main.py
```

El script prueba:

1. Validación Pydantic (`temperature` fuera de 0–2)
2. Resiliencia con una API key inválida (no crashea)
3. Modo normal y streaming con *"¿Qué es la entropía?"* sobre el proveedor configurado

## Archivos

```text
schemas.py        ChatMessage, LLMConfig, ModelResponse, Provider
clients.py        BaseLLMClient, OpenAI / Anthropic / Gemini, AsyncLLMManager
main.py           script de prueba
requirements.txt  openai, anthropic, google-genai, pydantic, python-dotenv
.env.example      plantilla de variables (no subas .env)
.gitignore        excluye .env, .venv, __pycache__
README.md         este archivo
```
