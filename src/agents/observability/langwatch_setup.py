import os
import langwatch

import logging

logger = logging.getLogger(__name__)

initialised = False

def langwatch_setup():
    global initialised
    if initialised:
        return
    if os.getenv("LANGWATCH_DISABLED", "false").lower() == "true":
        logger.warning("Langwatch is disabled")
        initialised = True
        return

    try:
        langwatch.setup(
            api_key=os.getenv("LANGWATCH_API_KEY"),
            endpoint_url = os.getenv("LANGWATCH_ENDPOINT_URL", "https://app.langwatch.ai"),
        )
        initialised = True
    except Exception:
        logger.exception("Failed to setup Langwatch")
        initialised = True


