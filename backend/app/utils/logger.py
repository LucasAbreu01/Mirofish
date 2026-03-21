import logging
import sys
from typing import Optional


def get_logger(name: Optional[str] = None, level: int = logging.DEBUG) -> logging.Logger:
    """Return a configured logger with structured console output.

    Args:
        name: Logger name. Defaults to ``mirofish`` if *None*.
        level: Logging level. Defaults to ``DEBUG``.

    Returns:
        A :class:`logging.Logger` instance with a console handler attached.
    """
    logger_name = name or "mirofish"
    logger = logging.getLogger(logger_name)

    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
