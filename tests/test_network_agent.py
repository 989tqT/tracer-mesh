from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tracer_mesh.agents.network import NetworkAgent


@pytest.fixture
def mock_broker():
    # mock message broker client
    broker = MagicMock()
    broker.create_consumer_group = AsyncMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def sample_rules():
    # sample configuration rules list directly parsed
    return [
        {
            "name": "test rule",
            "description": "rule for test",
            "alert_if": {"remote_ports": [22, 80], "states": ["ESTABLISHED"]},
        }
    ]


@pytest.mark.asyncio
async def test_network_agent_collects_and_publishes(mock_broker, sample_rules):
    # mock connection instance properties
    mock_conn = MagicMock()
    mock_conn.status = "ESTABLISHED"
    mock_conn.raddr = ("93.184.216.34", 80)
    mock_conn.laddr = ("192.168.1.5", 54321)
    mock_conn.pid = 1234

    # mock process details
    mock_process = MagicMock()
    mock_process.name.return_value = "python"

    with (
        patch("psutil.net_connections", return_value=[mock_conn]),
        patch("psutil.Process", return_value=mock_process),
    ):
        # initialize network agent under test
        agent = NetworkAgent(broker=mock_broker, rules_path="fake_path")

        # override rules loading function to return mock rules
        agent._load_rules = MagicMock(return_value=sample_rules)
        agent.rules = agent._load_rules()

        # collect events from network scan
        events = await agent._collect_network_events()

        # verify rule triggered correctly
        assert len(events) == 1
        assert events[0]["remote_port"] == 80
        assert events[0]["rule_triggered"] == "test rule"
        assert events[0]["process"] == "python"
