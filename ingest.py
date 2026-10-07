"""Ingesta de documentos locales en ChromaDB."""

import logging
from pathlib import Path

import chromadb
import tiktoken
from chromadb.errors import NotFoundError
from dotenv import find_dotenv, load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
VECTORSTORE_DIR = ROOT / "vectorstore"
COLLECTION = "lumen_docs"
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_TOKENS = 500
CHUNK_OVERLAP = 50

_encoder = tiktoken.get_encoding("cl100k_base")


def _largo_en_tokens(texto: str) -> int:
    return len(_encoder.encode(texto))


def get_embeddings() -> Embeddings:
    """Mismo modelo para indexar y para consultar."""
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def _splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_TOKENS,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=_largo_en_tokens,
    )


def _archivos_corpus(directorio: Path = DATA_DIR) -> list[Path]:
    return sorted(
        p
        for p in directorio.iterdir()
        if p.suffix.lower() in {".md", ".txt"} and p.is_file()
    )


def cargar_documentos(directorio: Path = DATA_DIR) -> list[Document]:
    rutas = _archivos_corpus(directorio)
    if not rutas:
        raise FileNotFoundError(f"No hay archivos .md o .txt en {directorio}")

    documentos: list[Document] = []
    for ruta in rutas:
        texto = ruta.read_text(encoding="utf-8").strip()
        if not texto:
            logger.warning("Se omite %s porque está vacío", ruta.name)
            continue
        documentos.append(Document(page_content=texto, metadata={"source": ruta.name}))
    if not documentos:
        raise FileNotFoundError(f"Los archivos de {directorio} están vacíos")
    return documentos


def _cliente() -> chromadb.PersistentClient:
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(VECTORSTORE_DIR))


def _ya_indexada() -> bool:
    try:
        coleccion = _cliente().get_collection(COLLECTION)
    except NotFoundError:
        return False
    return coleccion.count() > 0


def abrir_coleccion() -> Chroma:
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(VECTORSTORE_DIR),
    )


def ingest() -> Chroma:
    """Fragmenta /data y persiste en Chroma.

    Si la colección ya existe y tiene fragmentos, no vuelve a indexar.
    """
    if _ya_indexada():
        logger.info("La colección %s ya existe; no se reindexa", COLLECTION)
        return abrir_coleccion()

    documentos = cargar_documentos()
    fragmentos = _splitter().split_documents(documentos)
    logger.info(
        "Indexando %d fragmentos (chunk=%d tokens, overlap=%d, modelo=%s) desde %d archivos",
        len(fragmentos),
        CHUNK_TOKENS,
        CHUNK_OVERLAP,
        EMBEDDING_MODEL,
        len(documentos),
    )
    store = abrir_coleccion()
    if fragmentos:
        store.add_documents(fragmentos)
    return store


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ingest()
    total = _cliente().get_collection(COLLECTION).count()
    print(f"Colección lista: {total} fragmentos")
