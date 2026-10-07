"""Dos pruebas del RAG: una pregunta cubierta por /data y una pregunta trampa."""

import asyncio
import logging
import re
import sys
import unicodedata

from ingest import ingest
from rag import get_rag_response

FRASE_SIN_INFORMACION = "no lo sé"

PREGUNTA_EN_CONTEXTO = (
    "¿Cuántos días se retienen las métricas de alta resolución "
    "y cuánto tiempo se retiene el rollup de 1 hora?"
)
PREGUNTA_TRAMPA = "¿En qué año se fundó Lumen?"


def _tiene_retencion(texto: str) -> bool:
    plano = texto.casefold()
    return "15" in plano and "día" in plano and "13" in plano and "mes" in plano


def _inventa_anio(texto: str) -> bool:
    if re.search(r"\b(?:19|20)\d{2}\b", texto):
        return True
    return "dos mil" in texto.casefold()


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _negativa_explicita(texto: str) -> bool:
    return _sin_acentos(FRASE_SIN_INFORMACION) in _sin_acentos(texto)


async def _probar(titulo: str, pregunta: str):
    print(f"\n=== {titulo} ===")
    print(pregunta)
    respuesta = await get_rag_response(pregunta)
    print(respuesta.model_dump_json(indent=2))
    return respuesta


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ingest()
    en_contexto = await _probar("Pregunta en los documentos", PREGUNTA_EN_CONTEXTO)
    if not _tiene_retencion(en_contexto.respuesta) or not en_contexto.referencias:
        raise SystemExit(
            "FALLO: la respuesta no contiene la retención de 15 días "
            "y el rollup de 1 hora por 13 meses, o referencias quedó vacía."
        )

    trampa = await _probar("Pregunta fuera de contexto", PREGUNTA_TRAMPA)
    if _inventa_anio(trampa.respuesta) or not _negativa_explicita(trampa.respuesta):
        raise SystemExit(
            "FALLO: la respuesta inventa el año de fundación o no dice «No lo sé»."
        )
    print("\nPruebas OK")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SystemExit as exc:
        if exc.code not in (0, None):
            print(exc, file=sys.stderr)
        raise
