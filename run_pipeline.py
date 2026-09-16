import asyncio
import json
import logging

from dotenv import find_dotenv, load_dotenv
from pydantic import ValidationError

from chain import process_text
from schemas import EntidadesTecnicas, NivelDeCriticidad

load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

EJEMPLO_ARQUITECTURA = (
    "El checkout de la tienda corre sobre FastAPI detrás de Nginx. Las sesiones "
    "se cachean en Redis y los pedidos se persisten en PostgreSQL. Con picos de "
    "tráfico las conexiones al pool se agotan y el health-check empieza a fallar; "
    "los usuarios ven 502 y no pueden pagar."
)

TEXTO_AMBIGUO = (
    "Esta mañana el servicio anduvo raro un rato y después volvió. "
    "Alguien mencionó la base y el cache, pero no hay ticket ni métricas."
)


async def demo_validacion_local() -> None:
    print("=" * 60)
    print("1. El contrato Pydantic rechaza tecnologías vacías")
    print("=" * 60)
    try:
        EntidadesTecnicas(
            tecnologias=["  "],
            nivel_de_criticidad=NivelDeCriticidad.BAJA,
            resumen_tecnico="texto de relleno",
        )
    except ValidationError as e:
        print(e, flush=True)
    print(flush=True)


async def demo_pipeline(titulo: str, texto: str) -> None:
    print("=" * 60)
    print(titulo)
    print("=" * 60)
    print("Entrada:", texto, "\n", flush=True)
    resultado = await process_text(texto)
    print(json.dumps(resultado.model_dump(mode="json"), ensure_ascii=False, indent=2), flush=True)
    print(flush=True)


async def main() -> None:
    await demo_validacion_local()
    await demo_pipeline("2. Caso claro (arquitectura + incidente)", EJEMPLO_ARQUITECTURA)
    await demo_pipeline("3. Prueba de estrés (texto ambiguo)", TEXTO_AMBIGUO)


if __name__ == "__main__":
    asyncio.run(main())
