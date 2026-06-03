import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class MessageBroker:
    """
    async message broker for redis stream
    """

    def __init__(self, *, redis_url: str):
        # init connection param
        self.redis_url = redis_url
        self.client: aioredis.Redis | None = None

    async def connect(self) -> None:
        # establish async connection to redis
        self.client = aioredis.Redis.from_url(self.redis_url, decode_responses=True)
        logger.info("connected to redis stream broker")

    async def disconnect(self) -> None:
        # close connection safely
        if self.client:
            await self.client.close()
            logger.info("disconnected from redis stream broker")

    async def create_consumer_group(self, *, stream: str, group: str) -> None:
        # create consumer group if not exist
        if not self.client:
            raise RuntimeError("broker not connected")
        try:
            # create group from start of stream
            await self.client.xgroup_create(stream, group, id="0", mkstream=True)
            logger.info(f"created consumer group {group} on stream {stream}")
        except aioredis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                # group already exist ignore error
                logger.debug(f"consumer group {group} already exist on stream {stream}")
            else:
                raise e

    async def publish(self, *, stream: str, data: dict[str, Any]) -> str:
        # publish payload to specific stream
        if not self.client:
            raise RuntimeError("broker not connected")

        # serialize complex type to json string
        serialized_data = {}
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                serialized_data[k] = json.dumps(v)
            else:
                serialized_data[k] = str(v)

        message_id: str = await self.client.xadd(stream, serialized_data)
        return message_id

    async def subscribe(
        self,
        *,
        streams: list[str],
        group: str,
        consumer: str,
        callback: Callable[[str, str, dict[str, Any]], Awaitable[None]],
    ) -> None:
        # start listening loop for streams
        if not self.client:
            raise RuntimeError("broker not connected")

        # build stream dict starting with unacknowledged message
        streams_dict = {stream: ">" for stream in streams}

        async def listen_loop():
            while True:
                try:
                    # block for new message
                    response = await self.client.xreadgroup(
                        groupname=group,
                        consumername=consumer,
                        streams=streams_dict,
                        count=1,
                        block=1000,
                    )
                    if not response:
                        await asyncio.sleep(0.1)
                        continue

                    for stream_name, messages in response:
                        for msg_id, raw_data in messages:
                            # deserialize json fields back to dict
                            processed_data = {}
                            for k, v in raw_data.items():
                                try:
                                    processed_data[k] = json.loads(v)
                                except (json.JSONDecodeError, TypeError):
                                    processed_data[k] = v

                            # trigger async callback function
                            await callback(stream_name, msg_id, processed_data)

                            # acknowledge message processed successfully
                            await self.client.xack(stream_name, group, msg_id)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"error in stream subscriber loop: {e}")
                    await asyncio.sleep(1)

        # run task in background
        asyncio.create_task(listen_loop())
