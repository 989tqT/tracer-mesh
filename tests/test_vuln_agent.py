import json
from unittest.mock import AsyncMock

import pytest

from tracer_mesh.agents.vuln import VulnerabilityAnalysisAgent


@pytest.mark.asyncio
async def test_agent_vulnerability_detection():
    # mock broker client
    mock_broker = AsyncMock()
    mock_broker.create_consumer_group = AsyncMock()
    mock_broker.subscribe = AsyncMock()
    mock_broker.publish = AsyncMock()

    # mock llm client
    mock_llm = AsyncMock()
    llm_json_response = json.dumps(
        {
            "cve_id": "CVE-2026-9999",
            "severity": "HIGH",
            "description": "mock package vulnerability",
            "remediation_suggestion": "upgrade mock package",
        }
    )
    mock_llm.generate.return_value = llm_json_response
    mock_llm.get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

    # mock state store DB
    mock_store = AsyncMock()
    mock_store.search_cve_by_product.return_value = [
        {
            "cve_id": "CVE-2026-9999",
            "product": "vulnerable-lib",
            "version": "1.0.0",
            "severity": "HIGH",
            "description": "mock package vulnerability",
        }
    ]
    mock_store.search_cve_by_vector.return_value = []

    # init vulnerability agent
    agent = VulnerabilityAnalysisAgent(
        broker=mock_broker,
        llm=mock_llm,
        state_store=mock_store,
        consumer_group="test_group",
        consumer_name="test_worker",
    )

    # simulate incoming telemetry event
    test_event_data = {"packages": [{"name": "vulnerable-lib", "version": "1.0.0"}]}

    # trigger event handler callback
    await agent.handle_event("telemetry.system.inventory", "1625091234-0", test_event_data)

    # verify local cve database was queried
    mock_store.search_cve_by_product.assert_called_once_with(
        product="vulnerable-lib", version="1.0.0"
    )

    # verify local llm was invoked
    mock_llm.generate.assert_called_once()

    # verify message was published to vulnerability found stream
    mock_broker.publish.assert_called_once()
    publish_args = mock_broker.publish.call_args[1]

    assert publish_args["stream"] == "analysis.vulnerability.found"
    assert publish_args["data"]["cve_id"] == "CVE-2026-9999"
    assert publish_args["data"]["severity"] == "HIGH"
