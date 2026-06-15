import logging
import traceback

logger = logging.getLogger(__name__)


class FallbackChain:
    def __init__(self, name: str):
        self.name = name
        self.handlers = []

    def add_handler(self, func, name: str = None):
        self.handlers.append((func, name or func.__name__))
        return self

    def execute(self, *args, **kwargs):
        last_error = None
        for func, handler_name in self.handlers:
            try:
                logger.info("[%s] Trying handler: %s", self.name, handler_name)
                result = func(*args, **kwargs)
                if result is not None:
                    logger.info("[%s] Handler %s succeeded", self.name, handler_name)
                    return result
                logger.warning("[%s] Handler %s returned None", self.name, handler_name)
            except Exception as e:
                last_error = e
                logger.error("[%s] Handler %s failed: %s", self.name, handler_name, e)
        raise RuntimeError(f"[{self.name}] All handlers failed. Last error: {last_error}")


def critical_failure_alert(component: str, error: Exception):
    details = (
        f"CRITICAL FAILURE - {component}\n"
        f"Error: {error}\n"
        f"Traceback:\n{''.join(traceback.format_tb(error.__traceback__))}"
    )
    logger.critical(details)
    return details
