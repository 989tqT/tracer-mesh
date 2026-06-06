import logging
from typing import Any

from tracer_mesh.agents.base import BaseAgent
from tracer_mesh.core.broker import MessageBroker
from tracer_mesh.core.llm import LLMClient
from tracer_mesh.core.utils import extract_json
from tracer_mesh.templates import load_template

logger = logging.getLogger(__name__)


class PatchAgent(BaseAgent):
    """
    agent proposing remediation patch for identified vulnerability
    uses local llm to generate correction script
    """

    def __init__(
        self,
        *,
        broker: MessageBroker,
        llm: LLMClient,
        consumer_group: str = "patch_group",
        consumer_name: str = "patch_worker_1",
    ):
        # assign base class config
        super().__init__(broker=broker, consumer_group=consumer_group, consumer_name=consumer_name)
        self.llm = llm

    async def run(self) -> None:
        # register consumer group and subscribe to vulnerability found stream
        await self.broker.create_consumer_group(
            stream="analysis.vulnerability.found", group=self.consumer_group
        )
        await self.broker.subscribe(
            streams=["analysis.vulnerability.found"],
            group=self.consumer_group,
            consumer=self.consumer_name,
            callback=self.handle_vulnerability,
        )
        logger.info("patch proposer agent active listening for vulnerabilities")

    async def handle_vulnerability(
        self, stream: str, message_id: str, data: dict[str, Any]
    ) -> None:
        # process incoming vulnerability report and publish patch proposal
        logger.debug(f"received vulnerability finding details for {data.get('cve_id')}")

        # format prompt template using jinja environment
        template = load_template(name="patch_generation.j2")
        prompt = template.render(
            cve_id=data.get("cve_id", ""),
            severity=data.get("severity", ""),
            description=data.get("description", ""),
            affected_component=data.get("affected_component", []),
        )

        # generate structured patch suggestion using local reasoning client
        proposal = None
        try:
            response = await self.llm.generate(prompt=prompt)
            if response:
                # decode json content using extractor utility
                proposal = extract_json(response)
        except Exception as e:
            logger.warning(f"patch llm execution failed: {str(e)}")

        # fallback to generic proposal on llm failure or missing required field
        required_fields = ["cve_id", "action", "remediation_code", "validation_command"]
        if not proposal or not all(field in proposal for field in required_fields):
            logger.warning("llm patch generation failed or missing field, using fallback")
            comp = data.get("affected_component", [{}])
            name = comp[0].get("name", "unknown") if comp else "unknown"
            proposal = {
                "cve_id": data.get("cve_id"),
                "action": "upgrade",
                "remediation_code": f"apt-get upgrade {name}",
                "validation_command": f"dpkg -l | grep {data.get('cve_id', '')}",
            }

        # publish patch proposal to stream broker
        await self.broker.publish(stream="remediation.patch.proposed", data=proposal)
        logger.info(f"remediation patch proposed successfully for {proposal.get('cve_id')}")
