import argparse
import asyncio
import logging
import signal
import sys

from scripts.mock_telemetry import publish_mock_telemetry
from tracer_mesh.agents.recon import ReconAgent
from tracer_mesh.agents.vuln import VulnerabilityAnalysisAgent
from tracer_mesh.core.broker import MessageBroker
from tracer_mesh.core.config import settings
from tracer_mesh.core.db import StateStore
from tracer_mesh.core.llm import LLMClient

# configure high-readability logging outputs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("tracer_mesh.main")


async def shutdown(*, broker: MessageBroker, loop: asyncio.AbstractEventLoop) -> None:
    # close broker connection on shutdown
    logger.info("received shutdown signal cleaning up connection")
    await broker.disconnect()

    # gather and cancel all running task list
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def run_mock_generator(*, redis_url: str, delay: float = 3.0) -> None:
    # wait for agents to bootstrap
    await asyncio.sleep(delay)
    logger.info("kicking off mock telemetry publishing sequence")
    await publish_mock_telemetry(redis_url=redis_url)


async def start_app(*, args: argparse.Namespace) -> None:
    # resolve connection parameters
    redis_url = args.redis_url or settings.redis_url
    ollama_url = args.ollama_url or settings.ollama_url
    llm_model = args.llm_model or settings.llm_model
    emb_model = args.embedding_model or settings.embedding_model
    db_path = args.db_path or settings.db_path
    chroma_path = args.chroma_path or settings.chroma_path

    logger.info(
        f"bootstrapping tracer mesh service engine (reasoning: {llm_model}, embedding: {emb_model})"
    )

    # init message broker connection
    broker = MessageBroker(redis_url=redis_url)
    await broker.connect()

    # init local database indexes
    state_store = StateStore(db_path=db_path, chroma_path=chroma_path)
    state_store.init_db()

    # init local llm query client
    llm_client = LLMClient(base_url=ollama_url, model_name=llm_model)

    # instantiate core vulnerability analysis agent
    vuln_agent = VulnerabilityAnalysisAgent(
        broker=broker,
        llm=llm_client,
        state_store=state_store,
        consumer_group="vuln_group",
        consumer_name="vuln_cli_worker",
    )

    # register active signal handler for clean shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(
                sig, lambda: asyncio.create_task(shutdown(broker=broker, loop=loop))
            )
        except NotImplementedError:
            # signal handler not support on windows platform
            pass

    # start vulnerability agent processing loop
    await vuln_agent.run()

    # check if recon discovery agent enabled
    if args.recon:
        recon_agent = ReconAgent(
            broker=broker,
            consumer_group="recon_group",
            consumer_name="recon_cli_worker",
        )
        await recon_agent.run()

    # check if mock telemetry generation enabled
    if args.mock:
        asyncio.create_task(run_mock_generator(redis_url=redis_url))

    # keep orchestrator running indefinitely
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        logger.info("main runner loop cancelled execution")


def main() -> None:
    # configure command line arguments parser
    parser = argparse.ArgumentParser(
        description="Tracer Mesh: Local-first AI agent mesh for threat hunting."
    )
    parser.add_argument("--redis-url", help="redis connection endpoint url")
    parser.add_argument("--ollama-url", help="local ollama server base url")
    parser.add_argument("--llm-model", help="model used for security analysis")
    parser.add_argument("--embedding-model", help="model used for vector embeddings")
    parser.add_argument("--db-path", help="cve sqlite database file path")
    parser.add_argument("--chroma-path", help="chromadb database directory path")
    parser.add_argument(
        "--recon",
        action="store_true",
        help="activate local system recon discovery agent in background",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="trigger background mock telemetry publisher for testing",
    )

    args = parser.parse_args()

    # run main async event loop
    try:
        asyncio.run(start_app(args=args))
    except KeyboardInterrupt:
        logger.info("application terminated by user command")
        sys.exit(0)


if __name__ == "__main__":
    main()
