import asyncio
import importlib.metadata
import logging
from typing import Any

from tracer_mesh.agents.base import BaseAgent
from tracer_mesh.core.broker import MessageBroker

logger = logging.getLogger(__name__)

# target common ports list for discovery scan
COMMON_PORTS: list[int] = [21, 22, 23, 25, 53, 80, 110, 139, 443, 445, 1433, 3306, 3389, 8080, 8443]


class ReconAgent(BaseAgent):
    """
    Recon and Discovery Agent responsible for collecting local host system configuration.
    It scans installed python packages and checks open TCP ports asynchronously.
    """

    def __init__(
        self,
        *,
        broker: MessageBroker,
        consumer_group: str = "recon_group",
        consumer_name: str = "recon_worker_1",
        scan_interval: float = 60.0,
    ):
        """
        Initialize the ReconAgent configuration parameters.
        """
        # initialize base agent fields
        super().__init__(broker=broker, consumer_group=consumer_group, consumer_name=consumer_name)
        self.scan_interval = scan_interval

    async def run(self) -> None:
        """
        Run the periodic system state polling execution loop.
        """
        logger.info(f"Recon Agent active running scans every {self.scan_interval}s")

        async def poll_loop():
            while True:
                try:
                    # gather system details
                    system_data = await self.collect_system_inventory()

                    # publish telemetry payload to stream channel
                    msg_id = await self.broker.publish(
                        stream="telemetry.system.inventory", data=system_data
                    )
                    logger.info(f"recon agent published telemetry inventory msg: {msg_id}")
                except Exception as e:
                    logger.error(f"error during recon agent discovery cycle: {str(e)}")

                await asyncio.sleep(self.scan_interval)

        # start poll cycle in background task
        asyncio.create_task(poll_loop())

    async def collect_system_inventory(self) -> dict[str, Any]:
        """
        Gather local installed packages and active listening server ports.

        Returns:
            Dict[str, Any]: Formatted telemetry inventory payload.
        """
        # collect packages list from python context
        packages = self._get_installed_packages()

        # run async scanning over port list
        open_ports = await self._scan_open_ports()

        # compile telemetry dictionary format
        return {
            "host": "localhost",
            "os": "ubuntu-22.04",  # baseline fallback tag
            "packages": packages,
            "open_ports": open_ports,
        }

    def _get_installed_packages(self) -> list[dict[str, str]]:
        # read local distributions meta info
        packages_list = []
        dists = importlib.metadata.distributions()
        for dist in dists:
            name = dist.metadata["Name"]
            version = dist.version
            if name and version:
                packages_list.append({"name": name.lower(), "version": version})
        return packages_list

    async def _scan_open_ports(self) -> list[int]:
        # scan target common ports asynchronously
        open_ports = []

        async def check_port(*, port: int) -> None:
            try:
                # check socket connection state
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", port), timeout=0.1
                )
                open_ports.append(port)
                writer.close()
                await writer.wait_closed()
            except Exception:
                # port is closed or timeout occurred
                pass

        # run port checks concurrently
        tasks = [check_port(port=port) for port in COMMON_PORTS]
        await asyncio.gather(*tasks)
        return sorted(open_ports)
