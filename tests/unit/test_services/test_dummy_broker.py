"""
Базовые тесты для DummyBroker.
"""

import pytest

from src.app.core.services.dummy_broker import DummyBroker


class TestDummyBrokerBasic:
    """Базовые тесты для DummyBroker."""

    def test_is_worker_process_false(self):
        """Проверяем, что is_worker_process всегда False."""
        assert DummyBroker.is_worker_process is False

    @pytest.mark.asyncio
    async def test_startup_no_op(self):
        """Проверяем, что startup метод ничего не делает."""
        broker = DummyBroker()
        result = await broker.startup()
        assert result is None

    @pytest.mark.asyncio
    async def test_shutdown_no_op(self):
        """Проверяем, что shutdown метод ничего не делает."""
        broker = DummyBroker()
        result = await broker.shutdown()
        assert result is None

    def test_task_decorator_is_callable(self):
        """Проверяем, что декоратор task является вызываемым."""
        assert callable(DummyBroker.task)

    def test_task_decorator_with_function(self):
        """Проверяем работу декоратора с функцией."""
        def test_func():
            return "test"
        
        decorated = DummyBroker.task(test_func)
        assert callable(decorated)

    def test_task_decorator_without_function(self):
        """Проверяем, что декоратор без функции возвращает декоратор."""
        broker = DummyBroker()
        decorator = broker.task()
        assert callable(decorator)

    def test_broker_instance_exists(self):
        """Проверяем, что экземпляр брокера существует."""
        from src.app.core.services.dummy_broker import broker
        assert broker is not None
        assert isinstance(broker, DummyBroker)

    def test_broker_has_task_method(self):
        """Проверяем, что у брокера есть метод task."""
        assert hasattr(DummyBroker(), 'task')
        assert callable(DummyBroker().task)

    def test_broker_has_startup_method(self):
        """Проверяем, что у брокера есть метод startup."""
        assert hasattr(DummyBroker(), 'startup')
        assert callable(DummyBroker().startup)

    def test_broker_has_shutdown_method(self):
        """Проверяем, что у брокера есть метод shutdown."""
        assert hasattr(DummyBroker(), 'shutdown')
        assert callable(DummyBroker().shutdown)

    def test_task_decorator_accepts_args_kwargs(self):
        """Проверяем, что декоратор task принимает args и kwargs."""
        # Декоратор должен принимать любые аргументы
        decorator = DummyBroker.task("arg1", kwarg1="value1")
        assert callable(decorator)

    def test_task_decorator_with_simple_function(self):
        """Проверяем работу с простой функцией."""
        @DummyBroker.task
        def simple_func():
            return "simple"
        
        # Проверяем, что функция осталась вызываемой
        assert callable(simple_func)

    def test_task_decorator_with_function_args(self):
        """Проверяем работу с функцией с аргументами."""
        @DummyBroker.task
        def func_with_args(x, y):
            return x + y
        
        # Проверяем, что функция осталась вызываемой
        assert callable(func_with_args)

    def test_task_decorator_with_function_kwargs(self):
        """Проверяем работу с функцией с kwargs."""
        @DummyBroker.task
        def func_with_kwargs(x, default=1):
            return x + default
        
        # Проверяем, что функция осталась вызываемой
        assert callable(func_with_kwargs)

    def test_task_decorator_with_async_function(self):
        """Проверяем работу с async функцией."""
        @DummyBroker.task
        async def async_func():
            return "async"
        
        # Проверяем, что функция осталась вызываемой
        assert callable(async_func)

    def test_broker_class_structure(self):
        """Проверяем структуру класса DummyBroker."""
        # Проверяем атрибуты класса
        assert hasattr(DummyBroker, 'is_worker_process')
        assert hasattr(DummyBroker, 'task')
        
        # Проверяем методы экземпляра
        broker = DummyBroker()
        assert hasattr(broker, 'startup')
        assert hasattr(broker, 'shutdown')
        assert hasattr(broker, 'task')
