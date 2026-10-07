import logging
from typing import Any

from dotenv import find_dotenv, load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.exceptions import (
    ModelAPIError,
    ModelConnectionError,
    ModelRateLimitError,
    ModelTimeoutError,
    OutputParserException,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from schemas import EntidadesTecnicas, LLMConfig, Provider

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

_FINISH_INCOMPLETO = {"length", "max_tokens"}
_MAX_TOKENS_MINIMO = 2048
_MAX_INTENTOS = 3


class IncompleteOutputError(ValueError):
    """La respuesta del LLM se cortó (finish_reason) antes de completar el JSON."""


_EXCEPCIONES_RETRY = (
    IncompleteOutputError,
    OutputParserException,
    ValidationError,
    ModelAPIError,
    ModelRateLimitError,
    ModelConnectionError,
    ModelTimeoutError,
)

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Sos un analista de ingeniería de software. Extraé entidades técnicas "
            "del texto del usuario y devolvê un objeto estructurado.\n"
            "Reglas:\n"
            "- tecnologias: lista de nombres concretos (lenguajes, frameworks, "
            "bases de datos, colas, clouds, protocolos). Sin ítems vacíos.\n"
            "- nivel_de_criticidad: 'baja' si es informativo, 'media' si hay "
            "degradación, 'alta' si hay outage, pérdida de datos o riesgo de seguridad.\n"
            "- resumen_tecnico: una o dos oraciones, en español, que expliquen "
            "el hallazgo o la arquitectura.\n"
            "Si el texto es ambiguo, inferí lo mínimo razonable y no dejes campos vacíos.",
        ),
        ("human", "{text}"),
    ]
)


def _max_tokens_pipeline(cfg: LLMConfig) -> int:
    return max(cfg.max_tokens, _MAX_TOKENS_MINIMO)


def _crear_modelo(config: LLMConfig | None = None) -> BaseChatModel:
    """Reusa LLMConfig del Módulo 1 para instanciar el chat de LangChain."""
    cfg = config or LLMConfig.from_env()
    max_tokens = _max_tokens_pipeline(cfg)
    if cfg.provider == Provider.OPENAI:
        if not cfg.openai_api_key:
            raise ValueError("Falta openai_api_key para ChatOpenAI")
        return ChatOpenAI(
            model=cfg.model,
            api_key=cfg.openai_api_key.get_secret_value(),
            temperature=0,
            max_tokens=max_tokens,
        )
    if cfg.provider == Provider.ANTHROPIC:
        if not cfg.anthropic_api_key:
            raise ValueError("Falta anthropic_api_key para ChatAnthropic")
        return ChatAnthropic(
            model=cfg.model,
            api_key=cfg.anthropic_api_key.get_secret_value(),
            temperature=0,
            max_tokens=max_tokens,
        )
    if cfg.provider == Provider.GEMINI:
        if not cfg.google_api_key:
            raise ValueError("Falta google_api_key para ChatGoogleGenerativeAI")
        return ChatGoogleGenerativeAI(
            model=cfg.model,
            google_api_key=cfg.google_api_key.get_secret_value(),
            temperature=0,
            max_output_tokens=max_tokens,
        )
    raise ValueError(f"Proveedor no soportado: {cfg.provider}")


def crear_modelo(config: LLMConfig | None = None) -> BaseChatModel:
    """Punto público para instanciar el chat model. Lo usa el RAG."""
    return _crear_modelo(config)


def _finish_reason(raw: AIMessage | None) -> str | None:
    if raw is None:
        return None
    meta = raw.response_metadata or {}
    return meta.get("finish_reason") or meta.get("stop_reason")


def _intento_desde_config(config: RunnableConfig | None) -> int:
    for tag in (config or {}).get("tags") or []:
        if isinstance(tag, str) and tag.startswith("retry:attempt:"):
            try:
                return int(tag.rsplit(":", 1)[-1])
            except ValueError:
                return 2
    return 1


def _marcar_intento(
    entrada: dict[str, Any], config: RunnableConfig | None = None
) -> dict[str, Any]:
    intento = _intento_desde_config(config)
    if intento > 1:
        logger.info(
            "Reintento automático del pipeline: intento %s/%s",
            intento,
            _MAX_INTENTOS,
        )
    else:
        logger.info("Intento %s/%s del pipeline", intento, _MAX_INTENTOS)
    return entrada


def _validar_salida_estructurada(payload: dict[str, Any]) -> EntidadesTecnicas:
    """Revisa finish_reason y el parseo antes de aceptar el objeto."""
    raw = payload.get("raw")
    parsed = payload.get("parsed")
    parsing_error = payload.get("parsing_error")
    reason = _finish_reason(raw if isinstance(raw, AIMessage) else None)
    reason_norm = (reason or "").lower()
    cortado = reason_norm in _FINISH_INCOMPLETO

    logger.info("Validación de salida: finish_reason=%s parsed=%s", reason, parsed is not None)

    if parsing_error is not None:
        logger.warning("JSON mal formado o incompleto: %s", parsing_error)
        if isinstance(parsing_error, BaseException):
            raise OutputParserException(str(parsing_error)) from parsing_error
        raise OutputParserException(str(parsing_error))

    if parsed is None:
        if cortado:
            logger.warning("Respuesta incompleta (finish_reason=%s). Se reintentará.", reason)
            raise IncompleteOutputError(
                f"El modelo cortó la respuesta por tokens (finish_reason={reason})"
            )
        logger.warning("El parser no devolvió un objeto validado")
        raise OutputParserException("Salida estructurada vacía o incompleta")

    if not isinstance(parsed, EntidadesTecnicas):
        parsed = EntidadesTecnicas.model_validate(parsed)

    if cortado:
        logger.info(
            "finish_reason=%s, pero el objeto Pydantic ya está completo; se acepta",
            reason,
        )

    logger.info(
        "Objeto validado: tecnologias=%s criticidad=%s",
        parsed.tecnologias,
        parsed.nivel_de_criticidad.value,
    )
    return parsed


def build_chain(config: LLMConfig | None = None) -> Runnable:
    """prompt | model.with_structured_output(Schema) + .with_retry()."""
    modelo = _crear_modelo(config)
    extraer = modelo.with_structured_output(EntidadesTecnicas, include_raw=True)
    validar = RunnableLambda(_validar_salida_estructurada)

    cadena = RunnableLambda(_marcar_intento) | PROMPT | extraer | validar
    return cadena.with_retry(
        retry_if_exception_type=_EXCEPCIONES_RETRY,
        stop_after_attempt=_MAX_INTENTOS,
        wait_exponential_jitter=True,
    )


_cadena: Runnable | None = None


def get_chain() -> Runnable:
    global _cadena
    if _cadena is None:
        _cadena = build_chain()
    return _cadena


async def process_text(text: str) -> EntidadesTecnicas:
    """Ejecuta la cadena LCEL de forma asíncrona y loguea validación/reintentos."""
    if not text or not text.strip():
        raise ValueError("El texto de entrada no puede estar vacío")

    logger.info("Invocando pipeline sobre %d caracteres", len(text))
    try:
        resultado = await get_chain().ainvoke({"text": text})
    except _EXCEPCIONES_RETRY:
        logger.exception("El pipeline falló después de los reintentos automáticos")
        raise

    logger.info("Pipeline OK")
    return resultado
