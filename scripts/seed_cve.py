import asyncio
import logging
from typing import Any

from tracer_mesh.core.db import StateStore
from tracer_mesh.core.llm import LLMClient

# setup logging output
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# default critical cve baseline database
BASELINE_CVES: list[dict[str, str]] = [
    {
        "cve_id": "CVE-2021-44228",
        "product": "log4j",
        "version": "2.14.1",
        "severity": "CRITICAL",
        "description": (
            "Apache Log4j2 JNDI features do not protect against "
            "attacker controlled LDAP and other JNDI related endpoints."
        ),
    },
    {
        "cve_id": "CVE-2022-3602",
        "product": "openssl",
        "version": "3.0.6",
        "severity": "HIGH",
        "description": (
            "An off-by-one buffer overflow vulnerability in "
            "OpenSSL X.509 email address verification."
        ),
    },
    {
        "cve_id": "CVE-2023-27043",
        "product": "python",
        "version": "3.10.0",
        "severity": "HIGH",
        "description": (
            "Email parsing vulnerability in Python email.utils "
            "module leading to verification bypass."
        ),
    },
    {
        "cve_id": "CVE-2021-23017",
        "product": "nginx",
        "version": "1.20.0",
        "severity": "HIGH",
        "description": (
            "Nginx resolver vulnerability causing one-byte memory "
            "overwrite via crafted DNS response."
        ),
    },
]


async def seed_database(
    *, ollama_url: str, embedding_model: str, db_path: str, chroma_path: str
) -> None:
    """
    Initialize SQLite and ChromaDB stores, calculate local LLM embeddings,
    and perform batch ingestion.

    Args:
        ollama_url (str): Local Ollama HTTP service endpoint.
        embedding_model (str): Ollama target model name for embeddings.
        db_path (str): Output path to SQLite database file.
        chroma_path (str): Output path to ChromaDB storage directory.
    """
    logger.info("starting local cve database seeding process")

    # init databases
    store = StateStore(db_path=db_path, chroma_path=chroma_path)
    store.init_db()

    # init ollama client
    llm = LLMClient(base_url=ollama_url, model_name=embedding_model)

    cves_to_insert: list[dict[str, Any]] = []

    for cve in BASELINE_CVES:
        logger.info(f"generating embedding for {cve['cve_id']}")

        # request embedding vector
        embedding = await llm.get_embedding(text=cve["description"])

        if not embedding:
            logger.warning(f"could not calculate embedding for {cve['cve_id']} fallback to db only")

        cve_record = {
            "cve_id": cve["cve_id"],
            "product": cve["product"],
            "version": cve["version"],
            "severity": cve["severity"],
            "description": cve["description"],
            "embedding": embedding,
        }
        cves_to_insert.append(cve_record)

    # run batch database import
    await store.insert_cves(cves=cves_to_insert)
    logger.info("completed local database seeding successfully")


if __name__ == "__main__":
    # parse command line configurations
    ollama_endpoint = "http://localhost:11434"
    model_name = "nomic-embed-text"
    sqlite_db = "data/cve_db/nvd_mirror.db"
    chroma_dir = "data/cve_db/chroma"

    # run main async runner
    asyncio.run(
        seed_database(
            ollama_url=ollama_endpoint,
            embedding_model=model_name,
            db_path=sqlite_db,
            chroma_path=chroma_dir,
        )
    )
