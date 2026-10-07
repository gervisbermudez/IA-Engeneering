# Pre-entrega 3: RAG local

Flujo de recuperación semántica sobre notas de la plataforma Lumen.
La consulta busca fragmentos en ChromaDB y el modelo responde solo con ese contexto.

## Requisitos

- Python 3.12
- `OPENAI_API_KEY` para los embeddings (`text-embedding-3-small`)
- API key del proveedor indicado en `LLM_PROVIDER` (`openai`, `anthropic` o `gemini`) para el chat

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
python run_rag.py
```

`ingest.py` lee `data/*.md` y `data/*.txt`, los parte con
`RecursiveCharacterTextSplitter` (500 tokens, overlap de 50, medidos con tiktoken)
y los guarda en `./vectorstore` (ChromaDB). Si la colección ya existe y tiene
fragmentos, no vuelve a indexar.

Indexado y consulta usan el mismo modelo, `text-embedding-3-small`
(`OpenAIEmbeddings`). El chat reutiliza `crear_modelo()` (`LLMConfig.from_env()`).

`get_rag_response(query)` es asíncrona. La cadena LCEL une el retriever
(4 fragmentos), el formateo del contexto, el prompt, el LLM y
`PydanticOutputParser` (`RespuestaRAG`: `respuesta` + `referencias`). Si el dato
no está en el contexto, el prompt pide decir «No lo sé».

`run_rag.py` indexa (o reutiliza el índice) y hace dos consultas:

1. Retención de métricas de alta resolución (15 días) y rollup de 1 hora
   (13 meses). Falla si la respuesta no contiene esos datos o si `referencias` queda vacía.
2. Año de fundación de Lumen, que no está en `data/`. Falla si la respuesta
   inventa ese año. Tiene que responder «No lo sé».

## Archivos

```text
data/             Notas de la plataforma Lumen
ingest.py         Chunking y persistencia en ChromaDB
rag.py            Cadena LCEL y get_rag_response()
run_rag.py        Pregunta respondible y pregunta trampa
chain.py          Cliente de chat (crear_modelo)
schemas.py        LLMConfig y contratos Pydantic del chat
requirements.txt
.env.example
README.md
```
