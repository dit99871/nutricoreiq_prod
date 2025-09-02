from typing import Any, Awaitable, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class DummyBroker:
    """
    Простейшая заглушка брокера для dev-среды.

    - .task: декоратор, возвращает исходную async-функцию и навешивает на неё .kiq
      (async-метод), который просто выполняет функцию сразу.
    - .startup/.shutdown: no-op async методы.
    - .is_worker_process: всегда False.
    """

    is_worker_process: bool = False

    async def startup(self) -> None:  # совместимость с жизненным циклом
        return None

    async def shutdown(self) -> None:  # совместимость с жизненным циклом
        return None

    def task(self, *dargs: Any, **dkwargs: Any) -> Callable[[F], F]:
        """Декоратор, имитирующий taskiq .task.

        Любые аргументы принимаются и игнорируются, чтобы сигнатуры совпадали.
        На обёрнутую функцию добавляется атрибут .kiq, который является
        async-функцией и вызывает исходную функцию напрямую.
        """

        def decorator(func: F) -> F:
            async def kiq(*args: Any, **kwargs: Any) -> Any:
                return await func(*args, **kwargs)

            # Дополнительно можно имитировать .apply, если где-то потребуется
            async def apply(*args: Any, **kwargs: Any) -> Any:
                return await func(*args, **kwargs)

            # Присваиваем атрибуты к исходной функции
            setattr(func, "kiq", kiq)
            setattr(func, "apply", apply)

            # Для совместимости можно вернуть объект с теми же ссылками
            return func

        return decorator


# Экземпляр заглушки, аналогично реальному broker
broker = DummyBroker()
