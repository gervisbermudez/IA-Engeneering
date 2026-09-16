# Pipeline de extracción de entidades técnicas — Pre-entrega 2

Pipeline LCEL que recibe un párrafo sin procesar (arquitectura o log de error) y
devuelve un objeto Pydantic validado.

Este repo también incluye el cliente asíncrono unificado del Módulo 1
(`clients.py` + `main.py`).

## Contrato de salida

```json
{
  "tecnologias": ["FastAPI", "Redis", "PostgreSQL"],
  "nivel_de_criticidad": "alta",
  "resumen_tecnico": "API con caché en Redis y persistencia en PostgreSQL; cuello de botella en conexiones concurrentes."
}
```

El modelo `EntidadesTecnicas` exige:

- `tecnologias`: lista no vacía (sin strings en blanco)
- `nivel_de_criticidad`: enum `baja` | `media` | `alta`
- `resumen_tecnico`: al menos 10 caracteres

## Arquitectura del pipeline

```text
ChatPromptTemplate
        │
        ▼
ChatOpenAI / ChatAnthropic / Gemini   ← LLMConfig.from_env() (Módulo 1)
        │
        ▼
.with_structured_output(EntidadesTecnicas, include_raw=True)
        │
        ▼
validación (finish_reason + parseo)
        │
        ▼
.with_retry()  →  process_text() / ainvoke()
```

- **Prompt modular:** `ChatPromptTemplate` con la variable `{text}`. No hay f-strings
  dentro de la cadena.
- **Salida estructurada:** `model.with_structured_output(EntidadesTecnicas)`.
- **Resiliencia:** `.with_retry()` (hasta 3 intentos) ante JSON mal formado, objeto
  incompleto, `finish_reason` de corte por tokens (`length` / `max_tokens`) si el
  parseo falló, y errores transitorios de API (5xx, 429, timeout). Si el JSON ya
  valida, no se descarta por un `finish_reason` de corte. El pipeline pide al menos
  2048 tokens de salida.
- **Asincronía:** `process_text(text)` usa `.ainvoke()`.

## Requisitos

- Python 3.12
- API key del proveedor indicado en `LLM_PROVIDER` (`openai`, `anthropic` o `gemini`)

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

```bash
python run_pipeline.py
```

El script:

1. Muestra que Pydantic rechaza `tecnologias` vacías **antes** de llamar al LLM
2. Extrae entidades de una descripción de arquitectura + incidente
3. Hace una prueba de estrés con un texto ambiguo

Para el demo del Módulo 1 (cliente unificado + streaming):

```bash
python main.py
```

## Archivos

```text
schemas.py        Contratos Pydantic (Módulo 1 + EntidadesTecnicas)
chain.py          Prompt, LCEL, retry y process_text()
run_pipeline.py   Mini-script asíncrono de prueba
clients.py        Factory OpenAI / Anthropic / Gemini (Módulo 1)
main.py           Demo del cliente unificado
requirements.txt
.env.example
README.md
```
