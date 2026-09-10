import asyncio

from dotenv import find_dotenv, load_dotenv
from pydantic import SecretStr, ValidationError

from clients import AsyncLLMManager
from schemas import ChatMessage, LLMConfig, Provider

load_dotenv(find_dotenv())

PREGUNTA = [
    ChatMessage(role="system", content="Respondé de forma breve y clara."),
    ChatMessage(role="user", content="¿Qué es la entropía?"),
]


async def demo_pydantic():
    print("=" * 60)
    print("1. Validación preventiva con Pydantic")
    print("=" * 60)
    try:
        LLMConfig(
            provider=Provider.OPENAI,
            model="gpt-4o-mini",
            openai_api_key=SecretStr("sk-solo-para-validar-schema"),
            temperature=5.0,
        )
    except ValidationError as e:
        print("Error detectado ANTES de llamar a la API:")
        print(e)
    print()


async def demo_resiliencia():
    print("=" * 60)
    print("2. Resiliencia (API key inválida, sin crash)")
    print("=" * 60)
    config = LLMConfig(
        provider=Provider.OPENAI,
        model="gpt-4o-mini",
        openai_api_key=SecretStr("sk-invalida-para-prueba"),
        temperature=0.7,
        max_tokens=100,
    )
    resultado = await AsyncLLMManager(config).generate(PREGUNTA)
    print("¿El programa siguió vivo?: sí")
    print("Error capturado:", resultado.error)
    print()


async def demo_proveedor_configurado():
    print("=" * 60)
    print("3. Proveedor según LLM_PROVIDER (normal + streaming)")
    print("=" * 60)
    try:
        manager = AsyncLLMManager.from_env()
    except (ValidationError, ValueError) as e:
        print("No se pudo instanciar el cliente desde .env:")
        print(e)
        print("Definí LLM_PROVIDER y la API key correspondiente.\n")
        return

    print(f"Proveedor: {manager.config.provider.value} | modelo: {manager.config.model}")

    print("\nModo normal:")
    resultado = await manager.generate(PREGUNTA)
    if resultado.error:
        print("Error:", resultado.error)
    else:
        print(resultado.content)

    print("\nModo streaming:")
    async for chunk in manager.generate_stream(PREGUNTA):
        print(chunk, end="", flush=True)
    print("\n")


async def main():
    await demo_pydantic()
    await demo_resiliencia()
    await demo_proveedor_configurado()


if __name__ == "__main__":
    asyncio.run(main())
