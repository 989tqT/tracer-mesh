import argparse
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tracer_mesh.main import start_app


@pytest.mark.asyncio
@patch("tracer_mesh.main.MessageBroker")
@patch("tracer_mesh.main.StateStore")
@patch("tracer_mesh.main.LLMClient")
@patch("tracer_mesh.main.VulnerabilityAnalysisAgent")
async def test_main_startup_pipeline(
    mock_agent_class, mock_llm_class, mock_store_class, mock_broker_class
):
    # mock broker connection
    mock_broker = AsyncMock()
    mock_broker.connect = AsyncMock()
    mock_broker.disconnect = AsyncMock()
    mock_broker_class.return_value = mock_broker

    # mock database setup
    mock_store = MagicMock()
    mock_store.init_db = MagicMock()
    mock_store_class.return_value = mock_store

    # mock llm client setup
    mock_llm = AsyncMock()
    mock_llm_class.return_value = mock_llm

    # mock agent setup
    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock()
    mock_agent_class.return_value = mock_agent

    # build CLI argument Namespace mock
    args = argparse.Namespace(
        redis_url="redis://localhost:9999",
        ollama_url="http://localhost:8888",
        reasoning_model="test-llm",
        embedding_model="test-emb",
        db_path="test.db",
        chroma_path="test_chroma",
        mock=False,
    )

    # run start_app in background task and cancel it immediately
    task = asyncio.create_task(start_app(args=args))
    await asyncio.sleep(0.1)
    task.cancel()

    # verify broker connection called with parameter
    mock_broker_class.assert_called_once_with(redis_url="redis://localhost:9999")
    mock_broker.connect.assert_called_once()

    # verify local database initialized
    mock_store_class.assert_called_once_with(db_path="test.db", chroma_path="test_chroma")
    mock_store.init_db.assert_called_once()

    # verify agent was instantiated and executed
    mock_agent_class.assert_called_once()
    mock_agent.run.assert_called_once()
