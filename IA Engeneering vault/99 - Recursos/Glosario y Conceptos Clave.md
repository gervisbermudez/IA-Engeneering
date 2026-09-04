---
tags:
  - glosario
  - cheat-sheet
  - definiciones
created: 2026-09-04
---

# 📖 Glosario Técnico de AI Engineering

* **Asyncio**: Librería estándar de Python para concurrencia cooperativa no bloqueante mediante un Event Loop. Ideal para tareas I/O-bound (llamadas a APIs de LLMs).
* **Time to First Token (TTFT)**: Tiempo que transcurre desde que el usuario envía su petición hasta que se renderiza el primer token en pantalla. Optimizado mediante streaming.
* **LCEL (LangChain Expression Language)**: Sintaxis declarativa que utiliza el operador pipe (`|`) para conectar componentes `Runnable` (Prompts, Modelos, Parsers).
* **Embeddings**: Vectores numéricos densos de punto flotante que proyectan el significado semántico del texto en un espacio multidimensional.
* **Similitud Coseno**: Métrica angular para comparar vectores independientemente de la longitud del texto. Estándar en RAG.
* **Chunking**: Técnica de partición de documentos en unidades de texto coherentes con solapamiento (*overlap*) para evitar pérdida de contexto.
* **Reciprocal Rank Fusion (RRF)**: Algoritmo de combinación de resultados de diferentes motores (ej. BM25 léxico y Pinecone denso) basándose en su ranking ordinal.
* **LangGraph**: Framework basado en grafos de estado cíclicos diseñado para construir agentes autónomos con memoria persistente y branching condicional.
* **Ciclo ReAct (Reasoning + Acting)**: Paradigma donde un LLM analiza el problema, invoca herramientas, observa el resultado y sintetiza su respuesta en bucle.
* **Supervisor Pattern**: Topología jerárquica multi-agente donde un nodo central inteligente enruta y delega subtareas a agentes especializados sin ejecutar el trabajo directamente.
* **Checkpointer**: Mecanismo de persistencia (ej. `SqliteSaver`, `RedisSaver`) que almacena el estado completo de un grafo paso a paso, indexado por `thread_id`.
* **Human-in-the-Loop (HITL)**: Capacidad de pausar la ejecución de un agente autónomo antes de una acción crítica para exigir aprobación de un operador humano.
* **Tracing / Spans**: Desglose jerárquico de cada micro-paso de una petición para auditar latencia, consumo de tokens y detectar alucinaciones con Arize Phoenix o LangSmith.
