---
tags:
  - faq
  - repaso
  - examenes
created: 2026-09-04
---

# 🎯 Preguntas Frecuentes y Cheat Sheet de Examen

### ❓ 1. ¿Por qué usamos Asyncio y Python 3.12 desde el inicio si los scripts de IA suelen ser lineales?
**Respuesta**: Las aplicaciones reales de IA pasan el 90% del tiempo esperando respuestas de red de APIs externas. Si usas código síncrono, tu servidor se congela en cada llamada. `asyncio` permite que un único proceso atienda cientos de conexiones concurrentes mientras espera los tokens.

### ❓ 2. ¿Cuál es la diferencia real entre LangChain (LCEL) y LangGraph?
**Respuesta**:
* **LCEL (LangChain)** está diseñado para flujos acíclicos y deterministas ($A ightarrow B ightarrow C$). Ideal para pipelines de extracción o RAG básico.
* **LangGraph** está diseñado para flujos cíclicos con bucles de razonamiento donde el agente decide si la respuesta es satisfactoria o si debe reintentar o usar herramientas.

### ❓ 3. ¿Por qué aprender ChromaDB local si luego se usa Pinecone en la nube?
**Respuesta**: ChromaDB permite dominar las operaciones CRUD vectoriales, el chunking y la geometría semántica localmente sin costo ni latencia de red. Escalar a Pinecone en el Módulo 4 se convierte en un desafío de arquitectura (namespaces, batching, serverless) y no de comprensión básica.

### ❓ 4. ¿Por qué sumar scores de BM25 y similitud vectorial directamente es un error de novato?
**Respuesta**: Porque operan en escalas heterogéneas (un score BM25 de 22.0 no equivale a un coseno de 0.85). La técnica correcta de la industria es utilizar **Reciprocal Rank Fusion (RRF)** para combinar sus rankings relativos.

### ❓ 5. ¿Por qué más agentes autónomos no siempre es mejor?
**Respuesta**: Por la "Entropía de Agentes". Añadir agentes sin una arquitectura estructurada dispara la latencia, multiplica el costo de tokens y genera bucles de corrección infinitos. El patrón Supervisor con estado compartido y condiciones de corte estrictas garantiza orden y predictibilidad.
