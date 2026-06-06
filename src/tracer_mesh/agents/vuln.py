import asyncio
import logging
from typing import Any

from tracer_mesh.agents.base import BaseAgent
from tracer_mesh.core.broker import MessageBroker
from tracer_mesh.core.db import StateStore
from tracer_mesh.core.llm import LLMClient
from tracer_mesh.core.utils import extract_json
from tracer_mesh.templates import load_template

logger = logging.getLogger(__name__)


class VulnerabilityAnalysisAgent(BaseAgent):
    """
    Vulnerability Analysis Agent within the Tracer Mesh.

    This agent acts as the primary analytical unit for inspecting system inventories
    and network events. It parses telemetry payloads, identifies target components
    (software name and version), queries a combined local SQLite and ChromaDB CVE index,
    and runs a local LLM generation request via Ollama to determine system exposure.

    Attributes:
        broker (MessageBroker): The Redis streams communication interface.
        llm (LLMClient): Client to query the local LLM inference server.
        state_store (StateStore): Combined SQLite/ChromaDB state client.
        consumer_group (str): Redis consumer group identifier.
        consumer_name (str): Redis consumer worker node name.
    """

    def __init__(
        self,
        *,
        broker: MessageBroker,
        llm: LLMClient,
        state_store: StateStore,
        embedding_model: str = "nomic-embed-text",
        consumer_group: str = "vuln_group",
        consumer_name: str = "vuln_worker_1",
    ):
        """
        Initialize the VulnerabilityAnalysisAgent with its runtime clients.

        Args:
            broker (MessageBroker): Redis streams broker client instance.
            llm (LLMClient): local LLM HTTP client instance.
            state_store (StateStore): local CVE and vector store instance.
            consumer_group (str): Consumer group name.
            consumer_name (str): Unique worker instance name.
        """
        # assign base class config
        super().__init__(broker=broker, consumer_group=consumer_group, consumer_name=consumer_name)
        self.llm = llm
        self.state_store = state_store
        self.embedding_model = embedding_model

    async def run(self) -> None:
        """
        Register consumer groups, subscribe to system and network telemetry streams,
        and start the async listener execution block.
        """
        # setup consumer group for system inventory stream
        await self.broker.create_consumer_group(
            stream="telemetry.system.inventory", group=self.consumer_group
        )
        # setup consumer group for network event stream
        await self.broker.create_consumer_group(
            stream="telemetry.network.events", group=self.consumer_group
        )

        # subscribe to telemetry streams
        await self.broker.subscribe(
            streams=["telemetry.system.inventory", "telemetry.network.events"],
            group=self.consumer_group,
            consumer=self.consumer_name,
            callback=self.handle_event,
        )
        logger.info("Vulnerability Analysis Agent started processing streams")

    async def handle_event(self, stream: str, message_id: str, data: dict[str, Any]) -> None:
        """
        Process incoming telemetry messages from subscribed Redis streams.

        Args:
            stream (str): The stream name where the message originated.
            message_id (str): Redis generated message identifier.
            data (Dict[str, Any]): Deserialized message body payload.
        """
        logger.debug(f"event read from stream: {stream} ID: {message_id}")

        # run vulnerability analysis logic
        analysis_result = await self.analyze_vulnerability(event_data=data, source=stream)

        if analysis_result:
            # publish finding if vulnerability confirmed
            await self.broker.publish(stream="analysis.vulnerability.found", data=analysis_result)
            logger.info(f"detected vulnerability published: {analysis_result.get('cve_id')}")

    async def analyze_vulnerability(
        self, *, event_data: dict[str, Any], source: str
    ) -> dict[str, Any] | None:
        """
        Inspect telemetry payload, query local CVE databases, and run local LLM evaluation.

        Args:
            event_data (Dict[str, Any]): Telemetry event payload dictionary.
            source (str): Stream identifier source.

        Returns:
            Optional[Dict[str, Any]]: Vulnerability assessment dict or None if secure.
        """
        # extract soft components from telemetry payload
        components = self._extract_components(event_data=event_data, source=source)
        if not components:
            return None

        # search local database for matching cve record
        matched_cves = await self._query_local_cve_db(components=components)
        if not matched_cves:
            return None

        # prepare context block for LLM prompt
        prompt_context = {
            "event": event_data,
            "source": source,
            "matched_cves": matched_cves,
            "system_context": "OS: ubuntu-22.04 kernel: 5.15.0",
        }

        # request structured risk analysis from local LLM
        llm_response = await self._call_llm_for_analysis(context=prompt_context)
        if not llm_response:
            return None

        # construct unified vulnerability finding payload
        return {
            "cve_id": llm_response.get("cve_id"),
            "severity": llm_response.get("severity"),
            "description": llm_response.get("description"),
            "affected_component": components,
            "remediation_suggestion": llm_response.get("remediation_suggestion"),
            "raw_analysis": llm_response,
        }

    def _extract_components(
        self, *, event_data: dict[str, Any], source: str
    ) -> list[dict[str, str]]:
        """
        Extract software name and version fields from system or network telemetry events.

        Args:
            event_data (Dict[str, Any]): Stream raw payload.
            source (str): Source stream routing key.

        Returns:
            List[Dict[str, str]]: Extracted software objects containing 'name' and 'version'.
        """
        components = []
        if source == "telemetry.system.inventory":
            # parse install packages list
            packages = event_data.get("packages", [])
            for pkg in packages:
                if isinstance(pkg, dict) and "name" in pkg and "version" in pkg:
                    components.append({"name": pkg["name"], "version": pkg["version"]})
        elif source == "telemetry.network.events":
            # parse network service banner
            service = event_data.get("service", {})
            if service and isinstance(service, dict):
                components.append(
                    {"name": service.get("name", ""), "version": service.get("version", "")}
                )
        return components

    async def _query_local_cve_db(
        self, *, components: list[dict[str, str]]
    ) -> list[dict[str, Any]]:
        """
        Query local SQLite database and ChromaDB vector search for component vulnerabilities.

        Args:
            components (List[Dict[str, str]]): List of extracted software dependencies.

        Returns:
            List[Dict[str, Any]]: Matching CVE records.
        """
        async def query_component(*, comp: dict[str, str]) -> list[dict[str, Any]]:
            name = comp["name"]
            version = comp.get("version")

            # search precise product in sqlite
            rows = await self.state_store.search_cve_by_product(product=name, version=version)
            if rows:
                return rows

            # fallback to vector search if no precise db match found
            embedding = await self.llm.get_embedding(text=name, model=self.embedding_model)
            if not embedding:
                return []

            return await self.state_store.search_cve_by_vector(
                query_text=name, embedding=embedding
            )

        # execute queries concurrently to bypass sequential latency
        tasks = [query_component(comp=comp) for comp in components]
        results = await asyncio.gather(*tasks)

        matches = []
        for res in results:
            matches.extend(res)

        # eliminate duplicate cve records by id
        unique = {cve["cve_id"]: cve for cve in matches if cve and "cve_id" in cve}
        logger.info("found %d matched CVEs for components %s", len(unique), str(components))
        return list(unique.values())

    async def _call_llm_for_analysis(self, *, context: dict[str, Any]) -> dict[str, Any] | None:
        # query ollama endpoint and fallback to database record on failure
        try:
            # load analysis template from asset
            template = load_template(name="vuln_analysis.j2")
            prompt = template.render(context)

            # query local model with strict json format constraint
            response_text = await self.llm.generate(prompt=prompt)
            if response_text:
                # decode json content using extractor utility
                result = extract_json(response_text)
                if result:
                    # validate required json attribute
                    required_fields = ["cve_id", "severity", "description"]
                    if all(field in result for field in required_fields):
                        return result
        except Exception as e:
            logger.warning(f"llm execution failed: {str(e)}")

        # fallback to first cve record detail
        if context.get("matched_cves"):
            cve = context["matched_cves"][0]
            return {
                "cve_id": cve.get("cve_id"),
                "severity": cve.get("severity", "UNKNOWN"),
                "description": cve.get("description", ""),
                "remediation_suggestion": "Upgrade affected component to latest version."
            }
        return None
