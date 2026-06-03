import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from tracer_mesh.agents.patch import PatchAgent


@pytest.fixture
def mock_broker():
    # mock message broker client
    broker = MagicMock()
    broker.create_consumer_group = AsyncMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def mock_llm():
    # mock local llm client
    llm = MagicMock()
    llm.generate = AsyncMock()
    return llm


@pytest.mark.asyncio
async def test_patch_agent_handles_vulnerability_and_publishes(mock_broker, mock_llm):
    # mock llm response json
    mock_llm.generate.return_value = json.dumps(
        {
            "cve_id": "CVE-2021-44228",
            "action": "upgrade",
            "remediation_code": "apt-get upgrade log4j",
            "validation_command": "dpkg -l | grep log4j",
        }
    )

    # initialize patch proposer agent under test
    agent = PatchAgent(broker=mock_broker, llm=mock_llm)

    # simulate incoming vulnerability telemetry finding event
    event = {
        "cve_id": "CVE-2021-44228",
        "severity": "CRITICAL",
        "description": "Log4Shell RCE",
        "affected_component": [{"name": "log4j", "version": "2.14.1"}],
    }

    # call event handler directly
    await agent.handle_vulnerability("analysis.vulnerability.found", "msg-id-1", event)

    # verify local llm was invoked
    mock_llm.generate.assert_called_once()

    # verify message was published to patch proposed stream
    mock_broker.publish.assert_called_once_with(
        stream="remediation.patch.proposed",
        data={
            "cve_id": "CVE-2021-44228",
            "action": "upgrade",
            "remediation_code": "apt-get upgrade log4j",
            "validation_command": "dpkg -l | grep log4j",
        },
    )
