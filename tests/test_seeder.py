from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.seed_cve import seed_database


@pytest.mark.asyncio
@patch("scripts.seed_cve.StateStore")
@patch("scripts.seed_cve.LLMClient")
async def test_seeder_execution_flow(mock_llm_class, mock_store_class):
    # mock storage instance
    mock_store = MagicMock()
    mock_store.init_db = MagicMock()
    mock_store.insert_cves = AsyncMock()
    mock_store_class.return_value = mock_store

    # mock llm instance
    mock_llm = AsyncMock()
    mock_llm.get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
    mock_llm_class.return_value = mock_llm

    # execute seeding flow
    await seed_database(
        ollama_url="http://localhost:11434",
        embedding_model="nomic-embed-text",
        db_path="mock.db",
        chroma_path="mock_chroma",
    )

    # verify storage was initialized
    mock_store.init_db.assert_called_once()

    # verify embeddings were computed for baseline cves
    assert mock_llm.get_embedding.call_count > 0

    # verify database insert was invoked with list payload
    mock_store.insert_cves.assert_called_once()
    inserted_args = mock_store.insert_cves.call_args[1]

    assert "cves" in inserted_args
    assert len(inserted_args["cves"]) == 4
    assert inserted_args["cves"][0]["cve_id"] == "CVE-2021-44228"
    assert inserted_args["cves"][0]["embedding"] == [0.1, 0.2, 0.3]
