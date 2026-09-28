import logging
from pathlib import Path


def setup_logger(log_dir: Path):
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("qwen_assistant")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(
            log_dir / "assistant.log",
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
