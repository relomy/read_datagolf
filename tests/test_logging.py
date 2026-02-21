import logging

import read_datagolf.logging as logging_module


def _reset_root_logger():
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    root_logger.handlers.clear()
    root_logger.setLevel(logging.NOTSET)
    return root_logger, original_handlers, original_level


def _restore_root_logger(root_logger, original_handlers, original_level):
    root_logger.handlers.clear()
    for handler in original_handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(original_level)


def test_configure_logging_squelches_noisy_loggers(monkeypatch):
    root_logger, original_handlers, original_level = _reset_root_logger()
    try:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        logging.getLogger("googleapiclient.discovery").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)

        logging_module.configure_logging()

        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) == 1
        assert logging.getLogger("googleapiclient.discovery").level == logging.INFO
        assert logging.getLogger("urllib3").level == logging.INFO

        logging_module.configure_logging()
        assert len(root_logger.handlers) == 1
    finally:
        _restore_root_logger(root_logger, original_handlers, original_level)
