import asyncio
import logging
from typing import Any

from tracer_mesh.core.broker import MessageBroker

# configure console logging output
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# mock system package inventory telemetry
MOCK_SYSTEM_TELEMETRY: dict[str, Any] = {
    "host": "localhost",
    "os": "ubuntu-22.04",
    "packages": [
        {"name": "openssl", "version": "3.0.6"},
        {"name": "log4j", "version": "2.14.1"},
        {"name": "python", "version": "3.10.0"},
    ],
}

# mock network service telemetry
MOCK_NETWORK_TELEMETRY: dict[str, Any] = {
    "host": "localhost",
    "service": {"name": "nginx", "version": "1.20.0", "port": 80},
}


async def publish_mock_telemetry(*, redis_url: str) -> None:
    """
    Connect to local Redis Stream Broker and publish mock system and network telemetry.

    Args:
        redis_url (str): Target Redis connection URL.
    """
    logger.info(f"connecting to redis broker at {redis_url}")
    broker = MessageBroker(redis_url=redis_url)
    await broker.connect()

    try:
        # publish system inventory telemetry
        msg_id_sys = await broker.publish(
            stream="telemetry.system.inventory", data=MOCK_SYSTEM_TELEMETRY
        )
        logger.info(f"published mock system inventory: msg_id={msg_id_sys}")

        # publish network service event telemetry
        msg_id_net = await broker.publish(
            stream="telemetry.network.events", data=MOCK_NETWORK_TELEMETRY
        )
        logger.info(f"published mock network event: msg_id={msg_id_net}")

    except Exception as e:
        logger.error(f"failed to publish telemetry events: {str(e)}")
    finally:
        await broker.disconnect()


if __name__ == "__main__":
    redis_endpoint = "redis://localhost:6379"
    asyncio.run(publish_mock_telemetry(redis_url=redis_endpoint))
