from unittest.mock import AsyncMock, patch

import pytest

from scripts.mock_telemetry import publish_mock_telemetry


@pytest.mark.asyncio
@patch("scripts.mock_telemetry.MessageBroker")
async def test_mock_telemetry_publishing(mock_broker_class):
    # mock broker instance
    mock_broker = AsyncMock()
    mock_broker.connect = AsyncMock()
    mock_broker.publish = AsyncMock(return_value="1625091234-0")
    mock_broker.disconnect = AsyncMock()
    mock_broker_class.return_value = mock_broker

    # run mock publisher method
    await publish_mock_telemetry(redis_url="redis://localhost:6379")

    # verify connection establish and close calls
    mock_broker.connect.assert_called_once()
    mock_broker.disconnect.assert_called_once()

    # verify two events were published
    assert mock_broker.publish.call_count == 2

    # check first publish stream
    call_args_1 = mock_broker.publish.call_args_list[0][1]
    assert call_args_1["stream"] == "telemetry.system.inventory"
    assert "log4j" in str(call_args_1["data"])

    # check second publish stream
    call_args_2 = mock_broker.publish.call_args_list[1][1]
    assert call_args_2["stream"] == "telemetry.network.events"
    assert "nginx" in str(call_args_2["data"])
