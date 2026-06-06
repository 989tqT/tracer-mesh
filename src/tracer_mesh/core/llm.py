import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """
    async client for local ollama or vllm interface
    """

    def __init__(self, *, base_url: str = "http://localhost:11434", model_name: str = "llama3"):
        # set connection param
        self.base_url = base_url
        self.model_name = model_name

    async def generate(self, *, prompt: str) -> str | None:
        # query local llm endpoint
        url = f"{self.base_url}/api/generate"

        payload: dict[str, Any] = {"model": self.model_name, "prompt": prompt, "stream": False}

        retries = 3
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        # return generated text output
                        return data.get("response")
                    else:
                        logger.warning(
                            f"ollama response error status: {response.status_code} "
                            f"(attempt {attempt + 1}/{retries})"
                        )
            except Exception as e:
                logger.warning(
                    f"fail to connect to local llm: {str(e)} (attempt {attempt + 1}/{retries})"
                )
            if attempt < retries - 1:
                await asyncio.sleep(1.0)

        logger.error("all attempts to connect to local llm failed")
        return None

    async def get_embedding(self, *, text: str, model: str | None = None) -> list[float] | None:
        # fetch vector embedding from local ollama
        url = f"{self.base_url}/api/embeddings"
        target_model = model or self.model_name

        payload = {"model": target_model, "prompt": text}

        retries = 3
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        # return float vector output
                        return data.get("embedding")
                    else:
                        logger.warning(
                            f"ollama embedding response error status: {response.status_code} "
                            f"(attempt {attempt + 1}/{retries})"
                        )
            except Exception as e:
                logger.warning(
                    f"fail to generate embedding: {str(e)} (attempt {attempt + 1}/{retries})"
                )
            if attempt < retries - 1:
                await asyncio.sleep(1.0)

        logger.error("all attempts to generate embedding failed")
        return None
