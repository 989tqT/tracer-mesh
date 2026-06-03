import abc
import logging

from tracer_mesh.core.broker import MessageBroker

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    """
    abstract base agent for tracer mesh
    """

    def __init__(self, *, broker: MessageBroker, consumer_group: str, consumer_name: str):
        # assign message broker and credentials
        self.broker = broker
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name

    @abc.abstractmethod
    async def run(self) -> None:
        # run main background loop for agent
        pass
