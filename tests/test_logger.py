"""
Тесты для модуля logger.py.
Покрывает: CustomTextFormatter.format, get_logger.
"""

import logging
from unittest.mock import MagicMock, patch


# ─── CustomTextFormatter ─────────────────────────────────────────────────────


class TestCustomTextFormatter:
    """Тесты для CustomTextFormatter."""

    def _make_formatter(self):
        from src.app.core.logger import CustomTextFormatter
        return CustomTextFormatter(fmt="%(levelname)s - %(message)s")

    def _make_record(self, message="Test message", level=logging.INFO):
        record = logging.LogRecord(
            name="test",
            level=level,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )
        return record

    def test_format_without_context_string(self):
        """Без context_string форматирует обычно."""
        formatter = self._make_formatter()
        record = self._make_record("Hello World")
        result = formatter.format(record)

        assert "Hello World" in result
        assert "[" not in result  # нет контекста в скобках

    def test_format_with_context_string(self):
        """С context_string добавляет его в квадратных скобках."""
        formatter = self._make_formatter()
        record = self._make_record("Hello World")
        record.context_string = "ip=1.2.3.4 | request_id=abc"

        result = formatter.format(record)

        assert "Hello World" in result
        assert "[ip=1.2.3.4 | request_id=abc]" in result

    def test_format_context_string_appended_at_end(self):
        """Контекст добавляется в конце строки."""
        formatter = self._make_formatter()
        record = self._make_record("Test")
        record.context_string = "status=200"

        result = formatter.format(record)

        assert result.endswith("[status=200]")

    def test_format_empty_context_string(self):
        """Пустой context_string — добавляются пустые скобки."""
        formatter = self._make_formatter()
        record = self._make_record("Test")
        record.context_string = ""

        result = formatter.format(record)

        assert "[]" in result

    def test_format_preserves_base_format(self):
        """Базовый формат сохраняется."""
        formatter = self._make_formatter()
        record = self._make_record("Base message")

        result = formatter.format(record)

        assert "INFO" in result
        assert "Base message" in result


# ─── get_logger ───────────────────────────────────────────────────────────────


class TestGetLogger:
    """Тесты для get_logger."""

    def test_get_logger_returns_logger(self):
        """get_logger возвращает объект Logger."""
        from src.app.core.logger import get_logger

        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_named_correctly(self):
        """Logger имеет правильное имя."""
        from src.app.core.logger import get_logger

        logger = get_logger("my_service")
        assert logger.name == "my_service"

    def test_get_logger_none_returns_root(self):
        """get_logger(None) возвращает корневой логгер."""
        from src.app.core.logger import get_logger

        logger = get_logger(None)
        assert logger is logging.getLogger(None)

    def test_get_logger_same_name_same_instance(self):
        """Два вызова с одним именем возвращают один и тот же объект."""
        from src.app.core.logger import get_logger

        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Разные имена → разные логгеры."""
        from src.app.core.logger import get_logger

        logger1 = get_logger("service_a")
        logger2 = get_logger("service_b")
        assert logger1 is not logger2
        assert logger1.name != logger2.name