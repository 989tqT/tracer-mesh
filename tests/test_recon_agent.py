import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tracer_mesh.agents.recon import ReconAgent


@pytest.fixture
def mock_distributions():
    # mock distribution objects with metadata properties
    mock_dist = MagicMock()
    mock_dist.metadata = {"Name": "test-library"}
    mock_dist.version = "2.3.4"
    return [mock_dist]


@pytest.mark.asyncio
@patch("importlib.metadata.distributions")
async def test_recon_agent_collection(mock_dists_func, mock_distributions):
    # set return value for package lookup
    mock_dists_func.return_value = mock_distributions

    # mock message broker client
    mock_broker = AsyncMock()
    mock_broker.publish = AsyncMock(return_value="1625091234-0")

    # init recon discovery agent with short poll interval
    agent = ReconAgent(
        broker=mock_broker,
        consumer_group="test_recon_group",
        consumer_name="test_recon_worker",
        scan_interval=0.01,
    )

    # run open connection mock to simulate active ports
    async def mock_open_connection(host, port):
        # mock successful connection to port 80 only
        if port == 80:
            mock_writer = AsyncMock()
            mock_writer.close = MagicMock()
            mock_writer.wait_closed = AsyncMock()
            return AsyncMock(), mock_writer
        raise ConnectionRefusedError()

    with patch("asyncio.open_connection", side_effect=mock_open_connection):
        # collect system config
        inventory = await agent.collect_system_inventory()

        # verify package extracted correctly
        assert len(inventory["packages"]) == 1
        assert inventory["packages"][0]["name"] == "test-library"
        assert inventory["packages"][0]["version"] == "2.3.4"

        # verify async port scanner caught port 80
        assert 80 in inventory["open_ports"]
        assert 22 not in inventory["open_ports"]

        # test full loop execution in background
        task = asyncio.create_task(agent.run())
        await asyncio.sleep(0.05)
        task.cancel()

        # verify broker publish got called with telemetry payload
        assert mock_broker.publish.call_count >= 1
        call_args = mock_broker.publish.call_args[1]
        assert call_args["stream"] == "telemetry.system.inventory"
