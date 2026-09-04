# Unified Async LLM Client — Pre-entrega Módulo 1

Capa de abstracción asíncrona unificada para interactuar con proveedores líderes de Large Language Models (**OpenAI**, **Anthropic** y **Google Gemini**) utilizando **Python 3.12**, **Asyncio** y contratos de datos estrictos con **Pydantic**.

---

## 🎯 Objetivos de la Entrega

1. **Intercambiabilidad**: Instanciar proveedores distintos bajo una interfaz base unificada (`BaseLLMClient`) mediante el patrón Factory (`AsyncLLMManager`).
2. **Asincronía Total**: Todas las operaciones de red son no bloqueantes utilizando `async/await`.
3. **Streaming de Tokens**: Generadores asíncronos (`AsyncGenerator[str, None]`) con `yield` para respuestas en tiempo real con bajo *Time to First Token (TTFT)*.
4. **Validación Estricta**: Modelos Pydantic para mensajes de entrada, configuración del modelo y respuestas estructuradas.
5. **Resiliencia y Manejo de Errores**: Captura estructurada de excepciones de red, cuota (*Rate Limit*) y errores de API sin interrumpir el flujo principal.

---

## 📂 Estructura del Proyecto

```text
.
├── src/                    # Código fuente del cliente unificado
│   ├── __init__.py
│   ├── schemas.py          # Contratos de datos (Pydantic): ChatMessage, LLMConfig, ModelResponse, Provider
│   ├── clients.py          # BaseLLMClient, OpenAIClient, AnthropicClient, GeminiClient, AsyncLLMManager
│   ├── main.py             # Script de validación: pruebas en modo normal, streaming y resiliencia
│   └── entregable1.txt     # Código base y especificación de referencia
├── obsidian/               # Bóveda de notas de estudio organizada por módulos
├── requirements.txt        # Dependencias oficiales del proyecto (en raíz)
├── program-summary.pdf     # Guía integral del programa AI Engineering (en raíz)
├── .env.example            # Plantilla de variables de entorno requeridas
├── .env                    # Variables de entorno locales (ignorado en git)
├── .gitignore              # Exclusiones estándar (.venv, .env, __pycache__)
└── README.md               # Documentación completa de configuración y ejecución
```

---

## ⚙️ Configuración del Entorno

### 1. Requisitos Previos
- **Python 3.12+** instalado.
- Gestor de paquetes `pip` o `uv`.

### 2. Crear y Activar el Entorno Virtual

Con `uv` (recomendado):
```bash
uv venv --python 3.12 .venv
source .venv/bin/activate
```

O con `venv` estándar:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```
*(O con uv: `uv pip install -r requirements.txt`)*

### 4. Configurar Variables de Entorno
Copia el archivo `.env.example` a `.env` y coloca tus claves de API:

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:
```ini
OPENAI_API_KEY=tu_clave_de_openai
ANTHROPIC_API_KEY=tu_clave_de_anthropic
GOOGLE_API_KEY=tu_clave_de_gemini
```
> **Nota**: Si solo dispones de una de las claves (por ejemplo, Google AI Studio que ofrece *Free Tier*), el script ejecutará las pruebas para ese proveedor y avisará de los restantes sin fallar.

---

## 🚀 Ejecución de las Pruebas

Para correr la suite de validación completa:

```bash
python src/main.py
```

El script ejecuta automáticamente:
1. **Validación Preventiva con Pydantic**: Demuestra que un parámetro inválido (como `temperature=5.0`) es interceptado antes de consumir tokens o llamar a la API.
2. **Prueba de Resiliencia ante Fallos**: Realiza una petición con una clave inválida a propósito y comprueba que el sistema devuelve un `ModelResponse` con el error estructurado sin lanzar excepciones no controladas (*crash*).
3. **Pruebas de Modo Normal y Streaming**: Por cada proveedor configurado en `.env`, genera una respuesta síncrona completa y luego realiza la transmisión token a token por streaming.

---

## 🧩 Arquitectura Técnica

### Patrón Factory (`AsyncLLMManager`)
Desacopla la lógica de negocio de los clientes concretos:
```python
from schemas import LLMConfig, Provider, ChatMessage
from clients import AsyncLLMManager
from pydantic import SecretStr
import os

config = LLMConfig(
    provider=Provider.OPENAI,
    model="gpt-4o-mini",
    openai_api_key=SecretStr(os.environ["OPENAI_API_KEY"]),
    temperature=0.7,
    max_tokens=200
)

manager = AsyncLLMManager(config)
```

### Modo Normal vs. Modo Streaming
```python
messages = [ChatMessage(role="user", content="Explica la entropía en 2 líneas")]

# Normal (completo)
response = await manager.generate(messages)
print(response.content)

# Streaming (token a token)
async for token in manager.generate_stream(messages):
    print(token, end="", flush=True)
```

### Manejo de Secretos y Validación
- Uso de `SecretStr` de Pydantic para evitar la exposición accidental de API Keys en logs.
- Validación de rangos en `temperature` ($0 \le temp \le 2$) y `max_tokens` ($> 0$).
- Validación de roles permitidos en mensajes (`user`, `assistant`, `system`).
