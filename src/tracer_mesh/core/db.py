import asyncio
import logging
import sqlite3
from typing import Any

import chromadb

logger = logging.getLogger(__name__)


class StateStore:
    """
    manage local sqlite cve db and chromadb vector storage
    """

    def __init__(
        self, *, db_path: str = "data/cve_db/nvd_mirror.db", chroma_path: str = "data/cve_db/chroma"
    ):
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.chroma_client: chromadb.PersistentClient | None = None
        self.collection: Any = None

    def init_db(self) -> None:
        # initialize sqlite table and chroma collection
        # run sync operation inside initialize phase
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # create basic cve schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cves (
                cve_id TEXT PRIMARY KEY,
                product TEXT,
                version TEXT,
                severity TEXT,
                description TEXT
            )
        """)
        conn.commit()
        conn.close()

        # setup local chroma vector storage without default embedding function
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.chroma_client.get_or_create_collection(
            "cves", embedding_function=None
        )
        logger.info("initialized sqlite cve and chromadb storage")

    async def search_cve_by_product(
        self, *, product: str, version: str | None = None
    ) -> list[dict[str, Any]]:
        # query cve database by product name and version
        def query():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if version:
                cursor.execute(
                    "SELECT cve_id, product, version, severity, description "
                    "FROM cves WHERE product = ? AND version = ?",
                    (product, version),
                )
            else:
                cursor.execute(
                    "SELECT cve_id, product, version, severity, description "
                    "FROM cves WHERE product = ?",
                    (product,),
                )

            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]

        # run query in executor to avoid block main loop
        return await asyncio.to_thread(query)

    async def search_cve_by_vector(
        self, *, query_text: str, embedding: list[float] | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        # perform vector search on chroma database
        if not self.collection:
            logger.warning("chromadb collection not initialized")
            return []

        def query():
            # query closest vector matches
            if embedding is not None:
                results = self.collection.query(query_embeddings=[embedding], n_results=limit)
            else:
                logger.warning("skipping vector query due to missing embedding vector")
                return []

            cves = []
            if not results or not results["documents"]:
                return cves

            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            ids = results["ids"][0]

            for i in range(len(ids)):
                meta = metadatas[i] if metadatas else {}
                cves.append(
                    {
                        "cve_id": ids[i],
                        "product": meta.get("product", ""),
                        "version": meta.get("version", ""),
                        "severity": meta.get("severity", ""),
                        "description": documents[i],
                    }
                )
            return cves

        # offload vector query to thread pool
        return await asyncio.to_thread(query)

    async def insert_cves(self, *, cves: list[dict[str, Any]]) -> None:
        # bulk insert cve records to sqlite and chromadb
        if not cves:
            return

        # insert into sqlite first
        def insert_sqlite():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT OR REPLACE INTO cves "
                "(cve_id, product, version, severity, description) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (c["cve_id"], c["product"], c["version"], c["severity"], c["description"])
                    for c in cves
                ],
            )
            conn.commit()
            conn.close()

        await asyncio.to_thread(insert_sqlite)

        # insert into chromadb vector store
        if not self.collection:
            logger.warning("chromadb collection not ready for ingestion")
            return

        def insert_chroma():
            ids = [c["cve_id"] for c in cves]
            documents = [c["description"] for c in cves]
            metadatas = [
                {"product": c["product"], "version": c["version"], "severity": c["severity"]}
                for c in cves
            ]
            embeddings = [c.get("embedding") for c in cves]

            # check if valid embeddings exist for all items
            if all(emb is not None for emb in embeddings):
                self.collection.add(
                    ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
                )
            else:
                self.collection.add(ids=ids, documents=documents, metadatas=metadatas)

        await asyncio.to_thread(insert_chroma)
        logger.info(f"inserted {len(cves)} cve records to local databases")
