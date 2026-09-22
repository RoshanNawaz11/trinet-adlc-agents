import os
import langwatch

import logging

logger = logging.getLogger(__name__)

initialised = False

def langwatch_setup():
    global initialised
    if initialised:
        return
    disabled = os.getenv("LANGWATCH_DISABLED", "false").lower() == "true"

    try:
        langwatch.setup(
            api_key=os.getenv("LANGWATCH_API_KEY"),
            endpoint_url = os.getenv("LANGWATCH_ENDPOINT_URL", "https://app.langwatch.ai"),
        )
        initialised = True
        if disabled:
            logger.warning("Langwatch is disabled")
    except Exception:
        logger.exception("Failed to setup Langwatch")
        initialised = True


