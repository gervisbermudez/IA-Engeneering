import asyncio
import os
from dotenv import find_dotenv, load_dotenv
from pydantic import SecretStr, ValidationError

from schemas import ChatMessage, LLMConfig, Provider
from clients import AsyncLLMManager

# Cargar variables de entorno desde el archivo .env (búsqueda en root y directorios superiores)
load_dotenv(find_dotenv())


async def demo_pydantic_validation():
    print("=" * 60)
    print("1. VALIDACIÓN PREVENTIVA CON PYDANTIC")
    print("=" * 60)
    try:
        # Intentamos instanciar una configuración con temperatura inválida (> 2.0)
        LLMConfig(provider=Provider.OPENAI, model="gpt-4o-mini", temperature=5.0)
    except ValidationError as e:
        print("✅ Error detectado ANTES de llamar a la API (control de parámetros):")
        print(e)
    print()


async def demo_resilience():
    print("=" * 60)
    print("2. PRUEBA DE RESILIENCIA (Sin caídas ante API Key inválida)")
    print("=" * 60)
    pregunta = [ChatMessage(role="user", content="¿Qué es la entropía? Respondé en 2 líneas.")]

    config_invalida = LLMConfig(
        provider=Provider.OPENAI,
        model="gpt-4o-mini",
        openai_api_key=SecretStr("sk-invalida-para-prueba-resiliencia"),
        temperature=0.7,
        max_tokens=100,
    )

    manager_roto = AsyncLLMManager(config_invalida)
    resultado = await manager_roto.generate(pregunta)

    print("¿El programa siguió vivo y sin crash?: ✅ Sí")
    print(f"Error capturado estructuradamente: {resultado.error}")
    print()


async def demo_provider(provider: Provider, model: str, api_key_env_var: str):
    api_key = os.getenv(api_key_env_var)
    nombre = provider.value.capitalize()

    print("=" * 60)
    print(f"3. PRUEBAS CON PROVEEDOR: {nombre} ({model})")
    print("=" * 60)

    if not api_key:
        print(f"⚠️  Variable {api_key_env_var} no configurada en .env.")
        print(f"   Para probar {nombre}, agrega {api_key_env_var}=tu_clave en .env.")
        print()
        return

    # Mapeo de clave según proveedor
    config_args = {
        "provider": provider,
        "model": model,
        "temperature": 0.7,
        "max_tokens": 200,
    }
    if provider == Provider.OPENAI:
        config_args["openai_api_key"] = SecretStr(api_key)
    elif provider == Provider.ANTHROPIC:
        config_args["anthropic_api_key"] = SecretStr(api_key)
    elif provider == Provider.GEMINI:
        config_args["google_api_key"] = SecretStr(api_key)

    config = LLMConfig(**config_args)
    manager = AsyncLLMManager(config)

    pregunta = [ChatMessage(role="user", content="¿Qué es la entropía? Respondé en 2 líneas.")]

    # Modo Normal
    print(f"🟢 Modo Normal ({nombre}):")
    resultado = await manager.generate(pregunta)
    if resultado.error:
        print(f"❌ Error: {resultado.error}")
    else:
        print(resultado.content)

    # Modo Streaming
    print(f"\n🟢 Modo Streaming ({nombre}):")
    async for chunk in manager.generate_stream(pregunta):
        print(chunk, end="", flush=True)
    print("\n")


async def main():
    print("\n🚀 INICIANDO SUITE DE PRUEBAS DEL CLIENTE ASÍNCRONO DE LLM\n")

    # 1. Validación preventiva Pydantic
    await demo_pydantic_validation()

    # 2. Resiliencia ante errores
    await demo_resilience()

    # 3. Pruebas reales por proveedor si existen las API Keys
    await demo_provider(Provider.GEMINI, "gemini-2.5-flash", "GOOGLE_API_KEY")
    await demo_provider(Provider.OPENAI, "gpt-4o-mini", "OPENAI_API_KEY")
    await demo_provider(Provider.ANTHROPIC, "claude-3-5-sonnet-20241022", "ANTHROPIC_API_KEY")


if __name__ == "__main__":
    asyncio.run(main())
