"""Cadena RAG asíncrona: retriever Chroma + LCEL + PydanticOutputParser."""

import logging

from langchain_core.documents import Document
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, RunnablePassthrough
from pydantic import BaseModel, Field

from chain import crear_modelo
from ingest import abrir_coleccion

logger = logging.getLogger(__name__)

TOP_K = 4


class Referencia(BaseModel):
    fuente: str = Field(description="Nombre de archivo del contexto, por ejemplo arquitectura-lumen.md")
    fragmento: str = Field(description="Pasaje del contexto que sostiene la respuesta")


class RespuestaRAG(BaseModel):
    respuesta: str = Field(description="Respuesta en español, basada solo en el contexto")
    referencias: list[Referencia] = Field(
        default_factory=list,
        description="Fuentes usadas. Lista vacía si el contexto no alcanza para responder",
    )


def _formatear_documentos(docs: list[Document]) -> str:
    if not docs:
        return "(sin fragmentos recuperados)"
    bloques = []
    for doc in docs:
        fuente = doc.metadata.get("source", "desconocida")
        bloques.append(f"[fuente: {fuente}]\n{doc.page_content}")
    return "\n\n".join(bloques)


def _con_contexto(datos: dict) -> dict:
    return {
        "question": datos["question"],
        "context": _formatear_documentos(datos["docs"]),
    }


def build_rag_chain() -> Runnable:
    parser = PydanticOutputParser(pydantic_object=RespuestaRAG)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Sos un asistente técnico de la plataforma Lumen. "
                "Respondé únicamente con el CONTEXTO proporcionado. "
                "Si la respuesta no está en el contexto, decí «No lo sé» "
                "y devolvé referencias vacías. "
                "No inventes datos. No completes con conocimiento externo.\n"
                "{format_instructions}",
            ),
            ("human", "CONTEXTO:\n{context}\n\nPREGUNTA:\n{question}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    modelo = crear_modelo()
    retriever = abrir_coleccion().as_retriever(search_kwargs={"k": TOP_K})
    return (
        RunnableParallel(docs=retriever, question=RunnablePassthrough())
        | RunnableLambda(_con_contexto)
        | prompt
        | modelo
        | parser
    )


async def get_rag_response(query: str) -> RespuestaRAG:
    """Busca en Chroma, arma el prompt y parsea la respuesta del LLM."""
    if not query or not query.strip():
        raise ValueError("La consulta no puede estar vacía")

    pregunta = query.strip()
    logger.info("Consulta RAG: %s", pregunta)
    return await build_rag_chain().ainvoke(pregunta)
