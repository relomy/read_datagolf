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


def test_configure_logging_squelches_noisy_loggers_without_logging_ini(monkeypatch, tmp_path):
    root_logger, original_handlers, original_level = _reset_root_logger()
    try:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setattr(
            logging_module.app_config, "logging_ini_path", lambda: tmp_path / "missing.ini"
        )
        logging.getLogger("googleapiclient.discovery").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)

        logging_module.configure_logging()

        assert root_logger.level == logging.DEBUG
        assert logging.getLogger("googleapiclient.discovery").level == logging.INFO
        assert logging.getLogger("urllib3").level == logging.INFO
    finally:
        _restore_root_logger(root_logger, original_handlers, original_level)


def test_configure_logging_squelches_noisy_loggers_with_logging_ini(monkeypatch, tmp_path):
    root_logger, original_handlers, original_level = _reset_root_logger()
    try:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        logging_ini_path = tmp_path / "logging.ini"
        logging_ini_path.write_text(
            """
[loggers]
keys=root
[handlers]
keys=null
[formatters]
keys=simple
[logger_root]
level=DEBUG
handlers=null
[handler_null]
class=NullHandler
level=DEBUG
formatter=simple
args=()
[formatter_simple]
format=%(levelname)s %(name)s %(message)s
""".strip(),
            encoding="utf-8",
        )
        monkeypatch.setattr(logging_module.app_config, "logging_ini_path", lambda: logging_ini_path)
        logging.getLogger("googleapiclient.discovery").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)

        logging_module.configure_logging()

        assert root_logger.level == logging.DEBUG
        assert logging.getLogger("googleapiclient.discovery").level == logging.INFO
        assert logging.getLogger("urllib3").level == logging.INFO
    finally:
        _restore_root_logger(root_logger, original_handlers, original_level)
