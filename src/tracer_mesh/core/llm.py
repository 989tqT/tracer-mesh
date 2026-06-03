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

    async def generate(self, *, prompt: str, format: str | None = None) -> str | None:
        # query local llm endpoint
        url = f"{self.base_url}/api/generate"

        payload: dict[str, Any] = {"model": self.model_name, "prompt": prompt, "stream": False}

        if format:
            # set output mode like json
            payload["format"] = format

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    # return generated text output
                    return data.get("response")
                else:
                    logger.error(f"ollama response error status: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"fail to connect to local llm: {str(e)}")
            return None

    async def get_embedding(self, *, text: str, model: str | None = None) -> list[float] | None:
        # fetch vector embedding from local ollama
        url = f"{self.base_url}/api/embeddings"
        target_model = model or self.model_name

        payload = {"model": target_model, "prompt": text}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    # return float vector output
                    return data.get("embedding")
                else:
                    logger.error(f"ollama embedding response error status: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"fail to generate embedding: {str(e)}")
            return None
