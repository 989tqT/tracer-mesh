import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_json(text: str) -> dict[str, Any] | None:
    # parse first json object inside text string
    # strip markdown code block tag if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE).rstrip("`").strip()

    # query closest regex pattern match
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            # decode json substring securely
            decoded: dict[str, Any] = json.loads(match.group(0))
            return decoded
        except json.JSONDecodeError as e:
            logger.debug(f"fail to parse regex matched json block: {str(e)}")

    # fallback to parse full string
    try:
        fallback_decoded: dict[str, Any] = json.loads(cleaned)
        return fallback_decoded
    except json.JSONDecodeError as e:
        logger.debug(f"fail to parse cleaned text as fallback json: {str(e)}")
        return None

