# Анализ src/app/core/logger.py

## Критические проблемы

### 1. Отсутствует отступ в методе класса (строка 14)
```python
# ОШИБКА: Неправильный отступ
class JsonFormatter(logging.Formatter):
    """Форматирует логи в JSON для Loki."""

def format(self, record):  # <- Должно быть с отступом!
```

**Исправление:**
```python
class JsonFormatter(logging.Formatter):
    """Форматирует логи в JSON для Loki."""

    def format(self, record):
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "level": record.levelname,
            "message": record.getMessage(),
            "source": "app",
            "name": record.name,
            "lineno": record.lineno,
        }
        return json.dumps(log_entry)
```

### 2. Проблемы с логированием времени
```python
# ПРОБЛЕМА: Используется локальное время вместо UTC
"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],

# ИСПРАВЛЕНИЕ: Использовать UTC
"time": datetime.now(datetime.timezone.utc).isoformat(),
```

### 3. Закомментированный код консольного обработчика
```python
# ПРОБЛЕМА: Закомментированный код должен быть удален или реализован
# console_handler = logging.StreamHandler()
# console_handler.setFormatter(text_formatter)

# РЕКОМЕНДАЦИЯ: Добавить опциональный консольный вывод
def setup_logging(console_output: bool = True) -> None:
    # ...

    handlers = [file_handler]

    if console_output and settings.logging.log_stage == "DEV":
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(text_formatter)
        handlers.append(console_handler)

    logging.basicConfig(
        level=settings.logging.log_level_value,
        handlers=handlers,
    )
```

## Рекомендации по улучшению

### 1. Добавить structured logging
```python
class JsonFormatter(logging.Formatter):
    """Форматирует логи в JSON для Loki."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "source": "nutricoreiq",
        }

        # Добавить extra поля если есть
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id

        return json.dumps(log_entry, ensure_ascii=False)
```

### 2. Добавить контекстный логгер
```python
class ContextualLogger:
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context

    def info(self, msg, **kwargs):
        extra = {**self.context, **kwargs}
        self.logger.info(msg, extra=extra)

    def error(self, msg, **kwargs):
        extra = {**self.context, **kwargs}
        self.logger.error(msg, extra=extra)

def get_contextual_logger(name: str, **context) -> ContextualLogger:
    """Возвращает логгер с контекстом"""
    base_logger = logging.getLogger(name)
    return ContextualLogger(base_logger, **context)
```

### 3. Добавить валидацию конфигурации
```python
def setup_logging() -> None:
    """Настройка логирования с валидацией конфигурации."""

    # Валидация конфигурации
    if not settings.logging.log_file:
        raise ValueError("log_file must be specified")

    if settings.logging.log_file_max_size <= 0:
        raise ValueError("log_file_max_size must be positive")

    # Создание директории для логов
    log_dir = Path(settings.logging.log_file).parent
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise RuntimeError(f"Cannot create log directory: {log_dir}")

    # Остальная логика...
```

## Приоритет исправлений

1. **Критический**: Исправить отступ в методе format (синтаксическая ошибка)
2. **Высокий**: Использовать UTC время для логов
3. **Средний**: Убрать закомментированный код или реализовать консольный вывод
4. **Низкий**: Добавить structured logging и валидацию
