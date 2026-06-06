import asyncio
import logging
from pathlib import Path
from typing import Any

import psutil
import yaml

from tracer_mesh.agents.base import BaseAgent
from tracer_mesh.core.broker import MessageBroker

logger = logging.getLogger(__name__)

# set default rules path relative to root
_DEFAULT_RULES_PATH = (
    Path(__file__).parent.parent.parent.parent / "configs" / "network_rules.yaml"
)


class NetworkAgent(BaseAgent):
    """
    Agent for inspecting system active network connections.
    Uses psutil to read network states without administrative requirements.
    Matches connections against configs/network_rules.yaml.
    """

    def __init__(
        self,
        *,
        broker: MessageBroker,
        rules_path: str | None = None,
        scan_interval: float = 60.0,
        consumer_group: str = "network_group",
        consumer_name: str = "network_worker_1",
    ):
        """
        Initialize the NetworkAgent with its configs.
        """
        # assign base class config
        super().__init__(broker=broker, consumer_group=consumer_group, consumer_name=consumer_name)
        self.rules_path = Path(rules_path) if rules_path else _DEFAULT_RULES_PATH
        self.scan_interval = scan_interval
        self.rules: list[dict[str, Any]] = []

    async def run(self) -> None:
        """
        Create consumer groups and execute periodic connections scanning loops.
        """
        # setup stream consumer group
        await self.broker.create_consumer_group(
            stream="telemetry.network.events", group=self.consumer_group
        )

        # load rules from configurations
        self.rules = self._load_rules()
        logger.info(f"network agent active polling connections every {self.scan_interval}s")

        async def poll_loop():
            while True:
                try:
                    # inspect active connections
                    events = await self._collect_network_events()
                    for evt in events:
                        await self.broker.publish(stream="telemetry.network.events", data=evt)
                except Exception as e:
                    logger.error(f"error in network agent poll cycle: {str(e)}")

                await asyncio.sleep(self.scan_interval)

        # start connections scanning loop in background task
        asyncio.create_task(poll_loop())

    def _load_rules(self) -> list[dict[str, Any]]:
        # load network rules from local file
        try:
            with open(self.rules_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            rules = data.get("rules", [])
            logger.debug(f"loaded {len(rules)} network rules")
            return rules
        except Exception as e:
            logger.error(f"fail to read rule file {self.rules_path}: {str(e)}")
            return []

    async def _collect_network_events(self) -> list[dict[str, Any]]:
        # query system tcp connections
        try:
            # run psutil scan in background thread
            connections = await asyncio.to_thread(psutil.net_connections, kind="tcp")
        except Exception as e:
            logger.warning(f"could not query active connections: {str(e)}")
            return []

        events = []
        for conn in connections:
            if conn.status != "ESTABLISHED":
                continue

            # check remote destination address exists
            if not conn.raddr:
                continue

            remote_ip, remote_port = conn.raddr
            local_ip, local_port = conn.laddr
            pid = conn.pid
            process_name = None

            if pid:
                try:
                    # lookup process name from pid safely
                    proc = psutil.Process(pid)
                    process_name = proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # check connections against active rules list
            for rule in self.rules:
                alert_if = rule.get("alert_if", {})
                required_ports = alert_if.get("remote_ports", [])
                required_states = alert_if.get("states", [])

                if "ESTABLISHED" in required_states:
                    if remote_port in required_ports:
                        evt = {
                            "timestamp": asyncio.get_event_loop().time(),
                            "local_ip": local_ip,
                            "local_port": local_port,
                            "remote_ip": remote_ip,
                            "remote_port": remote_port,
                            "pid": pid,
                            "process": process_name or "unknown",
                            "rule_triggered": rule.get("name"),
                            "rule_desc": rule.get("description", ""),
                        }
                        events.append(evt)
                        break
        return events
